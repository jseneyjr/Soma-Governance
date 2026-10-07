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
import subprocess
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from soma_core.errors import (
    PathTraversalError,
    WorkspaceBareRepoError,
    WorkspaceError,
    WorkspaceNotFoundError,
)

_WINDOWS_DEVICE_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)


def _is_workspace_dir(d: str) -> bool:
    if os.path.isdir(os.path.join(d, ".soma", "cells")):
        return True
    try:
        home_str = str(Path.home())
    except Exception:
        home_str = ""
    if d not in ("/tmp", "/var/tmp", home_str):
        if os.path.isdir(os.path.join(d, ".soma")):
            return True
def _find_git_dirs(root: Path) -> tuple[Path | None, Path | None]:
    """Find (git_dir, git_common_dir) for a workspace root, walking up if necessary."""
    curr = root.resolve()
    while True:
        dot_git = curr / ".git"
        if dot_git.is_dir():
            return dot_git, dot_git
        elif dot_git.is_file():
            try:
                content = dot_git.read_text(encoding="utf-8", errors="replace").strip()
                if content.startswith("gitdir:"):
                    gitdir_str = content[7:].strip()
                    gitdir_path = Path(gitdir_str)
                    if not gitdir_path.is_absolute():
                        gitdir_path = (curr / gitdir_path).resolve()
                    commondir_file = gitdir_path / "commondir"
                    if commondir_file.is_file():
                        common_rel = commondir_file.read_text(encoding="utf-8").strip()
                        common_dir = (gitdir_path / common_rel).resolve()
                        return gitdir_path, common_dir
                    if gitdir_path.parent.name == "worktrees" and gitdir_path.parent.parent.is_dir():
                        return gitdir_path, gitdir_path.parent.parent
                    return gitdir_path, gitdir_path
            except (OSError, UnicodeError, ValueError):
                pass
        parent = curr.parent
        if parent == curr:
            break
        curr = parent
    return None, None


