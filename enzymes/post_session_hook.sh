#!/usr/bin/env bash
# Post-session hook: update cell fitness data from a session transcript.
# Thin backwards-compatible wrapper delegating to pure Python post_session_hook.py.
#
# Usage:
#   bash enzymes/post_session_hook.sh <transcript_path>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/soma_python.sh"
soma_resolve_python || true

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <transcript_path>" >&2
    exit 1
fi

TRANSCRIPT="$1"

if [[ ! -f "$TRANSCRIPT" ]]; then
    echo "Error: transcript not found: $TRANSCRIPT" >&2
    exit 1
fi

soma_py "$SCRIPT_DIR/post_session_hook.py" "$@"
exit $?
