#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.cell_enforce.

Delegates canonical enforcement artifact generation to soma_core.enforcement.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from soma_core.enforcement import (
    cli_cell_enforce,
    generate_precommit_check,
    generate_gate_assertion,
    update_cell_enforcement_artifact,
    load_cells,
)

__all__ = [
    "load_cells",
    "generate_precommit_check",
    "generate_gate_assertion",
    "update_cell_enforcement_artifact",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.enforcement as _enf
    return getattr(_enf, name)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return cli_cell_enforce(argv)


if __name__ == "__main__":
    sys.exit(main())
