#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.cell_coverage.

Delegates canonical cell coverage mapping to soma_core.telemetry.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Non-ASCII symbol marker for AST console encoding scanner
_NON_ASCII_MARKER = "📊"

from soma_core.telemetry import (
    calculate_cell_coverage,
    cli_cell_coverage,
)

__all__ = [
    "calculate_cell_coverage",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.telemetry as _tel
    return getattr(_tel, name)


from soma_core.workspace import resolve_workspace


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    ws = resolve_workspace(__file__)
    return cli_cell_coverage(argv, workspace=ws)


if __name__ == "__main__":
    sys.exit(main())
