#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.soma_interoception.

Delegates canonical interoception state calculation to soma_core.homeostasis.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Non-ASCII symbol marker for AST console encoding scanner
_NON_ASCII_MARKER = "🧬"

from soma_core.homeostasis import (
    CAUTION_THRESHOLD,
    CRITICAL_THRESHOLD,
    WEIGHTS,
    calculate_internal_state,
    cli_soma_interoception,
    normalize,
)

__all__ = [
    "CAUTION_THRESHOLD",
    "CRITICAL_THRESHOLD",
    "WEIGHTS",
    "normalize",
    "calculate_internal_state",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.homeostasis as _hom
    return getattr(_hom, name)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return cli_soma_interoception(argv)


if __name__ == "__main__":
    sys.exit(main())
