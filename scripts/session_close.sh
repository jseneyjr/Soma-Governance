#!/usr/bin/env bash
set -euo pipefail

# Session Close — Stop hook
# Exports conversation logs and pushes to private repo when session ends.

EXPORT_SCRIPT="$HOME/.gemini/antigravity/scratch/ai-steering-rules/scripts/export_logs.sh"

if [ -x "$EXPORT_SCRIPT" ]; then
    bash "$EXPORT_SCRIPT" > /dev/null 2>&1 || true
fi

# Return continue only if we need to block termination (we don't)
echo '{}'
