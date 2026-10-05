#!/usr/bin/env bash
# cell_create.sh: Programmatic Cell Creation for Soma
# Usage: bash enzymes/cell_create.sh --type <type> --hypothesis <hypothesis> --prediction <prediction> --falsification <falsification> [options]

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

soma_py "$SCRIPT_DIR/cell_create.py" "$@"
exit $?
