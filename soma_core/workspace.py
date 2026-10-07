"""Shared workspace resolution and path containment for Soma (Layer 0 Core).

Single source of truth for:
- Workspace discovery (SOMA_WORKSPACE / SOMA_ROOT -> .soma/cells -> CWD walk-up)
- Directory paths (.soma/cells, .soma/metrics, .soma/evidence)
- Path confinement and security boundaries (cross-platform, Windows device names)
- Strongly-typed Workspace value object implementing os.PathLike[str]

Strictly zero-dependency: uses only Python standard library.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from soma_core.errors import PathTraversalError, WorkspaceError, WorkspaceNotFoundError

_WINDOWS_DEVICE_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)


@dataclass(frozen=True, eq=False)
class Workspace(os.PathLike[str]):
    """Immutable, strongly-typed representation of a Soma project workspace.

    Implements os.PathLike[str] for seamless interoperability with open(),
    Path(), and os.path routines.
    """

    root: Path
    git_hooks_dir: Path | None = field(default=None)
    is_worktree: bool = field(default=False)

    def __post_init__(self) -> None:
        resolved_root = Path(self.root).resolve()
        object.__setattr__(self, "root", resolved_root)

        dot_git = resolved_root / ".git"
        is_wt = dot_git.is_file()
        object.__setattr__(self, "is_worktree", is_wt)

        if self.git_hooks_dir is None:
            hooks = resolve_git_hooks_dir(resolved_root)
            object.__setattr__(self, "git_hooks_dir", hooks)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Workspace):
            return self.root == other.root
        if isinstance(other, (str, Path, os.PathLike)):
            try:
                return self.root == Path(os.fspath(other)).resolve()
            except (TypeError, ValueError, OSError):
                return False
        return False

    def __hash__(self) -> int:
        return hash(self.root)

    @property
    def soma_dir(self) -> Path:
        """Path to .soma directory."""
        return self.root / ".soma"

    @property
    def cells_dir(self) -> Path:
        """Path to .soma/cells directory."""
        return self.root / ".soma" / "cells"

    @property
    def metrics_dir(self) -> Path:
        """Path to .soma/metrics directory."""
        return self.root / ".soma" / "metrics"

    @property
    def evidence_dir(self) -> Path:
        """Path to .soma/evidence directory."""
        return self.root / ".soma" / "evidence"

    @property
    def signals_file(self) -> Path:
        """Path to .soma/evidence/signals.jsonl file."""
        return self.evidence_dir / "signals.jsonl"

    def __fspath__(self) -> str:
        return str(self.root)

    def __str__(self) -> str:
        return str(self.root)

    def __repr__(self) -> str:
        return f"Workspace(root={self.root!r}, is_worktree={self.is_worktree})"

    def __truediv__(self, other: str | Path | os.PathLike[str]) -> Path:
        return self.root / other

    @classmethod
    def resolve(
        cls,
        start: str | Path | os.PathLike[str] | Workspace | None = None,
        caller_file: str | Path | os.PathLike[str] | None = None,
        strict_env: bool = False,
    ) -> Workspace:
        """Find the project root containing .soma/cells/ or .soma/.

        Resolution order:
        1. SOMA_WORKSPACE env var (if set)
           - If directory has .soma/cells, returns Workspace.
           - If strict_env is True and .soma/cells is missing, raises WorkspaceNotFoundError.
           - If directory exists, returns Workspace.
        2. SOMA_ROOT env var (if set)
           - If directory has .soma/cells, returns Workspace.
           - If strict_env is True and .soma/cells is missing, raises WorkspaceNotFoundError.
           - If directory exists, returns Workspace.
        3. Explicit start parameter (walks up from start)
        4. CWD (check if CWD has .soma/cells or .soma)
        5. Walk up from CWD
        6. Walk up from caller_file, skipping vendor/ directories
        7. Fallback to CWD
        """
        if isinstance(start, Workspace):
            return start

        # 1. SOMA_WORKSPACE env var
        soma_ws = os.environ.get("SOMA_WORKSPACE")
        if soma_ws:
            if os.path.isdir(os.path.join(soma_ws, ".soma", "cells")):
                return cls(root=Path(soma_ws))
            elif strict_env:
                raise WorkspaceNotFoundError(
                    f"SOMA_WORKSPACE is set to {soma_ws} but no .soma/cells found there."
                )
            elif os.path.isdir(soma_ws):
                return cls(root=Path(soma_ws))

        # 2. SOMA_ROOT env var
        soma_root = os.environ.get("SOMA_ROOT")
        if soma_root:
            if os.path.isdir(os.path.join(soma_root, ".soma", "cells")):
                return cls(root=Path(soma_root))
            elif strict_env:
                raise WorkspaceNotFoundError(
                    f"SOMA_ROOT is set to {soma_root} but no .soma/cells found there."
                )
            elif os.path.isdir(soma_root):
                return cls(root=Path(soma_root))

        # 3. Explicit start path walk-up
        if start is not None:
            cand = os.path.abspath(str(start))
            d = cand if os.path.isdir(cand) else os.path.dirname(cand)
            while d != os.path.dirname(d):
                if os.path.isdir(os.path.join(d, ".soma", "cells")) or os.path.isdir(os.path.join(d, ".soma")):
                    return cls(root=Path(d))
                d = os.path.dirname(d)
            return cls(root=Path(cand if os.path.isdir(cand) else os.path.dirname(cand)))

        # 4. Check CWD directly
        cwd = os.getcwd()
        if os.path.isdir(os.path.join(cwd, ".soma", "cells")):
            return cls(root=Path(cwd))

        # 5. Walk up from CWD
        d = cwd
        while d != os.path.dirname(d):
            if os.path.isdir(os.path.join(d, ".soma", "cells")) or os.path.isdir(os.path.join(d, ".soma")):
                return cls(root=Path(d))
            d = os.path.dirname(d)

        # 6. Walk up from caller_file (skipping vendor/ directories)
        if caller_file is not None:
            d = os.path.dirname(os.path.abspath(str(caller_file)))
            while d != os.path.dirname(d):
                if (
                    os.path.isdir(os.path.join(d, ".soma", "cells"))
                    and "/vendor/" not in d
                    and os.path.basename(os.path.dirname(d)) != "vendor"
                ):
                    return cls(root=Path(d))
                d = os.path.dirname(d)

        # 7. Fallback to CWD
        return cls(root=Path(cwd))

    @classmethod
    def confine(
        cls,
        untrusted_workspace: str | Path | os.PathLike[str] | Workspace,
    ) -> Workspace:
        """Validate and confine a workspace path.

        A valid workspace must:
        - Exist as a directory
        - Contain a .soma/cells/ subdirectory (proof of a valid Soma workspace)

        Returns a Workspace instance.
        Raises WorkspaceError / WorkspaceNotFoundError on invalid or malicious input.
        """
        if isinstance(untrusted_workspace, Workspace):
            return untrusted_workspace

        if not untrusted_workspace or not str(untrusted_workspace).strip():
            raise WorkspaceError("workspace path must not be empty")

        resolved = os.path.realpath(str(untrusted_workspace))
        if not os.path.isdir(resolved):
            raise WorkspaceNotFoundError(f"workspace does not exist or is not a directory: {resolved}")

        cells_dir = os.path.join(resolved, ".soma", "cells")
        if not os.path.isdir(cells_dir):
            raise WorkspaceError(f"not a valid Soma workspace (missing .soma/cells/): {resolved}")

        return cls(root=Path(resolved))

    def confine_path(self, untrusted_path: str | Path | os.PathLike[str]) -> tuple[str, str]:
        """Resolve and confine a file path within this workspace.

        Returns (resolved_absolute, relative_to_workspace).
        Raises PathTraversalError if the path escapes the workspace boundary.
        """
        p_str = str(untrusted_path) if untrusted_path is not None else ""
        if not p_str or not p_str.strip():
            raise PathTraversalError("file path must not be empty")

        if "\x00" in p_str:
            raise PathTraversalError("null bytes are not permitted in file paths")

        if p_str.startswith(("\\\\?\\", "\\\\.\\", "//?/", "//./")):
            raise PathTraversalError("extended device namespace paths are not permitted")

        # Reject alternate data streams (e.g. file.txt:stream)
        if ":" in p_str:
            has_drive = re.match(r"^[a-zA-Z]:[\\/]", p_str)
            rest = p_str[2:] if has_drive else p_str
            if ":" in rest:
                raise PathTraversalError(f"alternate data stream syntax (':') is not permitted: {p_str!r}")

        # Reject reserved Windows device names
        for seg in re.split(r"[\\/]", p_str):
            if not seg:
                continue
            base = seg.rstrip(". ").split(".")[0].upper()
            if base in _WINDOWS_DEVICE_NAMES:
                raise PathTraversalError(f"reserved Windows device name not permitted: {p_str!r}")

        workspace_root = self.root.resolve()
        candidate = Path(os.path.join(str(workspace_root), p_str)).resolve()

        if candidate == workspace_root:
            raise PathTraversalError("refusing to treat the workspace root as a file")

        try:
            relative = candidate.relative_to(workspace_root)
        except ValueError:
            raise PathTraversalError(
                f"path traversal blocked: {p_str!r} resolves to {candidate} "
                f"which is outside the workspace {workspace_root}"
            )

        return str(candidate), str(relative)

    def validate_cell_names(self, cell_names: list[str]) -> list[str]:
        """Validate that cell names reference cells that actually exist.

        Returns a list of invalid names (empty list means all names are valid).
        """
        if not cell_names:
            return []

        cells_dir = self.cells_dir
        if not cells_dir.is_dir():
            return list(cell_names)

        known = set()
        for dirpath, _dirnames, filenames in os.walk(str(cells_dir)):
            for fn in filenames:
                if fn.endswith(".md") and fn != "README.md":
                    known.add(os.path.splitext(fn)[0])

        return [name for name in cell_names if name not in known]


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
    """Get the path to the .soma/cells directory."""
    ws = workspace if isinstance(workspace, Workspace) else (
        Workspace(root=Path(workspace).resolve()) if workspace is not None else Workspace.resolve()
    )
    return str(ws.cells_dir)


def get_metrics_dir(workspace: str | Path | os.PathLike[str] | Workspace | None = None) -> str:
    """Get the path to the .soma/metrics directory."""
    ws = workspace if isinstance(workspace, Workspace) else (
        Workspace(root=Path(workspace).resolve()) if workspace is not None else Workspace.resolve()
    )
    return str(ws.metrics_dir)


def get_signals_file(workspace: str | Path | os.PathLike[str] | Workspace | None = None) -> str:
    """Get the path to the canonical signals file."""
    ws = workspace if isinstance(workspace, Workspace) else (
        Workspace(root=Path(workspace).resolve()) if workspace is not None else Workspace.resolve()
    )
    return str(ws.signals_file)


def get_outcomes_file(workspace: str | Path | os.PathLike[str] | Workspace | None = None) -> str:
    """Deprecated alias for get_signals_file."""
    return get_signals_file(workspace)


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
    return Workspace(root=Path(workspace).resolve()).confine_path(untrusted_path)


def validate_cell_names(
    cell_names: list[str],
    workspace: str | Path | os.PathLike[str] | Workspace,
) -> list[str]:
    """Validate that cell names reference cells that actually exist."""
    ws = workspace if isinstance(workspace, Workspace) else Workspace(root=Path(workspace).resolve())
    return ws.validate_cell_names(cell_names)


find_workspace_root = resolve_workspace


def resolve_git_hooks_dir(project_root: str | Path | os.PathLike[str] | None = None) -> Path | None:
    """Resolve the git hooks directory for a project root or worktree.

    Handles:
    1. Standard repository (.git is a directory -> .git/hooks)
    2. Git worktree (.git is a file containing 'gitdir: <path>')
       Resolves common_dir or parent .git/hooks.
    3. Git rev-parse --git-path hooks fallback when git CLI is available.

    Returns Path to hooks directory, or None if not inside a git repository.
    """
    root = Path(project_root or Path.cwd()).resolve()

    # 1. Try git CLI if available (handles core.hooksPath and custom setups)
    try:
        import subprocess

        res = subprocess.run(
            ["git", "rev-parse", "--git-path", "hooks"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if res.returncode == 0:
            p = res.stdout.strip()
            if p:
                hooks_path = Path(p)
                if not hooks_path.is_absolute():
                    hooks_path = (root / hooks_path).resolve()
                return hooks_path
    except (subprocess.SubprocessError, FileNotFoundError, PermissionError, UnicodeDecodeError, OSError):
        pass

    # 2. Pure Python fallback (zero external CLI dependencies)
    dot_git = root / ".git"
    if dot_git.is_dir():
        return dot_git / "hooks"
    elif dot_git.is_file():
        try:
            content = dot_git.read_text(encoding="utf-8", errors="replace").strip()
            if content.startswith("gitdir:"):
                gitdir_str = content[7:].strip()
                gitdir_path = Path(gitdir_str)
                if not gitdir_path.is_absolute():
                    gitdir_path = (root / gitdir_path).resolve()

                # In worktrees, commondir points back to the main .git dir
                commondir_file = gitdir_path / "commondir"
                if commondir_file.is_file():
                    common_rel = commondir_file.read_text(encoding="utf-8").strip()
                    common_dir = (gitdir_path / common_rel).resolve()
                    return common_dir / "hooks"

                # If inside .git/worktrees/<name>, traverse up to .git/hooks
                if gitdir_path.parent.name == "worktrees" and gitdir_path.parent.parent.is_dir():
                    return gitdir_path.parent.parent / "hooks"

                return gitdir_path / "hooks"
        except (OSError, UnicodeError, ValueError):
            return None

    return None


__all__ = [
    "Workspace",
    "confine_path",
    "confine_workspace",
    "find_workspace_root",
    "get_cells_dir",
    "get_metrics_dir",
    "get_outcomes_file",
    "get_signals_file",
    "resolve_git_hooks_dir",
    "resolve_workspace",
    "resolve_workspace_path",
    "validate_cell_names",
]

