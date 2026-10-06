#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.liveness_sentinel.

Delegates canonical subagent liveness monitoring to soma_core.sync.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from soma_core.sync import (
    check_liveness,
    cli_liveness_sentinel,
)

__all__ = [
    "check_liveness",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.sync as _syn
    return getattr(_syn, name)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return cli_liveness_sentinel(argv)


if __name__ == "__main__":
    sys.exit(main())
