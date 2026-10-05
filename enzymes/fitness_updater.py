#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.fitness_updater.

Delegates canonical transcript fitness updates to soma_core.telemetry.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from soma_core.telemetry import (
    cli_fitness_updater,
    detect_platform,
    extract_modified_files,
    match_cells,
    resolve_transcript_id,
    update_fitness,
)

__all__ = [
    "detect_platform",
    "resolve_transcript_id",
    "extract_modified_files",
    "match_cells",
    "update_fitness",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.telemetry as _tel
    return getattr(_tel, name)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return cli_fitness_updater(argv)


if __name__ == "__main__":
    sys.exit(main())
