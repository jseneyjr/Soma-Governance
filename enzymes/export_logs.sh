#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/soma_python.sh"
soma_resolve_python || true

soma_py "$SCRIPT_DIR/export_logs.py" "$@"
exit $?
