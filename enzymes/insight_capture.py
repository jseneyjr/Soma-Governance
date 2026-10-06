#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.insight_capture.

Delegates canonical insight capture to soma_core.insights.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from soma_core.insights import (
    capture_insight,
    cli_insight_capture,
)

__all__ = [
    "capture_insight",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.insights as _ins
    return getattr(_ins, name)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return cli_insight_capture(argv)


if __name__ == "__main__":
    sys.exit(main())
