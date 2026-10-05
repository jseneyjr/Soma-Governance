#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.insight_correlator.

Delegates canonical insight clustering to soma_core.insights.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from soma_core.insights import (
    cluster_insights,
    generate_cell_candidates,
    cli_insight_correlator,
)

__all__ = [
    "cluster_insights",
    "generate_cell_candidates",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.insights as _ins
    return getattr(_ins, name)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return cli_insight_correlator(argv)


if __name__ == "__main__":
    sys.exit(main())
