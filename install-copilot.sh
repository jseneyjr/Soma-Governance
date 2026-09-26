#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/rules"

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

# Copilot supports two modes:
# 1. Global: a single copilot-instructions.md file
# 2. Per-project: .github/copilot-instructions.md or .github/instructions/*.instructions.md
#
# This script generates a GLOBAL instructions file by concatenating all rules.
# Copilot doesn't support conditional triggers, so all rules are always active.

MODE="${1:-global}"

if [ "$MODE" = "project" ]; then
  TARGET_DIR=".github/instructions"
  echo "Installing steering rules for GitHub Copilot (project mode)..."
  echo "  Source: $SOURCE_DIR"
  echo "  Target: $TARGET_DIR"
  echo "  Config: TEAM_SIZE=$TEAM_SIZE GIT_STRATEGY=$GIT_STRATEGY RULES_SUBSET=$RULES_SUBSET"
  echo ""

  mkdir -p "$TARGET_DIR"

  count=0
  skipped=0
  for rule in "$SOURCE_DIR"/*.md; do
    filename="$(basename "$rule")"

    # Skip rules not in the selected subset
    if [ -n "$RULE_LIST" ] && ! echo "$RULE_LIST" | grep -qw "$filename"; then
      echo "  ⏭  $filename (not in $RULES_SUBSET subset)"
      skipped=$((skipped + 1))
      continue
    fi

    name="$(basename "$rule" .md)"
    target="$TARGET_DIR/${name}.instructions.md"

    if [ -f "$target" ]; then
      echo "  ⚠  ${name}.instructions.md already exists, backing up"
      cp "$target" "${target}.bak"
    fi

    # Strip YAML frontmatter and write as Copilot instruction file
    sed '1{/^---$/!q;};1,/^---$/d' "$rule" > "$target"
    echo "  ✅ ${name}.instructions.md"
    count=$((count + 1))
  done

  echo ""
  echo "Done! Installed $count instruction files to $TARGET_DIR"
  if [ "$RULES_SUBSET" != "all" ]; then
    echo "  ($skipped rules skipped — not in $RULES_SUBSET subset)"
  fi
  echo "Commit .github/instructions/ to your repo to share with your team."

elif [ "$MODE" = "global" ]; then
  # Detect OS for global instructions path
  if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
    TARGET_FILE="$USERPROFILE/copilot-instructions.md"
  else
    TARGET_FILE="$HOME/copilot-instructions.md"
  fi

  echo "Installing steering rules for GitHub Copilot (global mode)..."
  echo "  Source: $SOURCE_DIR"
  echo "  Target: $TARGET_FILE"
  echo "  Config: TEAM_SIZE=$TEAM_SIZE GIT_STRATEGY=$GIT_STRATEGY RULES_SUBSET=$RULES_SUBSET"
  echo ""

  if [ -f "$TARGET_FILE" ]; then
    echo "  ⚠  Existing file found, backing up to ${TARGET_FILE}.bak"
    cp "$TARGET_FILE" "${TARGET_FILE}.bak"
  fi

  # Concatenate all rules into a single file, stripping YAML frontmatter
  echo "# Copilot Global Instructions" > "$TARGET_FILE"
  echo "" >> "$TARGET_FILE"
  echo "> Auto-generated from gemini-steering-rules. Do not edit directly." >> "$TARGET_FILE"
  echo "" >> "$TARGET_FILE"

  count=0
  skipped=0
  for rule in "$SOURCE_DIR"/*.md; do
    filename="$(basename "$rule")"

    # Skip rules not in the selected subset
    if [ -n "$RULE_LIST" ] && ! echo "$RULE_LIST" | grep -qw "$filename"; then
      echo "  ⏭  $filename (not in $RULES_SUBSET subset)"
      skipped=$((skipped + 1))
      continue
    fi

    echo "---" >> "$TARGET_FILE"
    echo "" >> "$TARGET_FILE"
    # Strip YAML frontmatter
    sed '1{/^---$/!q;};1,/^---$/d' "$rule" >> "$TARGET_FILE"
    echo "" >> "$TARGET_FILE"
    echo "  ✅ $filename"
    count=$((count + 1))
  done

  echo ""
  echo "Done! All rules merged into $TARGET_FILE"
  if [ "$RULES_SUBSET" != "all" ]; then
    echo "  ($skipped rules skipped — not in $RULES_SUBSET subset)"
  fi
  echo "Enable 'Custom Instructions' in your IDE's Copilot settings to activate."

else
  echo "Usage: ./install-copilot.sh [global|project]"
  echo ""
  echo "  global   Merge all rules into ~/copilot-instructions.md (default)"
  echo "  project  Create individual .github/instructions/*.instructions.md files"
  exit 1
fi
