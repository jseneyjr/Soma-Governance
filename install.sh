#!/usr/bin/env bash
set -euo pipefail

RULES_DIR="$HOME/.gemini/config/rules"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/rules"

echo "Installing Gemini steering rules..."
echo "  Source: $SOURCE_DIR"
echo "  Target: $RULES_DIR"
echo ""

mkdir -p "$RULES_DIR"

count=0
for rule in "$SOURCE_DIR"/*.md; do
  name="$(basename "$rule")"
  if [ -f "$RULES_DIR/$name" ]; then
    echo "  ⚠  $name already exists, backing up to $name.bak"
    cp "$RULES_DIR/$name" "$RULES_DIR/$name.bak"
  fi
  cp "$rule" "$RULES_DIR/$name"
  echo "  ✅ $name"
  count=$((count + 1))
done

echo ""
echo "Done! Installed $count rules to $RULES_DIR"
echo "These will take effect on your next Gemini conversation turn."
