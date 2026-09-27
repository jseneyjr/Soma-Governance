#!/usr/bin/env bash
# AI Steering Rules — Shared Library
# Sourced by install.sh and platform wrappers.
# Provides config loading, validation, backup, and formatting utilities.

set -euo pipefail

# ── Colors & Formatting ──────────────────────────────────────────
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

log_info()  { echo -e "  ${GREEN}✅${NC} $*"; }
log_warn()  { echo -e "  ${YELLOW}⚠${NC}  $*"; }
log_skip()  { echo -e "  ${CYAN}⏭${NC}  $*"; }
log_error() { echo -e "  ${RED}❌${NC} $*" >&2; }

# ── Symlink-Safe Script Directory Resolution ─────────────────────
# Resolves the true directory of the calling script, even through symlinks.
# Thorns fix #3: naive dirname fails when script is symlinked.
resolve_script_dir() {
  local prg="${1:-${BASH_SOURCE[1]}}"
  while [ -h "$prg" ]; do
    local dir
    dir="$(cd -P "$(dirname "$prg")" && pwd)"
    prg="$(readlink "$prg")"
    [[ $prg != /* ]] && prg="$dir/$prg"
  done
  cd -P "$(dirname "$prg")" && pwd
}

# ── Configuration Loading ────────────────────────────────────────
# Loads steering.conf if present. Environment variables take precedence.
load_config() {
  local repo_dir="$1"
  local conf="$repo_dir/steering.conf"

  if [ -f "$conf" ]; then
    # Source config, but don't override existing env vars
    # (Thorns fix #2: preserve pre-set environment variables)
    set -a
    # shellcheck disable=SC1090
    source "$conf"
    set +a
  fi

  # Apply defaults for any unset variables
  TEAM_SIZE="${TEAM_SIZE:-solo}"
  GIT_STRATEGY="${GIT_STRATEGY:-trunk}"
  APPROVAL_CHAIN="${APPROVAL_CHAIN:-none}"
  RULES_SUBSET="${RULES_SUBSET:-all}"
  ENABLE_HOOKS="${ENABLE_HOOKS:-true}"
  # Thorns fix #6: namespaced to avoid Docker/CI PLATFORM collision
  STEERING_PLATFORM="${STEERING_PLATFORM:-gemini}"
}

# ── Enum Validation ──────────────────────────────────────────────
# Validates a value against a whitelist of allowed values.
validate_enum() {
  local name="$1"
  local value="$2"
  shift 2
  local allowed=("$@")

  for v in "${allowed[@]}"; do
    [ "$value" = "$v" ] && return 0
  done

  log_error "Invalid $name: '$value' (allowed: ${allowed[*]})"
  exit 1
}

# ── Validate All Configuration ───────────────────────────────────
validate_config() {
  validate_enum "TEAM_SIZE" "$TEAM_SIZE" solo small team enterprise
  validate_enum "GIT_STRATEGY" "$GIT_STRATEGY" trunk feature-branch gitflow
  validate_enum "APPROVAL_CHAIN" "$APPROVAL_CHAIN" none peer lead
  validate_enum "RULES_SUBSET" "$RULES_SUBSET" all core minimal
  validate_enum "ENABLE_HOOKS" "$ENABLE_HOOKS" true false
  validate_enum "STEERING_PLATFORM" "$STEERING_PLATFORM" gemini kiro copilot
}

# ── Rule Subset Resolution ───────────────────────────────────────
# Sets RULE_LIST based on RULES_SUBSET. Empty = install all.
resolve_subset() {
  case "$RULES_SUBSET" in
    minimal) RULE_LIST="providence.md subagent-delegation.md destructive-ops.md" ;;
    core)    RULE_LIST="providence.md cost-optimization.md subagent-delegation.md testing.md git-workflow.md destructive-ops.md" ;;
    all)     RULE_LIST="" ;;
  esac
}

# ── Rule Inclusion Check ─────────────────────────────────────────
# Returns 0 if the rule should be installed, 1 if skipped.
should_install() {
  local name="$1"
  # Empty RULE_LIST = install everything
  [ -z "$RULE_LIST" ] && return 0
  # Use -- to prevent filenames like -rf from being parsed as grep options
  echo "$RULE_LIST" | grep -qw -- "$name"
}

# ── File Backup (Timestamped) ────────────────────────────────────
# Creates a timestamped backup to prevent clobbering.
backup_file() {
  local target="$1"
  if [ -f "$target" ]; then
    local ts
    ts="$(date +%s 2>/dev/null || echo 'bak')"
    local backup="${target}.bak.${ts}"
    cp -- "$target" "$backup"
    log_warn "$(basename "$target") backed up to $(basename "$backup")"
  fi
}

# ── Directory Backup (Safe) ──────────────────────────────────────
# Removes existing .bak dir first to prevent recursive nesting.
backup_dir() {
  local target="$1"
  if [ -d "$target" ]; then
    local ts
    ts="$(date +%s 2>/dev/null || echo 'bak')"
    local backup="${target}.bak.${ts}"
    # Remove stale backup if exists to prevent nesting
    [ -d "$backup" ] && rm -rf -- "$backup"
    cp -r -- "$target" "$backup"
    log_warn "$(basename "$target")/ backed up to $(basename "$backup")/"
  fi
}

# ── Portable Frontmatter Strip ───────────────────────────────────
# Strips YAML frontmatter (--- delimited) using awk (not BSD-incompatible sed).
strip_frontmatter() {
  awk '
    BEGIN { in_front=0; found=0 }
    NR==1 && /^---$/ { in_front=1; next }
    in_front && /^---$/ { in_front=0; found=1; next }
    !in_front && found { print }
    !in_front && !found { print }
  '
}

# ── Team Override Application ────────────────────────────────────
# Appends team/gitflow/approval overrides to installed rule copies.
# Idempotent: checks for existing override marker before appending.
apply_team_overrides() {
  local rules_dir="$1"

  # Team branching override
  local git_wf="$rules_dir/git-workflow.md"
  [ -f "$rules_dir/git-workflow.instructions.md" ] && git_wf="$rules_dir/git-workflow.instructions.md"

  if [ "$TEAM_SIZE" != "solo" ] && { [ -f "$rules_dir/git-workflow.md" ] || [ -f "$rules_dir/git-workflow.instructions.md" ]; }; then
    if ! grep -q "## Team Workflow Overrides" "$git_wf" 2>/dev/null; then
      cat >> "$git_wf" << 'TEAM_OVERRIDE'

## Team Workflow Overrides (auto-generated)
- **All changes via feature branches**: Direct commits to main are prohibited for teams.
- **PR descriptions**: Every PR must include a summary of what changed and why.
- **Review required**: At least one peer review before merge.
- **Branch naming**: Use `feature/<name>`, `fix/<name>`, `chore/<name>` prefixes.
TEAM_OVERRIDE
      log_info "$(basename "$git_wf"): team branching enforced"
    fi
  fi

  # Gitflow override
  if [ "$GIT_STRATEGY" = "gitflow" ] && { [ -f "$rules_dir/git-workflow.md" ] || [ -f "$rules_dir/git-workflow.instructions.md" ]; }; then
    if ! grep -q "## Gitflow Overrides" "$git_wf" 2>/dev/null; then
      cat >> "$git_wf" << 'GITFLOW_OVERRIDE'

## Gitflow Overrides (auto-generated)
- **develop branch**: All feature branches merge to `develop`, not `main`.
- **release branches**: Cut `release/<version>` from `develop` when preparing a release.
- **hotfix branches**: Branch from `main` as `hotfix/<name>`, merge back to both `main` and `develop`.
GITFLOW_OVERRIDE
      log_info "$(basename "$git_wf"): gitflow strategy applied"
    fi
  fi

  # Approval chain override (quoted heredoc — Thorns fix: prevents prompt injection)
  local dest_ops="$rules_dir/destructive-ops.md"
  [ -f "$rules_dir/destructive-ops.instructions.md" ] && dest_ops="$rules_dir/destructive-ops.instructions.md"

  if [ "$APPROVAL_CHAIN" != "none" ] && { [ -f "$rules_dir/destructive-ops.md" ] || [ -f "$rules_dir/destructive-ops.instructions.md" ]; }; then
    if ! grep -q "## Approval Chain Override" "$dest_ops" 2>/dev/null; then
      local chain="$APPROVAL_CHAIN"
      cat >> "$dest_ops" << APPROVAL_OVERRIDE

## Approval Chain Override (auto-generated)
- **Approval required**: All destructive operations require ${chain} approval before execution.
- **Document approver**: When executing destructive ops, cite who approved and when.
APPROVAL_OVERRIDE
      log_info "$(basename "$dest_ops"): $APPROVAL_CHAIN approval chain enforced"
    fi
  fi
}

# ── Hooks Installation ───────────────────────────────────────────
# Renders hooks.json.template with resolved paths and installs to target.
install_hooks() {
  local repo_dir="$1"
  local target_dir="$2"
  local template="$repo_dir/hooks.json.template"
  local scripts_dir="$repo_dir/scripts"
  local target="$target_dir/hooks.json"

  if [ ! -f "$template" ]; then
    log_warn "hooks.json.template not found, skipping hooks installation"
    return 0
  fi

  mkdir -p "$target_dir"

  # Thorns fix #4: Use python3 for safe JSON templating instead of sed
  if command -v python3 &>/dev/null; then
    python3 -c "
import sys
template = open(sys.argv[1]).read()
rendered = template.replace('{{SCRIPTS_DIR}}', sys.argv[2])
print(rendered, end='')
" "$template" "$scripts_dir" > "$target"

    # Validate rendered JSON
    if python3 -m json.tool "$target" > /dev/null 2>&1; then
      log_info "hooks.json installed to $(basename "$target_dir")/"
    else
      log_error "hooks.json rendering produced invalid JSON"
      rm -f "$target"
      return 1
    fi
  else
    log_warn "python3 not found, skipping hooks installation"
    return 0
  fi
}
