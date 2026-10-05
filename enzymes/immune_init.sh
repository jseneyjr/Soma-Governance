#!/usr/bin/env bash
# Immune Init — PreInvocation hook
# Forwarding shim to soma_cli.hooks pre-invocation (preserves backward compatibility)
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

soma_py -c '
import os, sys
repo = os.environ.get("SOMA_STEERING_REPO")
if repo and repo not in sys.path:
    sys.path.insert(0, repo)
try:
    from soma_cli.hooks import main
    sys.exit(main(["pre-invocation", *sys.argv[1:]]))
except Exception:
    print("{}")
    sys.exit(0)
' "$@"
exit $?
