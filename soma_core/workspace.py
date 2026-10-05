"""Shared workspace resolution and path containment for Soma (Layer 0 Core).

Single source of truth for:
- Workspace discovery (SOMA_WORKSPACE / SOMA_ROOT -> .soma/cells -> CWD walk-up)
- Directory paths (.soma/cells, .soma/metrics, .soma/evidence)
- Path confinement and security boundaries (cross-platform, Windows device names)

Strictly zero-dependency: uses only Python standard library.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Any, List, Optional, Tuple, Union

_WINDOWS_DEVICE_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)



def resolve_workspace(
    start: Optional[Union[str, Path]] = None,
    caller_file: Optional[Union[str, Path]] = None,
    strict_env: bool = False,
) -> str:
    """Find the project root containing .soma/cells/ or .soma/.

    Resolution order:
    1. SOMA_WORKSPACE env var (if set)
       - If directory has .soma/cells, returns abspath.
       - If strict_env is True and .soma/cells is missing, raises ValueError.
       - If directory exists, returns abspath.
    2. SOMA_ROOT env var (if set)
       - If directory has .soma/cells, returns abspath.
       - If strict_env is True and .soma/cells is missing, raises ValueError.
       - If directory exists, returns abspath.
    3. Explicit start parameter (walks up from start)
    4. CWD (check if CWD has .soma/cells or .soma)
    5. Walk up from CWD
    6. Walk up from caller_file, skipping vendor/ directories
    7. Fallback to CWD

    Returns:
        Absolute string path to workspace.
    """
    # 1. SOMA_WORKSPACE env var
    soma_ws = os.environ.get("SOMA_WORKSPACE")
    if soma_ws:
        if os.path.isdir(os.path.join(soma_ws, ".soma", "cells")):
            return os.path.abspath(soma_ws)
        elif strict_env:
            raise ValueError(f"SOMA_WORKSPACE is set to {soma_ws} but no .soma/cells found there.")
        elif os.path.isdir(soma_ws):
            return os.path.abspath(soma_ws)

    # 2. SOMA_ROOT env var
    soma_root = os.environ.get("SOMA_ROOT")
    if soma_root:
        if os.path.isdir(os.path.join(soma_root, ".soma", "cells")):
            return os.path.abspath(soma_root)
        elif strict_env:
            raise ValueError(f"SOMA_ROOT is set to {soma_root} but no .soma/cells found there.")
        elif os.path.isdir(soma_root):
            return os.path.abspath(soma_root)

    # 3. Explicit start path walk-up
    if start:
        cand = os.path.abspath(str(start))
        d = cand if os.path.isdir(cand) else os.path.dirname(cand)
        while d != os.path.dirname(d):
            if os.path.isdir(os.path.join(d, ".soma", "cells")) or os.path.isdir(os.path.join(d, ".soma")):
                return d
            d = os.path.dirname(d)
        return cand if os.path.isdir(cand) else os.path.dirname(cand)

    # 4. Check CWD directly
    cwd = os.getcwd()
    if os.path.isdir(os.path.join(cwd, ".soma", "cells")):
        return cwd

    # 5. Walk up from CWD
    d = cwd
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, ".soma", "cells")) or os.path.isdir(os.path.join(d, ".soma")):
            return d
        d = os.path.dirname(d)

    # 6. Walk up from caller_file (skipping vendor/ directories)
    if caller_file:
        d = os.path.dirname(os.path.abspath(str(caller_file)))
        while d != os.path.dirname(d):
            if os.path.isdir(os.path.join(d, ".soma", "cells")):
                if "/vendor/" not in d and os.path.basename(os.path.dirname(d)) != "vendor":
                    return d
            d = os.path.dirname(d)

    # 7. Fallback to CWD
    return cwd


def resolve_workspace_path(
    start: Optional[Union[str, Path]] = None,
    caller_file: Optional[Union[str, Path]] = None,
    strict_env: bool = False,
) -> Path:
    """Return workspace root as a resolved Path object."""
    return Path(resolve_workspace(start=start, caller_file=caller_file, strict_env=strict_env)).resolve()


def get_cells_dir(workspace: Optional[Union[str, Path]] = None) -> str:
    """Get the path to the .soma/cells directory."""
    ws = resolve_workspace(workspace) if workspace is None else str(workspace)
    return os.path.join(ws, ".soma", "cells")


def get_metrics_dir(workspace: Optional[Union[str, Path]] = None) -> str:
    """Get the path to the .soma/metrics directory."""
    ws = resolve_workspace(workspace) if workspace is None else str(workspace)
    return os.path.join(ws, ".soma", "metrics")


def get_signals_file(workspace: Optional[Union[str, Path]] = None) -> str:
    """Get the path to the canonical signals file."""
    ws = resolve_workspace(workspace) if workspace is None else str(workspace)
    return os.path.join(ws, ".soma", "evidence", "signals.jsonl")


def get_outcomes_file(workspace: Optional[Union[str, Path]] = None) -> str:
    """Deprecated alias for get_signals_file."""
    return get_signals_file(workspace)


def confine_workspace(untrusted_workspace: Union[str, Path]) -> str:
    """Validate and confine a workspace path.

    A valid workspace must:
    - Exist as a directory
    - Contain a .soma/cells/ subdirectory (proof of a valid Soma workspace)

    Returns the resolved absolute path.
    Raises ValueError on invalid or malicious input.
    """
    if not untrusted_workspace or not str(untrusted_workspace).strip():
        raise ValueError("workspace path must not be empty")

    resolved = os.path.realpath(str(untrusted_workspace))
    if not os.path.isdir(resolved):
        raise ValueError(f"workspace does not exist or is not a directory: {resolved}")

    cells_dir = os.path.join(resolved, ".soma", "cells")
    if not os.path.isdir(cells_dir):
        raise ValueError(f"not a valid Soma workspace (missing .soma/cells/): {resolved}")

    return resolved


def confine_path(untrusted_path: Union[str, Path], workspace: Union[str, Path]) -> Tuple[str, str]:
    """Resolve and confine a file path within a workspace.

    Returns (resolved_absolute, relative_to_workspace).
    Raises ValueError if the path escapes the workspace boundary.
    """
    p_str = str(untrusted_path) if untrusted_path is not None else ""
    if not p_str or not p_str.strip():
        raise ValueError("file path must not be empty")

    if "\x00" in p_str:
        raise ValueError("null bytes are not permitted in file paths")

    if p_str.startswith(("\\\\?\\", "\\\\.\\", "//?/", "//./")):
        raise ValueError("extended device namespace paths are not permitted")

    # Reject alternate data streams (e.g. file.txt:stream)
    if ":" in p_str:
        has_drive = re.match(r"^[a-zA-Z]:[\\/]", p_str)
        rest = p_str[2:] if has_drive else p_str
        if ":" in rest:
            raise ValueError(f"alternate data stream syntax (':') is not permitted: {p_str!r}")

    # Reject reserved Windows device names
    for seg in re.split(r"[\\/]", p_str):
        if not seg:
            continue
        base = seg.rstrip(". ").split(".")[0].upper()
        if base in _WINDOWS_DEVICE_NAMES:
            raise ValueError(f"reserved Windows device name not permitted: {p_str!r}")

    workspace_root = Path(workspace).resolve()
    candidate = Path(os.path.join(str(workspace), p_str)).resolve()

    if candidate == workspace_root:
        raise ValueError("refusing to treat the workspace root as a file")

    try:
        relative = candidate.relative_to(workspace_root)
    except ValueError:
        raise ValueError(
            f"path traversal blocked: {p_str!r} resolves to {candidate} "
            f"which is outside the workspace {workspace_root}"
        )

    return str(candidate), str(relative)


def validate_cell_names(cell_names: List[str], workspace: Union[str, Path]) -> List[str]:
    """Validate that cell names reference cells that actually exist.

    Returns a list of invalid names (empty list means all names are valid).
    """
    if not cell_names:
        return []

    cells_dir = os.path.join(str(workspace), ".soma", "cells")
    if not os.path.isdir(cells_dir):
        return list(cell_names)

    known = set()
    for dirpath, _dirnames, filenames in os.walk(cells_dir):
        for fn in filenames:
            if fn.endswith(".md") and fn != "README.md":
                known.add(os.path.splitext(fn)[0])

    return [name for name in cell_names if name not in known]


__all__ = [
    "resolve_workspace",
    "resolve_workspace_path",
    "get_cells_dir",
    "get_metrics_dir",
    "get_signals_file",
    "get_outcomes_file",
    "confine_workspace",
    "confine_path",
    "validate_cell_names",
]
