#!/usr/bin/env bash
set -euo pipefail

# log_finding.sh — Single entry point for governance finding logging.
# Replaces ad-hoc echo >> commands. Routes critical findings to pending_critical.md.
#
# Usage: log_finding.sh --severity <critical|warning|nit> --rule <rule> --change <change> --source <source>

SEVERITY=""
RULE=""
CHANGE=""
SOURCE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --severity) SEVERITY="$2"; shift 2 ;;
    --rule)     RULE="$2"; shift 2 ;;
    --change)   CHANGE="$2"; shift 2 ;;
    --source)   SOURCE="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$SEVERITY" || -z "$RULE" || -z "$CHANGE" || -z "$SOURCE" ]]; then
  echo "Usage: $0 --severity <critical|warning|nit> --rule <rule> --change <change> --source <source>" >&2
  exit 1
fi

SEVERITY=$(echo "$SEVERITY" | tr '[:upper:]' '[:lower:]')
LOGS_REPO="${HOME}/.gemini/antigravity/scratch/ai-conversation-logs"
AUTO_LOG="${LOGS_REPO}/governance/auto_applied_log.jsonl"
CRITICAL="${LOGS_REPO}/governance/pending_critical.md"
LOCK_FILE="${LOGS_REPO}/governance/.governance.lock"
TIMESTAMP=$(date -Iseconds)

mkdir -p "${LOGS_REPO}/governance"

# Concurrency-safe write
(
  flock -x 200

  # 1. Append JSON record to audit log
  printf '{"timestamp":"%s","severity":"%s","rule":"%s","change":"%s","source":"%s"}\n' \
    "$TIMESTAMP" "$SEVERITY" "$RULE" "$CHANGE" "$SOURCE" >> "$AUTO_LOG"

  # 2. If critical, also append to pending_critical.md
  if [[ "$SEVERITY" == "critical" ]]; then
    cat >> "$CRITICAL" << EOF

### 🔴 CRITICAL: $RULE ($TIMESTAMP)
- **Change**: $CHANGE
- **Source**: $SOURCE
EOF
  fi
) 200>"$LOCK_FILE"

echo "✅ Logged $SEVERITY finding for $RULE"
