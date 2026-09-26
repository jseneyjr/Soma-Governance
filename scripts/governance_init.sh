#!/usr/bin/env bash
set -euo pipefail

# Governance Init — PreInvocation hook
# Fires before every model call. On first invocation, checks for pending proposals
# and injects a reminder if found. No-op on subsequent invocations.

INPUT=$(cat)
INVOCATION_NUM=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('invocationNum', 0))" 2>/dev/null || echo "0")

# Run on first invocation and every 100th invocation (catches existing sessions)
if [ "$INVOCATION_NUM" != "1" ] && [ "$(( INVOCATION_NUM % 100 ))" != "0" ]; then
    echo '{}'
    exit 0
fi

LOGS_REPO="$HOME/.gemini/antigravity/scratch/ai-conversation-logs"
PROPOSALS="$LOGS_REPO/governance/pending_proposals.md"
EXPORT_SCRIPT="$HOME/.gemini/antigravity/scratch/ai-steering-rules/scripts/export_logs.sh"

# Run log export if script exists
if [ -x "$EXPORT_SCRIPT" ]; then
    bash "$EXPORT_SCRIPT" > /dev/null 2>&1 || true
fi

# Check for pending governance proposals
if [ -f "$PROPOSALS" ] && [ -s "$PROPOSALS" ]; then
    FINDING_COUNT=$(grep -c "^###\|^##" "$PROPOSALS" 2>/dev/null || echo "?")
    cat << RESPONSE
{
  "injectSteps": [
    {
      "ephemeralMessage": "⚠️ GOVERNANCE: There are pending governance proposals in ai-conversation-logs/governance/pending_proposals.md ($FINDING_COUNT sections). Review and apply or dismiss before starting new work. Run: cat $PROPOSALS"
    }
  ]
}
RESPONSE
else
    echo '{}'
fi
