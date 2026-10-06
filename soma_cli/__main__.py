"""Allow `python3 -m soma_cli` when the soma script is not on PATH (BUG-041)."""
import sys

from soma_cli.cli import main

if __name__ == "__main__":
    sys.exit(main())
