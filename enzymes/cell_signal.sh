#!/usr/bin/env bash
# Soma - External Fitness Signal API
# Allows external systems to feed fitness signals back to cells.
# Usage:
#   bash enzymes/cell_signal.sh <cell_id> tp [--metric key=value]
#   bash enzymes/cell_signal.sh <cell_id> fp
#   bash enzymes/cell_signal.sh <cell_id> fn

set -euo pipefail

# Symlink-safe pattern to resolve repository directory
# Walk up from CWD to find project root with .soma/cells/
if [ -n "${SOMA_ROOT:-}" ] && [ -d "$SOMA_ROOT" ]; then
  REPO_DIR="$SOMA_ROOT"
else
  _d="$(pwd)"
  REPO_DIR="$_d"
  while true; do
    if [[ "$_d" != */vendor/* ]] && [[ "$_d" != */vendor ]]; then
      if [ -d "$_d/.soma/cells" ]; then
        REPO_DIR="$_d"
        break
      fi
    fi
    _parent="$(dirname "$_d")"
    [ "$_d" = "$_parent" ] && break
    _d="$_parent"
  done
fi
# Symlink-safe self-location: a dirname of a symlinked invocation names the
# link's directory, where soma_python.sh (and the Python helpers) don't exist.
PRG="${BASH_SOURCE[0]}"
while [ -h "$PRG" ]; do
  DIR="$(cd -P "$(dirname "$PRG")" && pwd)"
  PRG="$(readlink "$PRG")"
  [[ $PRG != /* ]] && PRG="$DIR/$PRG"
done
SCRIPT_DIR="$(cd -P "$(dirname "$PRG")" && pwd)"
source "$SCRIPT_DIR/soma_python.sh"
soma_resolve_python || true

soma_py "$SCRIPT_DIR/cell_signal.py" "$@"
exit $?
