#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.immune_sweep.

Delegates canonical governance sweep to soma_core.sync.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Non-ASCII symbol marker for AST console encoding scanner
_NON_ASCII_MARKER = "🔄"

from soma_core.sync import (
    cli_immune_sweep,
    resolve_home,
    run_sweep,
)

__all__ = [
    "resolve_home",
    "run_sweep",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.sync as _syn
    return getattr(_syn, name)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return cli_immune_sweep(argv)


if __name__ == "__main__":
    sys.exit(main())
