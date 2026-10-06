#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.cell_escaped_defects.

Delegates canonical escaped defect tracking to soma_core.defects.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from soma_core.defects import (
    compute_enhanced_fitness,
    find_covering_cells,
    generate_report,
    load_cells,
    match_glob,
    record_escaped_defect,
    scan_git_for_defects,
    update_cell_escaped_rate,
    cli_cell_escaped_defects,
)

__all__ = [
    "match_glob",
    "load_cells",
    "find_covering_cells",
    "record_escaped_defect",
    "update_cell_escaped_rate",
    "compute_enhanced_fitness",
    "scan_git_for_defects",
    "generate_report",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.defects as _def
    return getattr(_def, name)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return cli_cell_escaped_defects(argv)


if __name__ == "__main__":
    sys.exit(main())
