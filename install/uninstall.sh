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

source "$REPO_DIR/scripts/common.sh"
load_config "$REPO_DIR"

DRY_RUN=false
KEEP_CONFIG=false
FORCE=false
POSITIONAL_ARGS=()

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --keep-config) KEEP_CONFIG=true ;;
    --force) FORCE=true ;;
    *) POSITIONAL_ARGS+=("$arg") ;;
  esac
done

PLATFORM="${POSITIONAL_ARGS[0]:-${STEERING_PLATFORM:-gemini}}"

DETECTED_OS="$(detect_os)"
RESOLVED_HOME="$(resolve_home "$DETECTED_OS")"
MANIFEST_PATH="$RESOLVED_HOME/.prism-ai-steering/manifest.json"
if [ -f "$(pwd)/.prism/manifest.json" ]; then
  MANIFEST_PATH="$(pwd)/.prism/manifest.json"
fi

MANIFEST_EXISTS=false
if [ -f "$MANIFEST_PATH" ]; then
  MANIFEST_EXISTS=true
fi

echo "Uninstalling Prism AI Steering ($PLATFORM)..."
[ "$DRY_RUN" = "true" ] && echo "Mode: DRY-RUN (no files will be deleted)"

FILES_TO_REMOVE=()
DIRS_TO_REMOVE=()
MODIFY_FILES=()
BACKUP_DIR=""

if [ "$MANIFEST_EXISTS" = "true" ]; then
  echo "Found manifest at $MANIFEST_PATH. Reading paths..."
  BACKUP_DIR=$(python3 -c "import json, sys; d=json.load(open('$MANIFEST_PATH')); print(d.get('backup_dir', ''))" 2>/dev/null || true)
  
  while IFS= read -r f; do
    if [[ "$f" == *"/copilot-instructions.md" ]]; then
      MODIFY_FILES+=("$f")
    elif [ -n "$f" ]; then
      FILES_TO_REMOVE+=("$f")
    fi
  done < <(python3 -c "import json, sys; d=json.load(open('$MANIFEST_PATH')); print('\n'.join(d.get('files', [])))")
  
  while IFS= read -r d; do
    [ -n "$d" ] && DIRS_TO_REMOVE+=("$d")
  done < <(python3 -c "import json, sys; d=json.load(open('$MANIFEST_PATH')); print('\n'.join(d.get('skills', [])))")
  
  while IFS= read -r h; do
    [ -n "$h" ] && FILES_TO_REMOVE+=("$h")
  done < <(python3 -c "import json, sys; d=json.load(open('$MANIFEST_PATH')); print('\n'.join(d.get('hooks', [])))")
  
  FILES_TO_REMOVE+=("$MANIFEST_PATH")
