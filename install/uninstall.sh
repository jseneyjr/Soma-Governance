#!/usr/bin/env bash
set -euo pipefail

# Symlink-safe resolution
PRG="${BASH_SOURCE[0]}"
while [ -h "$PRG" ]; do
  DIR="$(cd -P "$(dirname "$PRG")" && pwd)"
  PRG="$(readlink "$PRG")"
  [[ $PRG != /* ]] && PRG="$DIR/$PRG"
done
REPO_DIR="$(cd -P "$(dirname "$PRG")/.." && pwd)"

source "$REPO_DIR/enzymes/common.sh"
load_config "$REPO_DIR"

DRY_RUN=false
KEEP_CONFIG=false
FORCE=false
NO_RESTORE=false
PURGE_DATA=false
POSITIONAL_ARGS=()

usage() {
  cat <<'USAGE'
Soma uninstaller

Usage: bash install/uninstall.sh [platform] [options]
  platform: gemini (default) | kiro | copilot | claude | mcp

Options:
  --dry-run       Print the removal plan without deleting anything
  --force         Skip the deletion confirmation prompt.
                  Does NOT disable the restore offer (use --no-restore).
  --no-restore    Do not offer to restore the previous configuration
  --keep-config   Never remove soma.conf
  --purge-data    Also remove user-authored governance data:
                  .soma/cells/, fitness.jsonl, docs/snapshots/
                  (these are PRESERVED by default)
  -h, --help      Show this help

Never removed without --purge-data: your cells, fitness history and snapshots.
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --keep-config) KEEP_CONFIG=true ;;
    --force) FORCE=true ;;
    --no-restore) NO_RESTORE=true ;;
    --purge-data) PURGE_DATA=true ;;
    -h|--help) usage; exit 0 ;;
    -*) log_error "Unknown option: $arg"; usage; exit 1 ;;
    *) POSITIONAL_ARGS+=("$arg") ;;
  esac
done

PLATFORM="${POSITIONAL_ARGS[0]:-${SOMA_PLATFORM:-gemini}}"

DETECTED_OS="$(detect_os)"
RESOLVED_HOME="$(resolve_home "$DETECTED_OS")"
MANIFEST_PATH="$RESOLVED_HOME/.soma/manifest.json"
if [ -f "$(pwd)/.soma/manifest.json" ]; then
  MANIFEST_PATH="$(pwd)/.soma/manifest.json"
fi

MANIFEST_EXISTS=false
if [ -f "$MANIFEST_PATH" ]; then
  MANIFEST_EXISTS=true
fi
MANIFEST_PLATFORM=""
MANIFEST_SCOPE=""
RESTORED_ANY=false

# ── Restore Helpers ───────────────────────────────────────────────
# The backup directory name differs from the destination name (genome -> rules,
# organs -> skills), so `cp -r src dst` would nest src inside dst. Copy contents
# instead. Also creates the destination parent: `[ -f x ] && cp x dir/` aborted
# the whole script under `set -e` when dir/ did not exist.
restore_dir_contents() {
  local src="$1" dst="$2"
  [ -d "$src" ] || return 0
  mkdir -p "$dst" || return 0
  # Dotfiles included; an empty source is not an error.
  if find "$src" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null | grep -q .; then
    cp -R "$src"/. "$dst"/ 2>/dev/null || {
      log_warn "Could not fully restore $src -> $dst"
      return 0
    }
  fi
  echo "  restored $dst"
  RESTORED_ANY=true
  return 0
}

restore_file() {
  local src="$1" dst="$2"
  [ -f "$src" ] || return 0
  mkdir -p "$(dirname "$dst")" || return 0
  cp -- "$src" "$dst" 2>/dev/null || {
    log_warn "Could not restore $src -> $dst"
    return 0
  }
  echo "  restored $dst"
  RESTORED_ANY=true
  return 0
}

echo "Uninstalling Soma ($PLATFORM)..."
[ "$DRY_RUN" = "true" ] && echo "Mode: DRY-RUN (no files will be deleted)"

FILES_TO_REMOVE=()
DIRS_TO_REMOVE=()
MODIFY_FILES=()
BACKUP_DIR=""

# Reads one field from the manifest. The path is passed through the environment
# rather than interpolated into the Python source: a quote in the path used to
# be a silent SyntaxError (swallowed by 2>/dev/null), and a crafted directory
# name was code execution.
read_manifest_field() {
  SOMA_MANIFEST="$MANIFEST_PATH" python3 -c '
import json, os, sys
field = sys.argv[1]
with open(os.environ["SOMA_MANIFEST"], "r", encoding="utf-8") as fh:
    data = json.load(fh)
value = data.get(field)
if value is None:
    pass
elif isinstance(value, list):
    for item in value:
        if item:
            print(item)
else:
    print(value)
' "$1"
}

if [ "$MANIFEST_EXISTS" = "true" ]; then
  echo "Found manifest at $MANIFEST_PATH. Reading paths..."

  if ! command -v python3 >/dev/null 2>&1; then
    log_error "A manifest exists at $MANIFEST_PATH but python3 is not available to read it."
    log_error "Refusing to continue: guessing paths risks an incomplete uninstall."
    log_error "Install python3, or delete the manifest to use pattern-based removal."
    exit 1
  fi

  # Validate before use. Failures inside process substitution are invisible to
  # `set -e`, so the old code silently produced an empty removal plan, deleted
  # the manifest, and reported "Uninstall complete."
  if ! MANIFEST_PLATFORM="$(read_manifest_field platform 2>/dev/null)"; then
    log_error "Manifest at $MANIFEST_PATH is unreadable or not valid JSON."
    log_error "Refusing to continue. Repair or delete it, then re-run."
    exit 1
  fi

  # Platform guard: the manifest branch used to ignore $PLATFORM entirely, so
  # `uninstall.sh mcp` against a kiro manifest deleted the kiro install.
  if [ -n "$MANIFEST_PLATFORM" ] && [ "$MANIFEST_PLATFORM" != "$PLATFORM" ]; then
    if [ "$FORCE" = "true" ]; then
      log_warn "PLATFORM MISMATCH: manifest records '$MANIFEST_PLATFORM', you asked for '$PLATFORM'."
      log_warn "--force supplied, continuing: the '$MANIFEST_PLATFORM' paths will be removed."
    else
      log_error "PLATFORM MISMATCH: manifest records '$MANIFEST_PLATFORM', you asked for '$PLATFORM'."
      log_error "Re-run as: bash install/uninstall.sh $MANIFEST_PLATFORM"
      log_error "Or pass --force to remove the '$MANIFEST_PLATFORM' paths anyway."
      exit 1
    fi
  fi

  BACKUP_DIR="$(read_manifest_field backup_dir)"
  MANIFEST_SCOPE="$(read_manifest_field scope)"

  is_safe_removal_path() {
    local target="$1"
    [ -z "$target" ] && return 1
    [ "$target" = "/" ] && return 1
    [ "$target" = "$RESOLVED_HOME" ] && return 1
    [ "$target" = "$(pwd)" ] && return 1
    case "$target" in
      "$RESOLVED_HOME"/*|"$(pwd)"/*) return 0 ;;
      *) return 1 ;;
    esac
  }

  while IFS= read -r f; do
    if is_safe_removal_path "$f"; then
      if [[ "$f" == *"/copilot-instructions.md" ]] || [[ "$f" == *"/CLAUDE.md" ]]; then
        MODIFY_FILES+=("$f")
      elif [ -n "$f" ]; then
        FILES_TO_REMOVE+=("$f")
      fi
    fi
  done <<< "$(read_manifest_field files)"

  while IFS= read -r d; do
    [ -n "$d" ] && is_safe_removal_path "$d" && DIRS_TO_REMOVE+=("$d")
  done <<< "$(read_manifest_field organs)"

  while IFS= read -r h; do
    [ -n "$h" ] && is_safe_removal_path "$h" && FILES_TO_REMOVE+=("$h")
  done <<< "$(read_manifest_field hooks)"

  FILES_TO_REMOVE+=("$MANIFEST_PATH")
else
  echo "No manifest found. Falling back to known patterns..."
  case "$PLATFORM" in
    gemini)
      # install.sh writes config/rules and config/skills. These globs used to
      # say config/genome and config/organs, so the fallback matched nothing and
      # removed nothing.
      for f in "$RESOLVED_HOME"/.gemini/config/rules/*.md; do
        [ -f "$f" ] && FILES_TO_REMOVE+=("$f")
      done
      for d in "$RESOLVED_HOME"/.gemini/config/skills/*; do
        [ -d "$d" ] && DIRS_TO_REMOVE+=("$d")
      done
      [ -d "$RESOLVED_HOME/.gemini/config/plugins/governance" ] && DIRS_TO_REMOVE+=("$RESOLVED_HOME/.gemini/config/plugins/governance")
      [ -d "$RESOLVED_HOME/.gemini/config/plugins/immune_system" ] && DIRS_TO_REMOVE+=("$RESOLVED_HOME/.gemini/config/plugins/immune_system")
      ;;
    kiro)
      for f in "$RESOLVED_HOME"/.kiro/steering/*.md; do
        [ -f "$f" ] && FILES_TO_REMOVE+=("$f")
      done
      for d in "$RESOLVED_HOME"/.kiro/skills/*; do
        [ -d "$d" ] && DIRS_TO_REMOVE+=("$d")
      done
      [ -d "$RESOLVED_HOME/.kiro/hooks" ] && DIRS_TO_REMOVE+=("$RESOLVED_HOME/.kiro/hooks")
      [ -f "$RESOLVED_HOME/.kiro/settings/mcp.json" ] && FILES_TO_REMOVE+=("$RESOLVED_HOME/.kiro/settings/mcp.json")
      ;;
    copilot)
      [ -d "$REPO_DIR/.github/instructions" ] && DIRS_TO_REMOVE+=("$REPO_DIR/.github/instructions")
      if [ -f "$RESOLVED_HOME/copilot-instructions.md" ]; then
        MODIFY_FILES+=("$RESOLVED_HOME/copilot-instructions.md")
      fi
      ;;
    claude)
      if [ -f "$(pwd)/CLAUDE.md" ]; then
        MODIFY_FILES+=("$(pwd)/CLAUDE.md")
      fi
      if [ -f "$RESOLVED_HOME/.claude/CLAUDE.md" ]; then
        MODIFY_FILES+=("$RESOLVED_HOME/.claude/CLAUDE.md")
      fi
      [ -f "$(pwd)/.mcp.json" ] && FILES_TO_REMOVE+=("$(pwd)/.mcp.json")
      ;;
    mcp)
      [ -f "$(pwd)/.mcp.json" ] && FILES_TO_REMOVE+=("$(pwd)/.mcp.json")
      ;;
  esac
fi

# ── User-Authored Data ────────────────────────────────────────────
# Cells, fitness history and snapshots are authored by the user, not installed
# by install.sh. Uninstalling a tool must not delete the user's work, so these
# are PRESERVED unless --purge-data is passed explicitly.
PRESERVED_PATHS=()
[ -d "$REPO_DIR/.soma/cells" ] && PRESERVED_PATHS+=("$REPO_DIR/.soma/cells")
[ -f "$REPO_DIR/fitness.jsonl" ] && PRESERVED_PATHS+=("$REPO_DIR/fitness.jsonl")
[ -d "$REPO_DIR/docs/snapshots" ] && PRESERVED_PATHS+=("$REPO_DIR/docs/snapshots")

if [ "$PURGE_DATA" = "true" ]; then
  if [ -d "$REPO_DIR/.soma/cells" ]; then
    DIRS_TO_REMOVE+=("$REPO_DIR/.soma/cells")
  fi
  [ -f "$REPO_DIR/fitness.jsonl" ] && FILES_TO_REMOVE+=("$REPO_DIR/fitness.jsonl")
  if [ -d "$REPO_DIR/docs/snapshots" ]; then
    DIRS_TO_REMOVE+=("$REPO_DIR/docs/snapshots")
  fi
  PRESERVED_PATHS=()
fi

# soma.conf is user configuration. Listed separately so the plan can label it
# as such instead of burying it among installed artifacts.
CONFIG_TO_REMOVE=()
if [ "$KEEP_CONFIG" = "false" ] && [ -f "$REPO_DIR/soma.conf" ]; then
  CONFIG_TO_REMOVE+=("$REPO_DIR/soma.conf")
fi

# ── Reconcile the Plan With Disk ──────────────────────────────────
# A manifest entry recorded as a file can exist as a directory, or be gone. The
# plan printed "[FILE]" for everything while the removal loop was [ -f ]-guarded,
# so directories were advertised as deletions and then silently left in place.
# Note: ${arr[@]+"${arr[@]}"} — on Bash 3.2, "${arr[@]}" on an empty array is
# fatal under `set -u`, which is why this script used to disable `set -u` across
# the entire removal section.
REAL_FILES=()
REAL_DIRS=()
for p in ${FILES_TO_REMOVE[@]+"${FILES_TO_REMOVE[@]}"} ${DIRS_TO_REMOVE[@]+"${DIRS_TO_REMOVE[@]}"}; do
  if [ -d "$p" ]; then
    REAL_DIRS+=("$p")
  elif [ -f "$p" ]; then
    REAL_FILES+=("$p")
  fi
done
FILES_TO_REMOVE=(${REAL_FILES[@]+"${REAL_FILES[@]}"})
DIRS_TO_REMOVE=(${REAL_DIRS[@]+"${REAL_DIRS[@]}"})

REAL_MOD=()
for m in ${MODIFY_FILES[@]+"${MODIFY_FILES[@]}"}; do
  [ -f "$m" ] && REAL_MOD+=("$m")
done
MODIFY_FILES=(${REAL_MOD[@]+"${REAL_MOD[@]}"})

echo ""
echo "The following will be removed/modified:"
for f in ${FILES_TO_REMOVE[@]+"${FILES_TO_REMOVE[@]}"}; do echo "  - [FILE] $f"; done
for d in ${DIRS_TO_REMOVE[@]+"${DIRS_TO_REMOVE[@]}"}; do echo "  - [DIR]  $d"; done
for m in ${MODIFY_FILES[@]+"${MODIFY_FILES[@]}"}; do echo "  - [MOD]  $m (remove soma sections, keep the rest)"; done
for c in ${CONFIG_TO_REMOVE[@]+"${CONFIG_TO_REMOVE[@]}"}; do echo "  - [USER CONFIG] $c (pass --keep-config to keep it)"; done

PLAN_COUNT=$(( ${#FILES_TO_REMOVE[@]} + ${#DIRS_TO_REMOVE[@]} + ${#MODIFY_FILES[@]} + ${#CONFIG_TO_REMOVE[@]} ))
if [ "$PLAN_COUNT" -eq 0 ]; then
  echo "Nothing to remove."
  exit 0
fi

if [ ${#PRESERVED_PATHS[@]} -gt 0 ]; then
  echo ""
  echo "Preserved (user-authored — pass --purge-data to remove):"
  for p in ${PRESERVED_PATHS[@]+"${PRESERVED_PATHS[@]}"}; do echo "  - [KEEP] $p"; done
fi

if [ "$DRY_RUN" = "false" ] && [ "$FORCE" = "false" ]; then
  # `read -p` returns 1 at EOF, and under `set -e` that aborted the script with
  # a bare exit 1 in CI, containers, or `curl | bash`. Abort explicitly instead.
  if [ ! -t 0 ]; then
    echo ""
    log_error "Confirmation required but stdin is not a terminal."
    log_error "Aborting without removing anything. Re-run with --force, or --dry-run to preview."
    exit 2
  fi
  echo ""
  read -r -p "Proceed with deletion? (y/N): " confirm
  if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
  fi
fi

if [ "$DRY_RUN" = "true" ]; then
  # Preview the restore mapping here. The old dry-run preview lived inside the
  # restore block further down, which this early exit made unreachable.
  if [ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR" ]; then
    echo ""
    echo "Would offer to restore from: $BACKUP_DIR"
    case "$PLATFORM" in
      gemini)
        echo "  $BACKUP_DIR/genome     -> $RESOLVED_HOME/.gemini/config/rules"
        echo "  $BACKUP_DIR/organs     -> $RESOLVED_HOME/.gemini/config/skills"
        echo "  $BACKUP_DIR/governance -> $RESOLVED_HOME/.gemini/config/plugins/governance"
        ;;
      kiro)
        echo "  $BACKUP_DIR/genome -> $RESOLVED_HOME/.kiro/steering"
        echo "  $BACKUP_DIR/organs -> $RESOLVED_HOME/.kiro/skills"
        echo "  $BACKUP_DIR/hooks  -> $RESOLVED_HOME/.kiro/hooks"
        ;;
      copilot)
        echo "  $BACKUP_DIR/copilot-instructions.md -> $RESOLVED_HOME/copilot-instructions.md"
        ;;
      claude)
        if [ "$MANIFEST_SCOPE" = "local" ]; then
          echo "  $BACKUP_DIR/CLAUDE.md -> $(pwd)/CLAUDE.md"
        else
          echo "  $BACKUP_DIR/CLAUDE.md -> $RESOLVED_HOME/.claude/CLAUDE.md"
        fi
        echo "  $BACKUP_DIR/.mcp.json -> $(pwd)/.mcp.json"
        ;;
      mcp)
        echo "  $BACKUP_DIR/.mcp.json -> $(pwd)/.mcp.json"
        ;;
    esac
  fi
  echo ""
  echo "Dry-run complete. Nothing was removed."
  exit 0
fi

# Inventory in-place backups BEFORE removing anything: cleaning a [MOD] file
# writes a fresh .bak containing Soma content, and the parent of a removed file
# may disappear.
for f in ${FILES_TO_REMOVE[@]+"${FILES_TO_REMOVE[@]}"}; do
  if [ -L "$f" ]; then
    rm -f "$f" && echo "Removed symlink $f"
  elif [ -f "$f" ]; then
    rm -f "$f" && echo "Removed $f"
  fi
done
for d in ${DIRS_TO_REMOVE[@]+"${DIRS_TO_REMOVE[@]}"}; do
  if [ -L "$d" ]; then
    rm -f "$d" && echo "Removed directory symlink $d"
  elif [ -d "$d" ]; then
    rm -rf "$d" && echo "Removed $d/"
  fi
done

for m in ${MODIFY_FILES[@]+"${MODIFY_FILES[@]}"}; do
  if [ -f "$m" ]; then
    sed -i.bak '/^# Copilot Global Instructions/,$d' "$m" && rm -f "$m.bak"
    sed -i.bak '/^# Soma Governance Rules/,$d' "$m" && rm -f "$m.bak"
    # Truncating at our header can leave an empty file behind. Remove it only if
    # nothing but whitespace remains, so a user's own content is never lost.
    if [ ! -s "$m" ] || [ -z "$(tr -d '[:space:]' < "$m")" ]; then
      rm -f "$m"
      echo "Cleaned and removed $m (contained only soma content)"
    else
      echo "Cleaned $m"
    fi
  fi
done

for c in ${CONFIG_TO_REMOVE[@]+"${CONFIG_TO_REMOVE[@]}"}; do
  [ -f "$c" ] && rm -f "$c" && echo "Removed user config $c"
done

# Clean soma hooks from claude settings.json, but only when one is actually
# present. The previous version rewrote the user's settings.json through jq
# unconditionally and printed "Cleaned ..." even when nothing matched — and on a
# jq failure it left a stray .tmp behind while still claiming success.
for settings_file in "$(pwd)/.claude/settings.json" "$RESOLVED_HOME/.claude/settings.json"; do
  if [ -f "$settings_file" ] && command -v jq >/dev/null 2>&1; then
    if jq -e '.hooks.soma? // empty' "$settings_file" >/dev/null 2>&1; then
      if jq 'del(.hooks.soma)' "$settings_file" > "$settings_file.tmp" 2>/dev/null; then
        mv "$settings_file.tmp" "$settings_file"
        echo "Cleaned soma hooks from $settings_file"
      else
        rm -f "$settings_file.tmp"
        log_warn "Could not rewrite $settings_file — left unchanged."
      fi
    fi
  fi
done

# If manifest file exists and wasn't caught by the array (e.g. empty)
[ -f "$MANIFEST_PATH" ] && rm -f "$MANIFEST_PATH"

if [ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR" ]; then
  echo ""
  if [ "$NO_RESTORE" = "true" ]; then
    echo "Skipping restore (--no-restore). Backup left at $BACKUP_DIR"
  elif [ ! -t 0 ]; then
    # Previously `read -p` here aborted the script under `set -e` at EOF.
    echo "Not restoring: stdin is not a terminal."
    echo "Backup preserved at $BACKUP_DIR — copy from it manually if needed."
  else
      # --force skips the DELETION prompt only. It used to also skip restore,
      # so the one flag meant for automation disabled recovery.
      read -r -p "Restore previous configuration from backup? [y/N] " restore_confirm
      if [[ "$restore_confirm" =~ ^[Yy]$ ]]; then
        echo "Restoring from $BACKUP_DIR..."
        case "$PLATFORM" in
          gemini)
            # install.sh creates $BACKUP_DIR/{genome,organs,governance}. This
            # block used to read rules/ and skills/, which never exist, so
            # restore silently did nothing and still printed "Restore complete."
            restore_dir_contents "$BACKUP_DIR/genome" "$RESOLVED_HOME/.gemini/config/rules"
            restore_dir_contents "$BACKUP_DIR/organs" "$RESOLVED_HOME/.gemini/config/skills"
            restore_dir_contents "$BACKUP_DIR/governance" "$RESOLVED_HOME/.gemini/config/plugins/governance"
            ;;
          kiro)
            restore_dir_contents "$BACKUP_DIR/genome" "$RESOLVED_HOME/.kiro/steering"
            restore_dir_contents "$BACKUP_DIR/organs" "$RESOLVED_HOME/.kiro/skills"
            restore_dir_contents "$BACKUP_DIR/hooks" "$RESOLVED_HOME/.kiro/hooks"
            ;;
          copilot)
            restore_file "$BACKUP_DIR/copilot-instructions.md" "$RESOLVED_HOME/copilot-instructions.md"
            ;;
          claude)
            # A local install backed up the project CLAUDE.md, so restore it to
            # the scope it came from rather than always to the global home.
            if [ "$MANIFEST_SCOPE" = "local" ]; then
              restore_file "$BACKUP_DIR/CLAUDE.md" "$(pwd)/CLAUDE.md"
            else
              restore_file "$BACKUP_DIR/CLAUDE.md" "$RESOLVED_HOME/.claude/CLAUDE.md"
            fi
            restore_file "$BACKUP_DIR/.mcp.json" "$(pwd)/.mcp.json"
            ;;
          mcp)
            restore_file "$BACKUP_DIR/.mcp.json" "$(pwd)/.mcp.json"
            ;;
        esac
        if [ "$RESTORED_ANY" = "true" ]; then
          echo "Restore complete."
        else
          # Do not claim success when nothing was found to restore.
          log_warn "Nothing was restored: $BACKUP_DIR held no recognised payload."
        fi
      else
        echo "Skipping restore. Backup left at $BACKUP_DIR"
      fi
  fi
fi

echo "Uninstall complete."
