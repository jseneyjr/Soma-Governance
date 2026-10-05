#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Governance Sweep — Periodic lower-priority governance check
# Thin backwards-compatible wrapper delegating to pure Python immune_sweep.py.
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"
RESOLVED_HOME=$(resolve_home)

# Ensure default data dir exists under isolated home when SOMA_DATA_DIR is not set
SOMA_DATA_DIR="${SOMA_DATA_DIR:-$RESOLVED_HOME/.gemini/antigravity}"
export SOMA_DATA_DIR
mkdir -p "$SOMA_DATA_DIR"

soma_py "$SCRIPT_DIR/immune_sweep.py" "$@"
exit $?