def _parse_worktree_porcelain(stdout: str) -> list[dict[str, Any]]:
    """Parse output of git worktree list --porcelain."""
    worktrees: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            if current and "path" in current:
                worktrees.append(current)
                current = {}
            continue
        if line.startswith("worktree "):
            if current and "path" in current:
                worktrees.append(current)
                current = {}
            current["path"] = Path(line[9:].strip())
            current["bare"] = False
            current["detached"] = False
            current["branch"] = None
            current["head"] = ""
        elif line.startswith("HEAD "):
            current["head"] = line[5:].strip()
        elif line.startswith("branch "):
            ref = line[7:].strip()
            prefix = "refs/heads/"
            current["branch"] = ref[len(prefix):] if ref.startswith(prefix) else ref
        elif line == "bare":
            current["bare"] = True
        elif line == "detached":
            current["detached"] = True
    if current and "path" in current:
        worktrees.append(current)
    return worktrees


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

    @property
    def is_git(self) -> bool:
        """True if this workspace is backed by a Git repository or worktree."""
        return (self.root / ".git").exists() or self.git_hooks_dir is not None

    def __fspath__(self) -> str:
        return str(self.root)

    def __str__(self) -> str:
        return str(self.root)

    def __repr__(self) -> str:
        return f"Workspace(root={self.root!r}, is_worktree={self.is_worktree})"

    def __truediv__(self, other: str | Path | os.PathLike[str]) -> Path:
        return self.root / other

    @classmethod
    def for_init(cls, path: str | Path | os.PathLike[str]) -> Workspace:
        """Construct a Workspace for initialization without requiring pre-existing .soma directory.

        Guards against symlink traversal escapes and non-directory files.
        """
        p = Path(path)
        if p.is_symlink():
            raise WorkspaceError(f"Workspace path cannot be a symlink: {p}")
        resolved = p.resolve()
        if resolved.is_file():
            raise WorkspaceError(f"Workspace path must be a directory, not a file: {resolved}")
        if cls is Workspace:
            dot_git = resolved / ".git"
            if dot_git.exists():
                return GitWorkspace(root=resolved)
        return cls(root=resolved)

    def scaffold(self, minimal: bool = False, dry_run: bool = False) -> list[Path]:
        """Scaffold standard directory structure for Soma governance.

        Creates .soma/cells/ and .soma/evidence/ (and .soma/metrics/).
        Guards against bare git repositories.
        """
        if (
            (self.root / "HEAD").is_file()
            and (self.root / "config").is_file()
            and (self.root / "objects").is_dir()
            and not (self.root / ".git").exists()
        ):
            raise WorkspaceBareRepoError(
                f"Cannot scaffold soma in a bare git repository: {self.root}"
            )

        dirs_to_create: list[Path] = [
            self.cells_dir / "walls",
            self.evidence_dir,
        ]
        if not minimal:
            dirs_to_create.extend([
                self.cells_dir / "vacuoles",
                self.cells_dir / "gates",
                self.metrics_dir,
            ])

        if not dry_run:
            for d in dirs_to_create:
                d.mkdir(parents=True, exist_ok=True)

        return dirs_to_create

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
        def _make_ws(cand_root: Path) -> Workspace:
            resolved_root = cand_root.resolve()
            if cls is Workspace:
                dot_git = resolved_root / ".git"
                if dot_git.exists() or _find_git_dirs(resolved_root)[0] is not None:
                    return GitWorkspace(root=resolved_root)
            return cls(root=resolved_root)

        if isinstance(start, Workspace):
            if cls is GitWorkspace and not isinstance(start, GitWorkspace):
                return GitWorkspace(root=start.root)
            return start

        # 1. SOMA_WORKSPACE env var
        soma_ws = os.environ.get("SOMA_WORKSPACE")
        if soma_ws:
            if os.path.isdir(os.path.join(soma_ws, ".soma", "cells")):
                return _make_ws(Path(soma_ws))
            elif strict_env:
                raise WorkspaceNotFoundError(
                    f"SOMA_WORKSPACE is set to {soma_ws} but no .soma/cells found there."
                )
            elif os.path.isdir(soma_ws):
                return _make_ws(Path(soma_ws))

        # 2. SOMA_ROOT env var
        soma_root = os.environ.get("SOMA_ROOT")
        if soma_root:
            if os.path.isdir(os.path.join(soma_root, ".soma", "cells")):
                return _make_ws(Path(soma_root))
            elif strict_env:
                raise WorkspaceNotFoundError(
                    f"SOMA_ROOT is set to {soma_root} but no .soma/cells found there."
                )
            elif os.path.isdir(soma_root):
                return _make_ws(Path(soma_root))

        # 3. Explicit start path walk-up
        if start is not None:
            cand = os.path.abspath(str(start))
            d = cand if os.path.isdir(cand) else os.path.dirname(cand)
            while d != os.path.dirname(d):
                if _is_workspace_dir(d):
                    return _make_ws(Path(d))
                d = os.path.dirname(d)
            return _make_ws(Path(cand if os.path.isdir(cand) else os.path.dirname(cand)))

        # 4. Check CWD directly
        cwd = os.getcwd()
        if _is_workspace_dir(cwd):
            return _make_ws(Path(cwd))

        # 5. Walk up from CWD
        d = cwd
        while d != os.path.dirname(d):
            if _is_workspace_dir(d):
                return _make_ws(Path(d))
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
                    return _make_ws(Path(d))
                d = os.path.dirname(d)

        # 7. Fallback to CWD
        return _make_ws(Path(cwd))

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

        resolved_path = Path(resolved)
        if cls is Workspace:
            dot_git = resolved_path / ".git"
            if dot_git.exists() or _find_git_dirs(resolved_path)[0] is not None:
                return GitWorkspace(root=resolved_path)
        return cls(root=resolved_path)

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


