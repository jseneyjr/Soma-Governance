#!/usr/bin/env bash
set -euo pipefail

# Safety Gate — PreToolUse hook
# Gates destructive run_command operations. Returns force_ask for dangerous patterns.

INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
tc = data.get('toolCall', {})
args = tc.get('args', {})
print(args.get('CommandLine', ''))
" 2>/dev/null || echo "")

# If we can't parse the command, allow it
if [ -z "$CMD" ]; then
    echo '{"decision": "allow"}'
    exit 0
fi

# Destructive patterns
BLOCKED=false
REASON=""

# Destructive file operations outside project dirs
if echo "$CMD" | grep -qE 'rm\s+(-[a-zA-Z]*r[a-zA-Z]*f|--recursive)\s+(/|~|/home)'; then
    BLOCKED=true
    REASON="Recursive delete targeting home/root directory"
fi

# Force push
if echo "$CMD" | grep -qE 'git\s+push\s+.*(-f|--force)'; then
    BLOCKED=true
    REASON="Force push detected — destructive-ops mandate requires confirmation"
fi

# Database destructive operations
if echo "$CMD" | grep -qiE '(DROP\s+(TABLE|DATABASE)|DELETE\s+FROM\s+\w+\s*$|TRUNCATE\s+TABLE)'; then
    BLOCKED=true
    REASON="Destructive database operation without WHERE clause"
fi

# Git reset --hard
if echo "$CMD" | grep -qE 'git\s+reset\s+--hard'; then
    BLOCKED=true
    REASON="Hard reset — will discard uncommitted changes"
fi

GATE_LOG="$HOME/.gemini/antigravity/scratch/ai-conversation-logs/governance/gate_events.jsonl"

if [ "$BLOCKED" = true ]; then
    echo "{\"timestamp\":\"$(date -Iseconds)\",\"command\":\"$(echo "$CMD" | head -c 200)\",\"decision\":\"BLOCKED\",\"reason\":\"$REASON\"}" >> "$GATE_LOG" 2>/dev/null || true
    cat << RESPONSE
{
  "decision": "force_ask",
  "reason": "🛡️ Safety Gate: $REASON"
}
RESPONSE
else
    echo "{\"timestamp\":\"$(date -Iseconds)\",\"command\":\"$(echo "$CMD" | head -c 200)\",\"decision\":\"ALLOWED\"}" >> "$GATE_LOG" 2>/dev/null || true
    echo '{"decision": "allow"}'
fi
