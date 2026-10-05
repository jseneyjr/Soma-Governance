#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.ci_outcome_reporter.

Delegates canonical CI outcome reporting to soma_core.enforcement.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from soma_core.enforcement import (
    _compute_credit_weights,
    _format_markdown,
    _match_cells,
    cli_ci_outcome_reporter,
    generate_ci_report,
)

__all__ = [
    "generate_ci_report",
    "_match_cells",
    "_compute_credit_weights",
    "_format_markdown",
    "main",
    "cli_ci_outcome_reporter",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.enforcement as _enf
    return getattr(_enf, name)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return cli_ci_outcome_reporter(argv)


if __name__ == "__main__":
    sys.exit(main())
