#!/usr/bin/env bash
# Post-session hook: update cell fitness data from a session transcript.
#
# Usage:
#   bash enzymes/post_session_hook.sh <transcript_path>
#
# This is the v1 integration point. The Oracle Checkpoint (Phase 4) will
# provide mid-session feedback; when it ships, this hook becomes its
# post-session cleanup step.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <transcript_path>" >&2
    exit 1
fi

TRANSCRIPT="$1"

if [[ ! -f "$TRANSCRIPT" ]]; then
    echo "Error: transcript not found: $TRANSCRIPT" >&2
    exit 1
fi

python3 "${SCRIPT_DIR}/fitness_updater.py" "$TRANSCRIPT"
