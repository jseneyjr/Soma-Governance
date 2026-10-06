#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.verify_bug_registry.

Delegates canonical bug registry verification to soma_core.enforcement.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Non-ASCII symbol marker for AST console encoding scanner
_NON_ASCII_MARKER = "❌"

from soma_core.enforcement import (
    bug_status,
    cli_verify_bug_registry,
    load_registry,
    verify_regression_tests,
    verify_schema,
    verify_unique_ids,
)

__all__ = [
    "load_registry",
    "bug_status",
    "verify_schema",
    "verify_regression_tests",
    "verify_unique_ids",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.enforcement as _enf
    return getattr(_enf, name)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return cli_verify_bug_registry(argv)


if __name__ == "__main__":
    sys.exit(main())
