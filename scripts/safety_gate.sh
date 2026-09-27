#!/usr/bin/env bash
set -euo pipefail

# Safety Gate — PreToolUse hook
# Gates destructive run_command operations. Returns force_ask for dangerous patterns.
# Output contract: {"decision": "allow"} or {"decision": "force_ask", "reason": "..."}
# Latency target: <100ms (pure bash, no subshells in hot path)

# Emergency bypass: operator can disable the gate entirely
if [ "${STEERING_SAFETY_GATE:-}" = "disabled" ]; then
    echo '{"decision": "allow"}'
    exit 0
fi

INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
tc = data.get('toolCall', {})
args = tc.get('args', {})
print(args.get('CommandLine', ''))
" 2>/dev/null || echo "")

# Fail-closed: if we can't parse the command or it's empty, force ask
if [ -z "$CMD" ]; then
    cat <<'RESPONSE'
{
  "decision": "force_ask",
  "reason": "🛡️ Safety Gate: Unable to parse command — requesting confirmation"
}
RESPONSE
    exit 0
fi

# Destructive patterns
BLOCKED=false
REASON=""

# --- File system destruction ---

# rm: catch -rf, -r -f, -fr, --recursive, and rmdir with ignore flag
if echo "$CMD" | grep -qE 'rm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r|-r\s+-f|-f\s+-r|--recursive)\s+(/|~|/home|\$HOME)'; then
    BLOCKED=true
    REASON="Recursive delete targeting home/root directory"
fi

if echo "$CMD" | grep -qE 'rmdir\s+--ignore-fail-on-non-empty'; then
    BLOCKED=true
    REASON="rmdir with --ignore-fail-on-non-empty — bypasses safety check"
fi

# mkfs — formatting a filesystem
if echo "$CMD" | grep -qE '\bmkfs\b'; then
    BLOCKED=true
    REASON="Filesystem format (mkfs) detected — destructive operation"
fi

# dd if= — raw disk write
if echo "$CMD" | grep -qE '\bdd\s+.*if='; then
    BLOCKED=true
    REASON="Raw disk write (dd) detected — destructive operation"
fi

# chmod 777 — overly permissive
if echo "$CMD" | grep -qE 'chmod\s+777'; then
    BLOCKED=true
    REASON="chmod 777 — overly permissive, potential security risk"
fi

# kill -9 -1 — kill all processes
if echo "$CMD" | grep -qE 'kill\s+-9\s+-1'; then
    BLOCKED=true
    REASON="kill -9 -1 — would kill all user processes"
fi

# --- Privilege escalation ---

# sudo — any sudo invocation
if echo "$CMD" | grep -qE '\bsudo\b'; then
    BLOCKED=true
    REASON="sudo detected — elevated privileges require confirmation"
fi

# --- Remote code execution ---

# curl|sh, wget|sh patterns
if echo "$CMD" | grep -qE 'curl\s.*\|.*sh|wget\s.*\|.*sh'; then
    BLOCKED=true
    REASON="Piping remote content to shell — potential code execution risk"
fi

# --- Git destructive operations ---

# Force push: --force, -f flag, or +refspec
if echo "$CMD" | grep -qE 'git\s+push\s+.*(-f|--force|--force-with-lease)'; then
    BLOCKED=true
    REASON="Force push detected — destructive-ops mandate requires confirmation"
fi

if echo "$CMD" | grep -qE 'git\s+push\s+\S+\s+\+'; then
    BLOCKED=true
    REASON="Force push via +refspec detected — destructive-ops mandate requires confirmation"
fi

# Git reset --hard
if echo "$CMD" | grep -qE 'git\s+reset\s+--hard'; then
    BLOCKED=true
    REASON="Hard reset — will discard uncommitted changes"
fi

# Git checkout -f (force checkout, discards local changes)
if echo "$CMD" | grep -qE 'git\s+checkout\s+-f'; then
    BLOCKED=true
    REASON="Force checkout — will discard uncommitted changes"
fi

# Git clean -fdx (removes untracked files and directories)
if echo "$CMD" | grep -qE 'git\s+clean\s+.*-[a-zA-Z]*f'; then
    BLOCKED=true
    REASON="git clean -f — will permanently remove untracked files"
fi

# Bulk git staging without dry-run: git add -A, git add ., git add --all, git add *
if echo "$CMD" | grep -qE 'git\s+add\s+(-A|\.|\*|--all)\s*$'; then
    BLOCKED=true
    REASON="Bulk staging (git add -A/./*/--all) — run git status first to verify file count"
fi

# --- Database destructive operations ---

if echo "$CMD" | grep -qiE '(DROP\s+(TABLE|DATABASE)|DELETE\s+FROM\s+\w+\s*|TRUNCATE\s+TABLE)'; then
    BLOCKED=true
    REASON="Destructive database operation without WHERE clause"
fi

# --- Logging ---

GATE_LOG="$HOME/.gemini/antigravity/scratch/ai-conversation-logs/governance/gate_events.jsonl"
GATE_LOG_DIR="$(dirname "$GATE_LOG")"

# Create log directory if missing (graceful)
if [ ! -d "$GATE_LOG_DIR" ]; then
    mkdir -p "$GATE_LOG_DIR" 2>/dev/null || true
fi

if [ "$BLOCKED" = true ]; then
    echo "{\"timestamp\":\"$(date -Iseconds)\",\"command\":\"$(echo "$CMD" | head -c 200)\",\"decision\":\"BLOCKED\",\"reason\":\"$REASON\"}" >> "$GATE_LOG" 2>/dev/null || true
    cat <<RESPONSE
{
  "decision": "force_ask",
  "reason": "🛡️ Safety Gate: $REASON"
}
RESPONSE
else
    echo "{\"timestamp\":\"$(date -Iseconds)\",\"command\":\"$(echo "$CMD" | head -c 200)\",\"decision\":\"ALLOWED\"}" >> "$GATE_LOG" 2>/dev/null || true
    echo '{"decision": "allow"}'
fi
