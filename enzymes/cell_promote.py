#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.cell_promote.

Delegates cell promotion and speciation to soma_core.lifecycle.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from soma_core.lifecycle import (
    DECAY_FACTOR,
    apply_decay,
    cli_cell_promote,
    normalize_fitness,
    resolve_metrics_dir,
)

__all__ = [
    "DECAY_FACTOR",
    "apply_decay",
    "normalize_fitness",
    "resolve_metrics_dir",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.lifecycle as _lc
    return getattr(_lc, name)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return cli_cell_promote(argv)


if __name__ == "__main__":
    sys.exit(main())
