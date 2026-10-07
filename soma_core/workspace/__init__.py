"""Shared workspace resolution and path containment for Soma (Layer 0 Core).

Modular package architecture providing:
- Workspace value object (base.py)
- GitWorkspace with zero-subprocess fast paths (git.py)
- Workspace discovery & compound fingerprinting (discovery.py)
- Path confinement and security boundaries (confinement.py)
- Scaffolding and initialization (scaffold.py)
- Git hook directory resolution (hooks.py)

Strictly zero-dependency: uses only Python standard library.
"""
from __future__ import annotations

import os
import warnings
from pathlib import Path

from soma_core.errors import PathTraversalError
from soma_core.workspace.base import Workspace
from soma_core.workspace.confinement import (
    _WINDOWS_DEVICE_NAMES,
    confine_path_internal,
    validate_workspace_path,
)
from soma_core.workspace.discovery import (
    _is_workspace_dir,
    is_soma_repo,
    resolve_workspace_root,
)
from soma_core.workspace.git import GitWorkspace, _parse_worktree_porcelain
from soma_core.workspace.hooks import _find_git_dirs, resolve_git_hooks_dir
from soma_core.workspace.scaffold import scaffold_workspace


def resolve_workspace(
    start: str | Path | os.PathLike[str] | Workspace | None = None,
    caller_file: str | Path | os.PathLike[str] | None = None,
    strict_env: bool = False,
) -> str:
    """Find the project root containing .soma/cells/ or .soma/."""
    return str(Workspace.resolve(start=start, caller_file=caller_file, strict_env=strict_env).root)


def resolve_workspace_path(
    start: str | Path | os.PathLike[str] | Workspace | None = None,
    caller_file: str | Path | os.PathLike[str] | None = None,
    strict_env: bool = False,
) -> Path:
    """Return workspace root as a resolved Path object."""
    return Workspace.resolve(start=start, caller_file=caller_file, strict_env=strict_env).root


def get_cells_dir(workspace: str | Path | os.PathLike[str] | Workspace | None = None) -> str:
    """Get the path to the .soma/cells directory (deprecated)."""
    warnings.warn(
        "get_cells_dir is deprecated and will be removed in v1.0.0; use Workspace.cells_dir or ws.cells_dir instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    ws = workspace if isinstance(workspace, Workspace) else (
        Workspace(root=Path(workspace).resolve()) if workspace is not None else Workspace.resolve()
    )
    return str(ws.cells_dir)


def get_metrics_dir(workspace: str | Path | os.PathLike[str] | Workspace | None = None) -> str:
    """Get the path to the .soma/metrics directory (deprecated)."""
    warnings.warn(
        "get_metrics_dir is deprecated and will be removed in v1.0.0; use Workspace.metrics_dir or ws.metrics_dir instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    ws = workspace if isinstance(workspace, Workspace) else (
        Workspace(root=Path(workspace).resolve()) if workspace is not None else Workspace.resolve()
    )
    return str(ws.metrics_dir)


def get_signals_file(workspace: str | Path | os.PathLike[str] | Workspace | None = None) -> str:
    """Get the path to the canonical signals file (deprecated)."""
    warnings.warn(
        "get_signals_file is deprecated and will be removed in v1.0.0; use Workspace.signals_file or ws.signals_file instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    ws = workspace if isinstance(workspace, Workspace) else (
        Workspace(root=Path(workspace).resolve()) if workspace is not None else Workspace.resolve()
    )
    return str(ws.signals_file)


def get_outcomes_file(workspace: str | Path | os.PathLike[str] | Workspace | None = None) -> str:
    """Deprecated alias for get_signals_file."""
    warnings.warn(
        "get_outcomes_file is deprecated and will be removed in v1.0.0; use Workspace.signals_file or ws.signals_file instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    ws = workspace if isinstance(workspace, Workspace) else (
        Workspace(root=Path(workspace).resolve()) if workspace is not None else Workspace.resolve()
    )
    return str(ws.signals_file)


def as_workspace(workspace: str | Path | os.PathLike[str] | Workspace | None = None) -> Workspace:
    """Coerce any workspace representation into a strongly-typed Workspace value object."""
    if isinstance(workspace, Workspace):
        return workspace
    if workspace:
        return Workspace.resolve(start=workspace)
    return Workspace.resolve()


def confine_workspace(untrusted_workspace: str | Path | os.PathLike[str] | Workspace) -> str:
    """Validate and confine a workspace path."""
    return str(Workspace.confine(untrusted_workspace).root)


def confine_path(
    untrusted_path: str | Path | os.PathLike[str],
    workspace: str | Path | os.PathLike[str] | Workspace,
) -> tuple[str, str]:
    """Resolve and confine a file path within a workspace."""
    if isinstance(workspace, Workspace):
        return workspace.confine_path(untrusted_path)
    p_str = str(untrusted_path) if untrusted_path is not None else ""
    if not p_str or not p_str.strip():
        raise PathTraversalError("file path must not be empty")
    return Workspace.resolve(start=workspace).confine_path(untrusted_path)


def validate_cell_names(
    cell_names: list[str],
    workspace: str | Path | os.PathLike[str] | Workspace,
) -> list[str]:
    """Validate that cell names reference cells that actually exist."""
    ws = workspace if isinstance(workspace, Workspace) else Workspace.resolve(start=workspace)
    return ws.validate_cell_names(cell_names)


find_workspace_root = resolve_workspace


__all__ = [
    "GitWorkspace",
    "Workspace",
    "as_workspace",
    "confine_path",
    "confine_workspace",
    "find_workspace_root",
    "get_cells_dir",
    "get_metrics_dir",
    "get_outcomes_file",
    "get_signals_file",
    "is_soma_repo",
    "resolve_git_hooks_dir",
    "resolve_workspace",
    "resolve_workspace_path",
    "validate_cell_names",
    "_WINDOWS_DEVICE_NAMES",
    "_find_git_dirs",
    "_is_workspace_dir",
    "_parse_worktree_porcelain",
]
