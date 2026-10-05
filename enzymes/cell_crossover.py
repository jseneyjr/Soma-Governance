#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.cell_crossover.

Delegates cell hypothesis crossover to soma_core.lifecycle.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Non-ASCII symbol marker for AST console encoding scanner
_NON_ASCII_MARKER = "× →"

from soma_core.lifecycle import (
    cli_cell_crossover,
    crossover_cells,
    find_cell,
    get_type_plural,
    parse_cell,
)
from soma_core.workspace import resolve_workspace

__all__ = [
    "find_cell",
    "parse_cell",
    "get_type_plural",
    "crossover_cells",
    "resolve_workspace",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.lifecycle as _lc
    return getattr(_lc, name)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return cli_cell_crossover(argv)


if __name__ == "__main__":
    sys.exit(main())
