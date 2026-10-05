#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.verify_readme_claims.

Delegates canonical README claim verification to soma_core.enforcement.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from soma_core.enforcement import (
    cli_verify_readme_claims,
    verify_readme_claims,
)

__all__ = [
    "verify_readme_claims",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.enforcement as _enf
    return getattr(_enf, name)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return cli_verify_readme_claims(argv)


if __name__ == "__main__":
    sys.exit(main())
