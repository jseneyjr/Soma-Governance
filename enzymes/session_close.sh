#!/usr/bin/env bash
# Session Close — Stop hook
# Forwarding shim to soma_cli.hooks session-close (preserves backward compatibility)
# Canonical evidence reader: delegates to soma_cli.hooks session-close.
# Preserves canonical signals.jsonl reader invariants:
# 1. Crossover reads triggers from signals.jsonl
# 2. Metamorphosis checks thresholds against signals.jsonl
# 3. Session dashboard aggregates counts from signals.jsonl
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
    sys.exit(main(["session-close", *sys.argv[1:]]))
except Exception:
    print("{}")
    sys.exit(0)
' "$@"
exit $?
