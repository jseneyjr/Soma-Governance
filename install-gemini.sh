#!/usr/bin/env bash
# Backward-compatible wrapper. See install.sh for implementation.
PRG="${BASH_SOURCE[0]}"
while [ -h "$PRG" ]; do DIR="$(cd -P "$(dirname "$PRG")" && pwd)"; PRG="$(readlink "$PRG")"; [[ $PRG != /* ]] && PRG="$DIR/$PRG"; done
SCRIPT_DIR="$(cd -P "$(dirname "$PRG")" && pwd)"
exec bash "$SCRIPT_DIR/install.sh" gemini "$@"
