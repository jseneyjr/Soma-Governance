#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.cell_create.

Delegates programmatic cell creation to soma_core.lifecycle.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from soma_core.lifecycle import (
    VALID_TYPES,
    cli_cell_create,
    create_cell,
    generate_slug,
    validate_cell_id,
)
from soma_core.workspace import resolve_workspace

__all__ = [
    "VALID_TYPES",
    "resolve_workspace",
    "validate_cell_id",
    "generate_slug",
    "create_cell",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.lifecycle as _lc
    return getattr(_lc, name)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return cli_cell_create(argv)


if __name__ == "__main__":
    sys.exit(main())