@dataclass(frozen=True, eq=False)
class GitWorkspace(Workspace):
    """A Soma workspace backed by a Git repository or linked worktree."""

    git_dir: Path | None = field(default=None)
    git_common_dir: Path | None = field(default=None)

    def __post_init__(self) -> None:
        super().__post_init__()
        resolved_root = self.root
        git_dir, common_dir = _find_git_dirs(resolved_root)
        if git_dir is not None:
            object.__setattr__(self, "git_dir", git_dir)
            object.__setattr__(self, "git_common_dir", common_dir or git_dir)
            if self.git_hooks_dir is None:
                hooks = resolve_git_hooks_dir(resolved_root)
                object.__setattr__(self, "git_hooks_dir", hooks)

    @property
    def is_git(self) -> bool:
        """True if this workspace is backed by a Git repository or worktree."""
        return bool(self.git_dir is not None and self.git_dir.exists())

    def __repr__(self) -> str:
        return f"GitWorkspace(root={self.root!r}, branch={self.branch_name!r}, is_worktree={self.is_worktree})"

    @property
    def head_commit(self) -> str | None:
        """Commit hash of HEAD, resolved using zero-subprocess fast paths when possible."""
        if not self.git_dir or not self.git_dir.exists():
            return None
        head_file = self.git_dir / "HEAD"
        if not head_file.is_file():
            return None
        try:
            head_content = head_file.read_text(encoding="utf-8", errors="replace").strip()
            if not head_content:
                return None
            if not head_content.startswith("ref:"):
                # Detached HEAD: direct commit SHA
                if len(head_content) in (40, 64) and all(c in "0123456789abcdefABCDEF" for c in head_content):
                    return head_content
                return None

            ref_path_rel = head_content[4:].strip()
            # Try loose ref in git_dir, then git_common_dir
            for base_dir in (self.git_dir, self.git_common_dir):
                candidate_ref = base_dir / ref_path_rel
                if candidate_ref.is_file():
                    sha = candidate_ref.read_text(encoding="utf-8", errors="replace").strip()
                    if sha:
                        return sha

            # Try packed-refs in git_common_dir
            packed_refs_file = self.git_common_dir / "packed-refs"
            if packed_refs_file.is_file():
                for line in packed_refs_file.read_text(encoding="utf-8", errors="replace").splitlines():
                    line = line.strip()
                    if not line or line.startswith(("#", "^")):
                        continue
                    parts = line.split(maxsplit=1)
                    if len(parts) == 2 and parts[1] == ref_path_rel:
                        return parts[0]
        except (OSError, UnicodeError, ValueError):
            pass

        # Fallback to subprocess
        res = self._run_git(["git", "rev-parse", "HEAD"])
        if res.returncode == 0:
            out = res.stdout.strip()
            if out:
                return out
        return None

    @property
    def branch_name(self) -> str | None:
        """Active branch name, or None if in detached HEAD state."""
        if not self.git_dir or not self.git_dir.exists():
            return None
        head_file = self.git_dir / "HEAD"
        if not head_file.is_file():
            return None
        try:
            head_content = head_file.read_text(encoding="utf-8", errors="replace").strip()
            prefix = "ref: refs/heads/"
            if head_content.startswith(prefix):
                return head_content[len(prefix):].strip()
            if head_content.startswith("ref:"):
                return None
            return None
        except (OSError, UnicodeError):
            pass

        # Fallback to subprocess
        res = self._run_git(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        if res.returncode == 0:
            b = res.stdout.strip()
            if b and b != "HEAD":
                return b
        return None

    def get_diff(self, staged: bool = False, base: str | None = None) -> str:
        """Extract unified diff from working tree, staged index, or base commit."""
        cmd = ["git", "diff", "--no-color", "--no-ext-diff"]
        if staged:
            cmd.append("--cached")
        if base:
            cmd.append(base)
        res = self._run_git(cmd)
        return res.stdout if res.returncode == 0 else ""

    def get_changed_files(self, staged: bool = False, base: str | None = None) -> list[str]:
        """List repo-relative paths of modified or added files."""
        cmd = ["git", "diff", "--name-only"]
        if staged:
            cmd.append("--cached")
        if base:
            cmd.append(base)
        res = self._run_git(cmd)
        if res.returncode != 0:
            return []
        return [line.strip() for line in res.stdout.splitlines() if line.strip()]

    def get_untracked_files(self) -> list[str]:
        """List untracked files respecting .gitignore."""
        res = self._run_git(["git", "ls-files", "--others", "--exclude-standard"])
        if res.returncode != 0:
            return []
        return [line.strip() for line in res.stdout.splitlines() if line.strip()]

    def list_worktrees(self) -> list[dict[str, Any]]:
        """Discover linked worktrees associated with this repository."""
        res = self._run_git(["git", "worktree", "list", "--porcelain"])
        if res.returncode != 0:
            return [{
                "path": self.root,
                "bare": False,
                "head": self.head_commit or "",
                "branch": self.branch_name,
                "detached": self.branch_name is None,
            }]
        return _parse_worktree_porcelain(res.stdout)

    def _run_git(self, cmd: list[str], timeout: float = 5.0) -> subprocess.CompletedProcess[str]:
        """Execute a git command confined to this repository root."""
        try:
            return subprocess.run(
                cmd,
                cwd=str(self.root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,
                stdout="",
                stderr=str(exc),
            )


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
    return get_signals_file(workspace)


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

    dot_git = root / ".git"
    if not dot_git.exists():
        return None

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
    _git_dir, common_dir = _find_git_dirs(root)
    if common_dir is not None:
        return common_dir / "hooks"

    return None


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
    "resolve_git_hooks_dir",
    "resolve_workspace",
    "resolve_workspace_path",
    "validate_cell_names",
]

