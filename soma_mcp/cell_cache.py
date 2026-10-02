"""Content-fingerprinted in-memory cell cache for the MCP hot path."""
from __future__ import annotations

import os
import threading
from typing import Any, Iterable, Optional

from soma_core import cell_inventory
from soma_core.cell_inventory import CellInventoryEntry, CellInventoryError


class CellCacheError(RuntimeError):
    """Cell loading failed; cached or partial results were not returned."""

    def __init__(
        self,
        operation: str,
        path: str,
        message: str,
        cause: Optional[BaseException] = None,
    ) -> None:
        self.operation = operation
        self.path = path
        self.cause = cause
        super().__init__(f"cell cache {operation} failed for {path}: {message}")


class CellCache:
    """Thread-safe parsed-cell cache keyed by canonical content fingerprint."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cells = []  # type: list[dict[str, Any]]
        self._fingerprint = None  # type: Optional[str]
        self._workspace = None  # type: Optional[str]

    def get_cells(self, workspace: str) -> list[dict[str, Any]]:
        """Return cells, reparsing only when canonical inventory bytes change."""
        workspace_key = os.path.abspath(os.fspath(workspace))
        with self._lock:
            try:
                inventory = cell_inventory.inventory_cells(workspace_key)
            except CellInventoryError as exc:
                raise CellCacheError(
                    exc.operation, exc.path, str(exc), exc
                ) from exc

            if (
                self._workspace == workspace_key
                and self._fingerprint == inventory.fingerprint
            ):
                return self._cells

            cells = self._load(workspace_key, inventory.entries)
            self._cells = cells
            self._fingerprint = inventory.fingerprint
            self._workspace = workspace_key
            return self._cells

    def invalidate(self) -> None:
        """Force parsing on the next successful inventory."""
        with self._lock:
            self._fingerprint = None
            self._workspace = None

    @staticmethod
    def _load(
        workspace: str,
        entries: Iterable[CellInventoryEntry],
    ) -> list[dict[str, Any]]:
        """Parse the exact bytes already captured by canonical inventory."""
        from soma_mcp.jit_engine import parse_frontmatter, _get_body, warn

        cells = []
        for entry in entries:
            if os.path.basename(entry.relative_path) == "README.md":
                continue
            try:
                content = entry.content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise CellCacheError(
                    "decode", entry.absolute_path, str(exc), exc
                ) from exc
            try:
                fm = parse_frontmatter(content)
            except Exception as exc:
                raise CellCacheError(
                    "parse", entry.absolute_path, str(exc), exc
                ) from exc
            if fm is None:
                warn(
                    f"skipped cell {entry.relative_path}: "
                    "malformed YAML frontmatter"
                )
                continue
            if not fm:
                warn(f"skipped cell {entry.relative_path}: no frontmatter metadata")
                continue
            if fm.get("expired_at"):
                continue
            fm["_name"] = os.path.splitext(os.path.basename(entry.absolute_path))[0]
            fm["_path"] = entry.relative_path
            fm["_body"] = _get_body(content)
            fm["_full"] = content
            cells.append(fm)

        CellCache._verify_integrity(workspace)
        return cells

    @staticmethod
    def _verify_integrity(workspace: str) -> None:
        """Preserve optional manifest diagnostics without affecting cell bytes."""
        from soma_mcp.jit_engine import warn

        cells_dir = os.path.join(workspace, ".soma", "cells")
        try:
            from soma_mcp.integrity import (
                load_manifest,
                verify_manifest,
                load_key,
                verify_signature,
            )
            manifest = load_manifest(workspace)
            if manifest is None:
                return
            for issue in verify_manifest(cells_dir, manifest):
                warn(f"integrity: {issue['type']} — {issue['detail']}")
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
