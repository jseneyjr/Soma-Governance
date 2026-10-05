#!/usr/bin/env bash
set -euo pipefail

EXECUTE=false
if [[ "${1:-}" == "--execute" ]]; then
  EXECUTE="--execute"
fi

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/soma_python.sh"
soma_resolve_python || true
soma_py "$SCRIPT_DIR/cell_selection.py" "$@"
exit $?
