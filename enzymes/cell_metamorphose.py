#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.cell_metamorphose.

Delegates cell maturity metamorphosis to soma_core.lifecycle.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from soma_core.lifecycle import (
    METAMORPHOSIS_PATHS,
    cli_cell_metamorphose,
    metamorphose_cell,
)

__all__ = [
    "METAMORPHOSIS_PATHS",
    "metamorphose_cell",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.lifecycle as _lc
    return getattr(_lc, name)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return cli_cell_metamorphose(argv)


if __name__ == "__main__":
    sys.exit(main())
