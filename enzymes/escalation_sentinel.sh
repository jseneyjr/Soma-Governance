#!/usr/bin/env bash
# escalation_sentinel.sh — Zero-token protocol escalation recommender (E14)
# Thin backwards-compatible wrapper delegating to pure Python escalation_sentinel.py.
#
# Analyzes staged/unstaged git changes and recommends the minimum review
# protocol based on file sensitivity patterns and diff size.
#
# Usage:
#   ./escalation_sentinel.sh [--staged]    # Analyze staged changes
#   ./escalation_sentinel.sh [--all]       # Analyze all uncommitted changes
#   ./escalation_sentinel.sh [file...]     # Analyze specific files

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/soma_python.sh"
soma_resolve_python || true

soma_py "$SCRIPT_DIR/escalation_sentinel.py" "$@"
exit $?
