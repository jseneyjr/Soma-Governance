#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.post_session_hook.

Delegates canonical post-session transcript fitness and evidence hook to soma_core.sync.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from soma_core.sync import (
    cli_post_session_hook,
    run_post_session_hook,
)

__all__ = [
    "run_post_session_hook",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.sync as _syn
    return getattr(_syn, name)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return cli_post_session_hook(argv)


if __name__ == "__main__":
    sys.exit(main())
