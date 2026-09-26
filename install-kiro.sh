#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/rules"
RULES_DIR="$HOME/.kiro/steering"

# ── Config (from environment/Makefile, or defaults) ──
TEAM_SIZE="${TEAM_SIZE:-solo}"
GIT_STRATEGY="${GIT_STRATEGY:-trunk}"
RULES_SUBSET="${RULES_SUBSET:-all}"

# ── Rule Subset Selection ──
case "$RULES_SUBSET" in
  minimal) RULE_LIST="providence.md subagent-delegation.md destructive-ops.md" ;;
  core)    RULE_LIST="providence.md cost-optimization.md subagent-delegation.md testing.md git-workflow.md destructive-ops.md" ;;
  all)     RULE_LIST="" ;;  # empty = install everything
  *)       echo "❌ Unknown RULES_SUBSET: $RULES_SUBSET"; exit 1 ;;
esac

echo "Installing steering rules for Kiro..."
echo "  Source: $SOURCE_DIR"
echo "  Target: $RULES_DIR"
echo "  Config: TEAM_SIZE=$TEAM_SIZE GIT_STRATEGY=$GIT_STRATEGY RULES_SUBSET=$RULES_SUBSET"
echo ""

mkdir -p "$RULES_DIR"

# Mapping: Gemini triggers -> Kiro inclusion modes
# always_on -> always
# model_decision -> manual (user references via #rulename)

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

  # Convert Gemini trigger syntax to Kiro inclusion syntax
  sed -e 's/^trigger: always_on$/inclusion: always/' \
      -e 's/^trigger: model_decision$/inclusion: manual/' \
      "$rule" > "$RULES_DIR/$name"

  echo "  ✅ $name"
  count=$((count + 1))
done

echo ""
echo "Done! Installed $count rules to $RULES_DIR"
if [ "$RULES_SUBSET" != "all" ]; then
  echo "  ($skipped rules skipped — not in $RULES_SUBSET subset)"
fi
echo ""
echo "Rules with 'inclusion: always' are active on every interaction."
echo "Rules with 'inclusion: manual' can be referenced in chat via #rulename, e.g.:"
echo "  #testing  #documentation  #destructive-ops  #feature-specs  #architectural-tenets"
