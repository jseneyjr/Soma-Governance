#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.team_sync.

Delegates canonical team cell & metrics synchronization to soma_core.sync.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from soma_core.sync import (
    cli_team_sync,
    load_soma_config,
    run_pull,
    run_push,
    run_status,
)

__all__ = [
    "load_soma_config",
    "run_push",
    "run_pull",
    "run_status",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.sync as _syn
    return getattr(_syn, name)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return cli_team_sync(argv)


if __name__ == "__main__":
    sys.exit(main())
