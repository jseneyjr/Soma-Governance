"""Mtime-based in-memory cell cache for MCP hot path.

v0.83 'Fast Path': Eliminates redundant disk I/O by caching parsed cell
frontmatter and invalidating only when the cells directory mtime changes.

Thread-safe via simple lock (MCP server may handle concurrent requests).
"""
from __future__ import annotations

import glob
import os
import threading
from typing import Any


class CellCache:
    """In-memory cache for parsed governance cells.

    Checks ``os.stat(cells_dir).st_mtime`` on each call. If unchanged,
    returns the cached list. If changed, re-globs and re-parses all cells.

    Also tracks individual file mtimes to detect in-place edits that may
    not update the directory mtime on all filesystems.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cells: list[dict[str, Any]] = []
        self._dir_mtime: float = 0.0
        self._file_mtimes: dict[str, float] = {}
        self._workspace: str | None = None

    def get_cells(self, workspace: str) -> list[dict[str, Any]]:
        """Return cached cell list, re-parsing only if files changed."""
        cells_dir = os.path.join(workspace, '.soma', 'cells')

        if not os.path.isdir(cells_dir):
            return []

        with self._lock:
            # Check if directory mtime changed or workspace switched
            try:
                current_mtime = CellCache._get_tree_mtime(cells_dir)
            except OSError:
                return []

            if (self._workspace == workspace
                    and current_mtime == self._dir_mtime
                    and self._cells is not None):
                return self._cells

            # Cache miss — re-parse all cells
            self._cells = self._load(workspace, cells_dir)
            self._dir_mtime = current_mtime
            self._workspace = workspace
            return self._cells

    def invalidate(self) -> None:
        """Force cache invalidation on next call."""
        with self._lock:
            self._dir_mtime = 0.0
            self._file_mtimes.clear()

    @staticmethod
    def _load(workspace: str, cells_dir: str) -> list[dict[str, Any]]:
        """Parse all cell files from disk. Mirrors load_all_cells() logic."""
        # Lazy import to avoid circular dependency (jit_engine → cell_cache → jit_engine)
        from soma_mcp.jit_engine import parse_frontmatter, _get_body, warn

        cells = []
        for cell_file in glob.glob(
            os.path.join(cells_dir, '**', '*.md'), recursive=True
        ):
            if os.path.basename(cell_file) == 'README.md':
                continue
            rel = os.path.relpath(cell_file, workspace)
            try:
                with open(cell_file, encoding='utf-8') as f:
                    content = f.read()
                fm = parse_frontmatter(content)
                if fm is None:
                    warn(f'skipped cell {rel}: malformed YAML frontmatter')
                    continue
                if not fm:
                    warn(f'skipped cell {rel}: no frontmatter metadata')
                    continue
                if fm.get('expired_at'):
                    continue
                fm['_name'] = os.path.splitext(os.path.basename(cell_file))[0]
                fm['_path'] = rel
                fm['_body'] = _get_body(content)
                fm['_full'] = content
                cells.append(fm)
            except Exception as e:
                warn(f'skipped cell {rel}: {e.__class__.__name__}: {e}')

        # Integrity verification: check cells against manifest if present.
        # Graceful degradation — warnings only, never blocks cell loading.
        try:
            from soma_mcp.integrity import (
                load_manifest, verify_manifest, load_key, verify_signature,
            )
            manifest = load_manifest(workspace)
            if manifest is not None:
                issues = verify_manifest(cells_dir, manifest)
                for issue in issues:
                    warn(
                        f"integrity: {issue['type']} — {issue['detail']}"
                    )
                # HMAC signature verification
                key = load_key(workspace)
                if key is not None and "signature" in manifest:
                    if verify_signature(manifest, key):
                        warn("integrity: HMAC signature verified ✓")
                    else:
                        warn(
                            "integrity: HMAC signature verification FAILED "
                            "— manifest may be tampered"
                        )
        except Exception as exc:
            warn(f"integrity check failed (non-fatal): {exc}")

        return cells

    @staticmethod
    def _get_tree_mtime(cells_dir: str) -> float:
        """Get the maximum mtime across the cells directory tree.

        Checks subdirectory mtimes too, since adding a file to a subdirectory
        updates that subdirectory's mtime, not the root directory's.
        """
        max_mtime = os.stat(cells_dir).st_mtime
        for dirpath, _dirnames, filenames in os.walk(cells_dir):
            dir_mtime = os.stat(dirpath).st_mtime
            if dir_mtime > max_mtime:
                max_mtime = dir_mtime
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                try:
                    fmtime = os.stat(fpath).st_mtime
                    if fmtime > max_mtime:
                        max_mtime = fmtime
                except OSError:
                    pass
        return max_mtime
