#!/usr/bin/env python3
"""cell_transfer.py: Copies a cell to another project with fitness reset.

Backward-compatible forwarding layer to soma_cli.transfer.
Usage:
    python enzymes/cell_transfer.py <cell_id> --to /path/to/target/project
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from soma_cli.transfer import transfer_cell, resolve_workspace, run_transfer  # noqa: F401


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Copies a cell to another project with fitness reset")
    parser.add_argument("cell_id", nargs="?", default="", help="ID of cell to transfer")
    parser.add_argument("--to", dest="target_dir", default="", help="Path to target project")
    args = parser.parse_args(argv)

    if not args.cell_id or not args.target_dir:
        print("Error: Missing cell_id or --to directory", file=sys.stderr)
        print("Usage: cell_transfer.py <cell_id> --to /path/to/target/project", file=sys.stderr)
        return 1

    return transfer_cell(cell_id=args.cell_id, target_dir_str=args.target_dir)


if __name__ == "__main__":
    sys.exit(main())
