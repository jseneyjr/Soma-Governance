#!/usr/bin/env bash
set -euo pipefail

# Session Close — Stop hook
# Exports conversation logs and syncs both repos when session ends.

# Symlink-safe resolution (Thorns fix #3)
PRG="${BASH_SOURCE[0]}"
while [ -h "$PRG" ]; do
  DIR="$(cd -P "$(dirname "$PRG")" && pwd)"
  PRG="$(readlink "$PRG")"
  [[ $PRG != /* ]] && PRG="$DIR/$PRG"
done
SCRIPT_DIR="$(cd -P "$(dirname "$PRG")" && pwd)"

# Resolve repo root relative to this script (scripts/ -> repo root)
STEERING_REPO="$(cd -P "$SCRIPT_DIR/.." && pwd)"
LOGS_REPO="$HOME/.gemini/antigravity/scratch/ai-conversation-logs"
EXPORT_SCRIPT="$STEERING_REPO/scripts/export_logs.sh"

# Clean stale git locks (only if no process is actively using them)
for repo in "$STEERING_REPO" "$LOGS_REPO"; do
    lock="$repo/.git/index.lock"
    if [ -f "$lock" ]; then
        if command -v fuser > /dev/null 2>&1; then
            if ! fuser "$lock" > /dev/null 2>&1; then
                rm -f -- "$lock"
            fi
        elif command -v lsof > /dev/null 2>&1; then
            if ! lsof "$lock" > /dev/null 2>&1; then
                rm -f -- "$lock"
            fi
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
    # Safe branch detection (Thorns fix #10): skip push if detached HEAD
    CURRENT_BRANCH=$(git symbolic-ref --short -q HEAD 2>/dev/null || true)
    if [ -n "$CURRENT_BRANCH" ] && [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        git add . && git commit -m "chore(sync): auto-sync on session close: $(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S")" && git push origin "$CURRENT_BRANCH" 2>/dev/null || true
    fi
fi

echo '{}'
