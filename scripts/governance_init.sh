#!/usr/bin/env bash
set -euo pipefail

# Governance Init — PreInvocation hook
# Fires before every model call. On first invocation (and every 100th),
# checks for pending governance proposals.
#
# Severity routing (ALL auto-applied, visibility differs):
#   🔴 Critical → auto-applied + LOUD ephemeral alert so user sees it immediately
#   🟡 Warning / 🔵 Nit → auto-applied + quiet info on next session start

INPUT=$(cat)
INVOCATION_NUM=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('invocationNum', 0))" 2>/dev/null || echo "0")

# Run on first invocation and every 100th invocation (catches existing sessions)
if [ "$INVOCATION_NUM" != "1" ] && [ "$(( INVOCATION_NUM % 100 ))" != "0" ]; then
    echo '{}'
    exit 0
fi

LOGS_REPO="$HOME/.gemini/antigravity/scratch/ai-conversation-logs"
CRITICAL="$LOGS_REPO/governance/pending_critical.md"
AUTO_LOG="$LOGS_REPO/governance/auto_applied_log.jsonl"
EXPORT_SCRIPT="$HOME/.gemini/antigravity/scratch/ai-steering-rules/scripts/export_logs.sh"

# Run log export async (non-blocking — avoid 2-5s startup delay)
if [ -x "$EXPORT_SCRIPT" ]; then
    bash "$EXPORT_SCRIPT" > /dev/null 2>&1 &
fi

# Check for CRITICAL findings only (non-critical are auto-applied by the pipeline)
if [ -f "$CRITICAL" ] && [ -s "$CRITICAL" ]; then
    FINDING_COUNT=$(grep -c "🔴\|CRITICAL" "$CRITICAL" 2>/dev/null || echo "?")
    cat << RESPONSE
{
  "injectSteps": [
    {
      "ephemeralMessage": "🔴 GOVERNANCE: $FINDING_COUNT critical change(s) were AUTO-APPLIED to your steering rules. Review what changed: cat $CRITICAL && cat $AUTO_LOG | tail -5"
    }
  ]
}
RESPONSE
else
    # Check if any auto-applied changes happened since last session
    if [ -f "$AUTO_LOG" ]; then
        RECENT=$(tail -1 "$AUTO_LOG" 2>/dev/null || echo "")
        if [ -n "$RECENT" ]; then
            cat << RESPONSE
{
  "injectSteps": [
    {
      "ephemeralMessage": "ℹ️ Governance: Non-critical findings were auto-applied since your last session. Audit trail: $AUTO_LOG"
    }
  ]
}
RESPONSE
        else
            echo '{}'
        fi
    else
        echo '{}'
    fi
fi
