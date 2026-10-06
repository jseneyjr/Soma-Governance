#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.cell_fitness.

Delegates cell fitness evaluation and reporting to soma_core.lifecycle.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Non-ASCII symbol marker for AST console encoding scanner
_NON_ASCII_MARKER = "∞"

from soma_core.lifecycle import (
    antifragile_bonus,
    bayesian_fitness,
    cli_cell_fitness,
    decayed_fitness,
    format_snr,
)
from soma_core.workspace import resolve_workspace

__all__ = [
    "bayesian_fitness",
    "antifragile_bonus",
    "format_snr",
    "decayed_fitness",
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
    ws = resolve_workspace()

    return cli_cell_fitness(argv, workspace=ws)


if __name__ == "__main__":
    sys.exit(main())
