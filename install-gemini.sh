#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/rules"
RULES_DIR="$HOME/.gemini/config/rules"
SKILLS_DIR="$HOME/.gemini/config/skills"
SKILLS_SOURCE="$SCRIPT_DIR/skills"

# ── Config (from environment/Makefile, or defaults) ──
TEAM_SIZE="${TEAM_SIZE:-solo}"
GIT_STRATEGY="${GIT_STRATEGY:-trunk}"
AI_USAGE="${AI_USAGE:-individual}"
APPROVAL_CHAIN="${APPROVAL_CHAIN:-none}"
TECH_STACK="${TECH_STACK:-python}"
RULES_SUBSET="${RULES_SUBSET:-all}"
ENABLE_HOOKS="${ENABLE_HOOKS:-true}"

# ── Rule Subset Selection ──
case "$RULES_SUBSET" in
  minimal) RULE_LIST="providence.md subagent-delegation.md destructive-ops.md" ;;
  core)    RULE_LIST="providence.md cost-optimization.md subagent-delegation.md testing.md git-workflow.md destructive-ops.md" ;;
  all)     RULE_LIST="" ;;  # empty = install everything
  *)       echo "❌ Unknown RULES_SUBSET: $RULES_SUBSET"; exit 1 ;;
esac

echo "Installing Gemini steering rules..."
echo "  Source: $SOURCE_DIR"
echo "  Target: $RULES_DIR"
echo "  Config: TEAM_SIZE=$TEAM_SIZE GIT_STRATEGY=$GIT_STRATEGY RULES_SUBSET=$RULES_SUBSET"
echo ""

mkdir -p "$RULES_DIR"

# ── Install Rules ──
count=0
skipped=0
for rule in "$SOURCE_DIR"/*.md; do
  name="$(basename "$rule")"

  # Skip rules not in the selected subset
  if [ -n "$RULE_LIST" ] && ! echo "$RULE_LIST" | grep -qw "$name"; then
    echo "  ⏭  $name (not in $RULES_SUBSET subset)"
    skipped=$((skipped + 1))
    continue
  fi

  if [ -f "$RULES_DIR/$name" ]; then
    echo "  ⚠  $name already exists, backing up to $name.bak"
    cp "$RULES_DIR/$name" "$RULES_DIR/$name.bak"
  fi
  cp "$rule" "$RULES_DIR/$name"
  echo "  ✅ $name"
  count=$((count + 1))
done

# ── Install Skills (if directory exists) ──
skill_count=0
if [ -d "$SKILLS_SOURCE" ]; then
  mkdir -p "$SKILLS_DIR"
  for skill in "$SKILLS_SOURCE"/*/; do
    skill_name="$(basename "$skill")"
    if [ -d "$SKILLS_DIR/$skill_name" ]; then
      echo "  ⚠  skill/$skill_name already exists, backing up"
      cp -r "$SKILLS_DIR/$skill_name" "$SKILLS_DIR/${skill_name}.bak"
    fi
    cp -r "$skill" "$SKILLS_DIR/$skill_name"
    echo "  ✅ skill/$skill_name"
    skill_count=$((skill_count + 1))
  done
fi

# ── Team-Specific Overrides ──
if [ "$TEAM_SIZE" != "solo" ] && [ -f "$RULES_DIR/git-workflow.md" ]; then
  echo ""
  echo "Applying team overrides (TEAM_SIZE=$TEAM_SIZE)..."
  cat >> "$RULES_DIR/git-workflow.md" << 'TEAM_OVERRIDE'

## Team Workflow Overrides (auto-generated)
- **All changes via feature branches**: Direct commits to main are prohibited for teams.
- **PR descriptions**: Every PR must include a summary of what changed and why.
- **Review required**: At least one peer review before merge.
- **Branch naming**: Use `feature/<name>`, `fix/<name>`, `chore/<name>` prefixes.
TEAM_OVERRIDE
  echo "  ✅ git-workflow.md: team branching enforced"
fi

# ── Git Strategy Override ──
if [ "$GIT_STRATEGY" = "gitflow" ] && [ -f "$RULES_DIR/git-workflow.md" ]; then
  cat >> "$RULES_DIR/git-workflow.md" << 'GITFLOW_OVERRIDE'

## Gitflow Overrides (auto-generated)
- **develop branch**: All feature branches merge to `develop`, not `main`.
- **release branches**: Cut `release/<version>` from `develop` when preparing a release.
- **hotfix branches**: Branch from `main` as `hotfix/<name>`, merge back to both `main` and `develop`.
GITFLOW_OVERRIDE
  echo "  ✅ git-workflow.md: gitflow strategy applied"
fi

# ── Approval Chain Override ──
if [ "$APPROVAL_CHAIN" != "none" ] && [ -f "$RULES_DIR/destructive-ops.md" ]; then
  echo ""
  echo "Applying approval chain ($APPROVAL_CHAIN)..."
  cat >> "$RULES_DIR/destructive-ops.md" << APPROVAL_OVERRIDE

## Approval Chain Override (auto-generated)
- **Approval required**: All destructive operations require ${APPROVAL_CHAIN} approval before execution.
- **Document approver**: When executing destructive ops, cite who approved and when.
APPROVAL_OVERRIDE
  echo "  ✅ destructive-ops.md: $APPROVAL_CHAIN approval chain enforced"
fi

echo ""
echo "Done! Installed $count rules, $skill_count skills to $RULES_DIR"
[ "$skipped" -gt 0 ] && echo "  ($skipped rules skipped — not in $RULES_SUBSET subset)"
echo "These will take effect on your next Gemini conversation turn."