else
  echo "No manifest found. Falling back to known patterns..."
  case "$PLATFORM" in
    gemini)
      for f in "$RESOLVED_HOME"/.gemini/config/rules/*.md; do
        [ -f "$f" ] && FILES_TO_REMOVE+=("$f")
      done
      for d in "$RESOLVED_HOME"/.gemini/config/skills/*; do
        [ -d "$d" ] && DIRS_TO_REMOVE+=("$d")
      done
      [ -d "$RESOLVED_HOME/.gemini/config/plugins/governance" ] && DIRS_TO_REMOVE+=("$RESOLVED_HOME/.gemini/config/plugins/governance")
      ;;
    kiro)
      for f in "$RESOLVED_HOME"/.kiro/steering/*.md; do
        [ -f "$f" ] && FILES_TO_REMOVE+=("$f")
      done
      for d in "$RESOLVED_HOME"/.kiro/skills/*; do
        [ -d "$d" ] && DIRS_TO_REMOVE+=("$d")
      done
      [ -d "$RESOLVED_HOME/.kiro/hooks" ] && DIRS_TO_REMOVE+=("$RESOLVED_HOME/.kiro/hooks")
      ;;
    copilot)
      [ -d "$REPO_DIR/.github/instructions" ] && DIRS_TO_REMOVE+=("$REPO_DIR/.github/instructions")
      if [ -f "$RESOLVED_HOME/copilot-instructions.md" ]; then
        MODIFY_FILES+=("$RESOLVED_HOME/copilot-instructions.md")
      fi
      ;;
  esac
fi

# Local cell data
if [ -d "$REPO_DIR/.prism/cells" ]; then
  for f in "$REPO_DIR"/.prism/cells/*; do
    [ -e "$f" ] && FILES_TO_REMOVE+=("$f")
  done
fi
[ -f "$REPO_DIR/fitness.jsonl" ] && FILES_TO_REMOVE+=("$REPO_DIR/fitness.jsonl")

# Local snapshots
if [ -d "$REPO_DIR/docs/snapshots" ]; then
  for f in "$REPO_DIR"/docs/snapshots/*; do
    [ -e "$f" ] && FILES_TO_REMOVE+=("$f")
  done
fi

if [ "$KEEP_CONFIG" = "false" ] && [ -f "$REPO_DIR/steering.conf" ]; then
  FILES_TO_REMOVE+=("$REPO_DIR/steering.conf")
fi

echo ""
echo "The following will be removed/modified:"
for f in "${FILES_TO_REMOVE[@]}"; do echo "  - [FILE] $f"; done
for d in "${DIRS_TO_REMOVE[@]}"; do echo "  - [DIR]  $d"; done
for m in "${MODIFY_FILES[@]}"; do echo "  - [MOD]  $m (remove prism sections)"; done

if [ ${#FILES_TO_REMOVE[@]} -eq 0 ] && [ ${#DIRS_TO_REMOVE[@]} -eq 0 ] && [ ${#MODIFY_FILES[@]} -eq 0 ]; then
  echo "Nothing to remove."
  exit 0
fi

if [ "$DRY_RUN" = "false" ] && [ "$FORCE" = "false" ]; then
  read -p "Proceed with deletion? (y/N): " confirm
  if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
  fi
fi

if [ "$DRY_RUN" = "true" ]; then
  echo "Dry-run complete."
  exit 0
fi

for f in "${FILES_TO_REMOVE[@]}"; do
  [ -f "$f" ] && rm -f "$f"
done
for d in "${DIRS_TO_REMOVE[@]}"; do
  [ -d "$d" ] && rm -rf "$d"
done

for m in "${MODIFY_FILES[@]}"; do
  if [ -f "$m" ]; then
    # Removes everything between # Copilot Global Instructions and the end (or just deletes the auto-gen stuff)
    # The install script appends to it with a comment "> Auto-generated from prism-ai-steering."
    # We will just remove lines starting from "# Copilot Global Instructions" to the end of the file.
    sed -i '/^# Copilot Global Instructions/,$d' "$m"
    echo "Cleaned $m"
  fi
done

# If manifest file exists and wasn't caught by the array (e.g. empty)
[ -f "$MANIFEST_PATH" ] && rm -f "$MANIFEST_PATH"

if [ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR" ]; then
  echo ""
  if [ "$DRY_RUN" = "true" ]; then
    echo "Dry-run: Would offer to restore from backup: $BACKUP_DIR"
    echo "Restore mapping:"
    case "$PLATFORM" in
      gemini)
        echo "  $BACKUP_DIR/rules -> $RESOLVED_HOME/.gemini/config/rules"
        echo "  $BACKUP_DIR/skills -> $RESOLVED_HOME/.gemini/config/skills"
        echo "  $BACKUP_DIR/governance -> $RESOLVED_HOME/.gemini/config/plugins/governance"
        ;;
      kiro)
        echo "  $BACKUP_DIR/steering -> $RESOLVED_HOME/.kiro/steering"
        echo "  $BACKUP_DIR/skills -> $RESOLVED_HOME/.kiro/skills"
        echo "  $BACKUP_DIR/hooks -> $RESOLVED_HOME/.kiro/hooks"
        ;;
      copilot)
        echo "  $BACKUP_DIR/copilot-instructions.md -> $RESOLVED_HOME/copilot-instructions.md"
        ;;
    esac
  else
    if [ "$FORCE" = "false" ]; then
      read -p "Restore previous configuration from backup? [y/N] " restore_confirm
      if [[ "$restore_confirm" =~ ^[Yy]$ ]]; then
        echo "Restoring from $BACKUP_DIR..."
        case "$PLATFORM" in
          gemini)
            [ -d "$BACKUP_DIR/rules" ] && cp -r "$BACKUP_DIR/rules" "$RESOLVED_HOME/.gemini/config/"
            [ -d "$BACKUP_DIR/skills" ] && cp -r "$BACKUP_DIR/skills" "$RESOLVED_HOME/.gemini/config/"
            [ -d "$BACKUP_DIR/governance" ] && cp -r "$BACKUP_DIR/governance" "$RESOLVED_HOME/.gemini/config/plugins/"
            ;;
          kiro)
            [ -d "$BACKUP_DIR/steering" ] && cp -r "$BACKUP_DIR/steering" "$RESOLVED_HOME/.kiro/"
            [ -d "$BACKUP_DIR/skills" ] && cp -r "$BACKUP_DIR/skills" "$RESOLVED_HOME/.kiro/"
            [ -d "$BACKUP_DIR/hooks" ] && cp -r "$BACKUP_DIR/hooks" "$RESOLVED_HOME/.kiro/"
            ;;
          copilot)
            [ -f "$BACKUP_DIR/copilot-instructions.md" ] && cp "$BACKUP_DIR/copilot-instructions.md" "$RESOLVED_HOME/"
            ;;
        esac
        echo "Restore complete."
      else
        echo "Skipping restore."
      fi
    else
      echo "Force mode enabled, skipping restore."
    fi
  fi
fi

echo "Uninstall complete."
