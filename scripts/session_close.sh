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

# --- Cell Feedback Prompt ---
CELLS_DIR="$STEERING_REPO/.prism/cells"
if [ -d "$CELLS_DIR" ] && [ "$(find "$CELLS_DIR" -type f -name "*.md" | wc -l)" -gt 0 ]; then
    echo -e "\n=== Governance Cell Feedback ==="
    read -p "Did any cells help this session? [y/n/skip]: " feedback_resp
    if [[ "$feedback_resp" == "y" || "$feedback_resp" == "n" ]]; then
        read -p "Which cell? (enter name without .md): " cell_name
        cell_file=$(find "$CELLS_DIR" -type f -name "${cell_name}.md" | head -n 1)
        if [ -n "$cell_file" ]; then
            useful="false"
            if [[ "$feedback_resp" == "y" ]]; then useful="true"; fi
            
            # Log to fitness.jsonl
            timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S")
            echo "{\"timestamp\": \"$timestamp\", \"cell\": \"$cell_name\", \"triggered\": true, \"useful\": $useful}" >> "$CELLS_DIR/fitness.jsonl"
            
            # Update frontmatter fitness counters
            python3 -c "
import sys, re
fpath = sys.argv[1]
useful = sys.argv[2] == 'true'
with open(fpath, 'r') as f: content = f.read()
def inc(m): return f'{m.group(1)}{int(m.group(2)) + 1}'
content = re.sub(r'(triggers:\s*)(\d+)', inc, content)
if useful:
    content = re.sub(r'(true_positives:\s*)(\d+)', inc, content)
else:
    content = re.sub(r'(false_positives:\s*)(\d+)', inc, content)
with open(fpath, 'w') as f: f.write(content)
" "$cell_file" "$useful"
            echo "Cell fitness updated."
        else
            echo "Cell not found: $cell_name"
        fi
    fi
fi
