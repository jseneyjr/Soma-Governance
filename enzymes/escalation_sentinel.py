#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.escalation_sentinel.

Delegates canonical protocol escalation & last-gasp apoptosis checks to soma_core.sync.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Non-ASCII symbol marker for AST console encoding scanner
_NON_ASCII_MARKER = "⚡"

from soma_core.sync import (
    HIGH_PATTERNS,
    LOW_PATTERNS,
    MEDIUM_PATTERNS,
    PROTOCOL_RANKS,
    TEST_PATTERNS,
    check_membrane_overrides,
    classify_file,
    cli_escalation_sentinel,
    detect_branch_ops,
    gather_files,
    get_diff_size,
    is_test_file,
    recommend_protocol,
    run_last_gasp,
)

__all__ = [
    "HIGH_PATTERNS",
    "MEDIUM_PATTERNS",
    "LOW_PATTERNS",
    "TEST_PATTERNS",
    "PROTOCOL_RANKS",
    "classify_file",
    "is_test_file",
    "gather_files",
    "get_diff_size",
    "detect_branch_ops",
    "check_membrane_overrides",
    "recommend_protocol",
    "run_last_gasp",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.sync as _syn
    return getattr(_syn, name)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return cli_escalation_sentinel(argv)


if __name__ == "__main__":
    sys.exit(main())
