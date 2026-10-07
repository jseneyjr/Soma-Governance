"""Workspace discovery and compound fingerprinting for Soma (Layer 0 Core).

Discovers project roots via environment variables, upward directory walks, and callers.
Provides compound fingerprinting (is_soma_repo) to distinguish Soma's own repository
from foreign repositories adopting Soma governance.
Strictly zero-dependency: uses only Python standard library.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from soma_core.errors import WorkspaceNotFoundError


def _is_workspace_dir(d: str) -> bool:
    """Check if directory contains a Soma workspace marker (.soma/cells or .soma)."""
    if os.path.isdir(os.path.join(d, ".soma", "cells")):
        return True
    try:
        home_str = str(Path.home())
    except Exception:
        home_str = ""
    if d not in ("/tmp", "/var/tmp", home_str):
        if os.path.isdir(os.path.join(d, ".soma")):
            return True
    return False


def is_soma_repo(root: Path) -> bool:
    """Compound check to verify if a workspace root is the core Soma repository.

    Requires:
    1. pyproject.toml containing non-commented name = 'soma-governance'
    2. Both soma_core/ and soma_cli/ directories exist.
    """
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return False

    try:
        content = pyproject.read_text(encoding="utf-8", errors="replace")
        # Match non-commented name = "soma-governance" or name = 'soma-governance'
        if not re.search(r'^[ \t]*name[ \t]*=[ \t]*["\']soma-governance["\']', content, re.MULTILINE):
            return False
    except OSError:
        return False

    return (root / "soma_core").is_dir() and (root / "soma_cli").is_dir()


def resolve_workspace_root(
    start: str | Path | os.PathLike[str] | None = None,
    caller_file: str | Path | os.PathLike[str] | None = None,
    strict_env: bool = False,
) -> Path:
    """Find the project root containing .soma/cells/ or .soma/.

    Resolution order:
    1. SOMA_WORKSPACE env var (if set)
       - If directory has .soma/cells, returns Path.
       - If strict_env is True and .soma/cells is missing, raises WorkspaceNotFoundError.
       - If directory exists, returns Path.
    2. SOMA_ROOT env var (if set)
       - If directory has .soma/cells, returns Path.
       - If strict_env is True and .soma/cells is missing, raises WorkspaceNotFoundError.
       - If directory exists, returns Path.
    3. Explicit start parameter (walks up from start)
    4. CWD (check if CWD has .soma/cells or .soma)
    5. Walk up from CWD
    6. Walk up from caller_file, skipping vendor/ directories
    7. Fallback to CWD
    """
    # 1. SOMA_WORKSPACE env var
    soma_ws = os.environ.get("SOMA_WORKSPACE")
    if soma_ws:
        if os.path.isdir(os.path.join(soma_ws, ".soma", "cells")):
            return Path(soma_ws).resolve()
        elif strict_env:
            raise WorkspaceNotFoundError(
                f"SOMA_WORKSPACE is set to {soma_ws} but no .soma/cells found there."
            )
        elif os.path.isdir(soma_ws):
            return Path(soma_ws).resolve()

    # 2. SOMA_ROOT env var
    soma_root = os.environ.get("SOMA_ROOT")
    if soma_root:
        if os.path.isdir(os.path.join(soma_root, ".soma", "cells")):
            return Path(soma_root).resolve()
        elif strict_env:
            raise WorkspaceNotFoundError(
                f"SOMA_ROOT is set to {soma_root} but no .soma/cells found there."
            )
        elif os.path.isdir(soma_root):
            return Path(soma_root).resolve()

    # 3. Explicit start path walk-up
    if start is not None:
        cand = os.path.abspath(str(start))
        d = cand if os.path.isdir(cand) else os.path.dirname(cand)
        while d != os.path.dirname(d):
            if _is_workspace_dir(d):
                return Path(d).resolve()
            d = os.path.dirname(d)
        return Path(cand if os.path.isdir(cand) else os.path.dirname(cand)).resolve()

    # 4. Check CWD directly
    cwd = os.getcwd()
    if _is_workspace_dir(cwd):
        return Path(cwd).resolve()

    # 5. Walk up from CWD
    d = cwd
    while d != os.path.dirname(d):
        if _is_workspace_dir(d):
            return Path(d).resolve()
        d = os.path.dirname(d)

    # 6. Walk up from caller_file (skipping vendor/ directories)
    if caller_file is not None:
        d = os.path.dirname(os.path.abspath(str(caller_file)))
        while d != os.path.dirname(d):
            if (
                _is_workspace_dir(d)
                and "/vendor/" not in d
                and os.path.basename(os.path.dirname(d)) != "vendor"
            ):
                return Path(d).resolve()
            d = os.path.dirname(d)

    # 7. Fallback to CWD
    return Path(cwd).resolve()


__all__ = [
    "_is_workspace_dir",
    "is_soma_repo",
    "resolve_workspace_root",
]
