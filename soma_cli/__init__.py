"""Soma CLI — user-facing governance commands."""
from __future__ import annotations

from pathlib import Path


def resolve_root(args, default=None):
    """Resolve project/repo root from args, checking _root then _project_root."""
    root = getattr(args, '_root', getattr(args, '_project_root', None))
    if root is not None:
        return Path(root)
    return default if default is not None else Path.cwd()
