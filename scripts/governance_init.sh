#!/usr/bin/env bash
set -euo pipefail

# Governance Init — PreInvocation hook
# Fires before every model call. On first invocation (and every 100th),
# checks for pending governance proposals.
#
# Alert routing:
#   🔴 Critical → LOUD alert, rotates pending_critical.md → last_critical.md
#   ℹ️  Non-critical → quiet alert ONLY if genuinely new findings exist (cursor-based)
#   {} → silent if nothing new

INPUT=$(cat)
INVOCATION_NUM=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('invocationNum', 0))" 2>/dev/null || echo "0")

# Run on first invocation and every 100th invocation
if [ "$INVOCATION_NUM" != "1" ] && [ "$(( INVOCATION_NUM % 100 ))" != "0" ]; then
    echo '{}'
    exit 0
fi

LOGS_REPO="$HOME/.gemini/antigravity/scratch/ai-conversation-logs"
CRITICAL="$LOGS_REPO/governance/pending_critical.md"
LAST_CRITICAL="$LOGS_REPO/governance/last_critical.md"
AUTO_LOG="$LOGS_REPO/governance/auto_applied_log.jsonl"
CURSOR_FILE="$LOGS_REPO/governance/.last_seen_audit_lines"
LOCK_FILE="$LOGS_REPO/governance/.governance.lock"
EXPORT_SCRIPT="$HOME/.gemini/antigravity/scratch/ai-steering-rules/scripts/export_logs.sh"

# Run log export async (non-blocking)
if [ -x "$EXPORT_SCRIPT" ]; then
    bash "$EXPORT_SCRIPT" > /dev/null 2>&1 &
fi

# Alert decision — concurrency-safe
if [ -d "$LOGS_REPO/governance" ]; then
    (
        flock -x 200

        # 1. Check for critical findings
        if [ -f "$CRITICAL" ] && [ -s "$CRITICAL" ]; then
            FINDING_COUNT=$(grep -c "🔴" "$CRITICAL" 2>/dev/null || echo "1")

            # Rotate: pending → last (user can cat last_critical.md)
            cp -f "$CRITICAL" "$LAST_CRITICAL"
            : > "$CRITICAL"

            # Update cursor so we don't double-alert non-critical
            if [ -f "$AUTO_LOG" ]; then
                wc -l < "$AUTO_LOG" > "$CURSOR_FILE"
            fi

            cat << RESPONSE
{
  "injectSteps": [
    {
      "ephemeralMessage": "🔴 GOVERNANCE: $FINDING_COUNT critical change(s) were AUTO-APPLIED to your steering rules. Review: cat $LAST_CRITICAL"
    }
  ]
}
RESPONSE
        else
            # 2. Check for genuinely new non-critical findings (cursor-based)
            NEW_FINDINGS=0
            if [ -f "$AUTO_LOG" ]; then
                TOTAL_LINES=$(wc -l < "$AUTO_LOG")
                LAST_SEEN=0
                if [ -f "$CURSOR_FILE" ]; then
                    LAST_SEEN=$(cat "$CURSOR_FILE" 2>/dev/null || echo "0")
                fi
                NEW_FINDINGS=$((TOTAL_LINES - LAST_SEEN))
            fi

            if [ "$NEW_FINDINGS" -gt 0 ]; then
                # Update cursor
                echo "$TOTAL_LINES" > "$CURSOR_FILE"
                cat << RESPONSE
{
  "injectSteps": [
    {
      "ephemeralMessage": "ℹ️ Governance: $NEW_FINDINGS non-critical finding(s) auto-applied since last session. Audit: tail -$NEW_FINDINGS $AUTO_LOG"
    }
  ]
}
RESPONSE
            else
                echo '{}'
            fi
        fi
    ) 200>"$LOCK_FILE"
else
    echo '{}'
fi
