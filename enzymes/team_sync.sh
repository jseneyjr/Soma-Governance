#!/usr/bin/env bash
set -euo pipefail

# Symlink-safe resolution
PRG="${BASH_SOURCE[0]}"
while [ -h "$PRG" ]; do
  DIR="$(cd -P "$(dirname "$PRG")" && pwd)"
  PRG="$(readlink "$PRG")"
  [[ $PRG != /* ]] && PRG="$DIR/$PRG"
done
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
SCRIPTS_DIR="$REPO_DIR/enzymes"
# If scripts dir doesn't exist at resolved root, fall back to original script location
[ ! -d "$SCRIPTS_DIR" ] && SCRIPTS_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPTS_DIR/soma_python.sh"
soma_resolve_python || true

soma_py "$SCRIPTS_DIR/team_sync.py" "$@"
exit $?
