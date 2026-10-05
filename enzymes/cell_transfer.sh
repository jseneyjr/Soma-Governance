#!/usr/bin/env bash
# cell_transfer.sh: Copies a cell to another project with fitness reset.
# Usage: bash enzymes/cell_transfer.sh <cell_id> --to /path/to/target/project
set -euo pipefail

PRG="${BASH_SOURCE[0]}"
while [ -h "$PRG" ]; do
  DIR="$(cd -P "$(dirname "$PRG")" && pwd)"
  PRG="$(readlink "$PRG")"
  [[ $PRG != /* ]] && PRG="$DIR/$PRG"
done
SCRIPT_DIR="$(cd -P "$(dirname "$PRG")" && pwd)"
source "$SCRIPT_DIR/common.sh"
STEERING_REPO="$(cd -P "$SCRIPT_DIR/.." && pwd)"
export SOMA_STEERING_REPO="$STEERING_REPO"

soma_py "$SCRIPT_DIR/cell_transfer.py" "$@"
exit $?
