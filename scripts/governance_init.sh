#!/usr/bin/env bash
set -euo pipefail

# Governance Init — PreInvocation hook
# Fires before every model call. On first invocation (and every 100th),
# checks for pending governance proposals.
#
# Severity routing:
#   🔴 Critical → escalate to user via ephemeral message (DO NOT auto-apply)
#   🟡 Warning / 🔵 Nit → auto-applied by governance pipeline (logged to auto_applied_log.jsonl)

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

# Run log export if script exists
if [ -x "$EXPORT_SCRIPT" ]; then
    bash "$EXPORT_SCRIPT" > /dev/null 2>&1 || true
fi

# Check for CRITICAL findings only (non-critical are auto-applied by the pipeline)
if [ -f "$CRITICAL" ] && [ -s "$CRITICAL" ]; then
    FINDING_COUNT=$(grep -c "🔴\|CRITICAL" "$CRITICAL" 2>/dev/null || echo "?")
    cat << RESPONSE
{
  "injectSteps": [
    {
      "ephemeralMessage": "🔴 CRITICAL GOVERNANCE ALERT: $FINDING_COUNT critical finding(s) require your review. Non-critical findings have been auto-applied. Review: cat $CRITICAL"
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
