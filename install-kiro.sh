#!/usr/bin/env bash
set -euo pipefail

RULES_DIR="$HOME/.kiro/steering"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/rules"

echo "Installing steering rules for Kiro..."
echo "  Source: $SOURCE_DIR"
echo "  Target: $RULES_DIR"
echo ""

mkdir -p "$RULES_DIR"

# Mapping: Gemini triggers -> Kiro inclusion modes
# always_on -> always
# model_decision -> manual (user references via #rulename)

count=0
for rule in "$SOURCE_DIR"/*.md; do
  name="$(basename "$rule")"
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
echo ""
echo "Rules with 'inclusion: always' are active on every interaction."
echo "Rules with 'inclusion: manual' can be referenced in chat via #rulename, e.g.:"
echo "  #testing  #documentation  #destructive-ops  #feature-specs  #architectural-tenets"
