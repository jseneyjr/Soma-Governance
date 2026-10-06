#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.oracle_checkpoint.

Delegates canonical checkpoint evaluation to soma_core.arbitration.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from soma_core.arbitration import (
    _classify_cells,
    _load_cells,
    _load_fitness_evidence,
    cli_checkpoint,
    generate_checkpoint,
)
from soma_core.workspace import resolve_workspace

__all__ = [
    "generate_checkpoint",
    "_load_fitness_evidence",
    "_load_cells",
    "_classify_cells",
    "resolve_workspace",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.arbitration as _arb
    return getattr(_arb, name)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return cli_checkpoint(argv)


if __name__ == "__main__":
    sys.exit(main())
