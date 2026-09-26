#!/usr/bin/env bash
set -euo pipefail

# Session Close — Stop hook
# Exports conversation logs and syncs both repos when session ends.

STEERING_REPO="$HOME/.gemini/antigravity/scratch/ai-steering-rules"
LOGS_REPO="$HOME/.gemini/antigravity/scratch/ai-conversation-logs"
EXPORT_SCRIPT="$STEERING_REPO/scripts/export_logs.sh"

# Clean stale git locks (only if no process is actively using them)
for repo in "$STEERING_REPO" "$LOGS_REPO"; do
    lock="$repo/.git/index.lock"
    if [ -f "$lock" ]; then
        if ! fuser "$lock" > /dev/null 2>&1; then
            rm -f "$lock"
        fi
    fi
done

# Export logs
if [ -x "$EXPORT_SCRIPT" ]; then
    bash "$EXPORT_SCRIPT" > /dev/null 2>&1 || true
fi

# Push steering repo if dirty (catches any rule edits made during session)
if [ -d "$STEERING_REPO/.git" ]; then
    cd "$STEERING_REPO"
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        git add . && git commit -m "Auto-sync on session close: $(date -Iseconds)" && git push origin master 2>/dev/null || true
    fi
fi

echo '{}'
