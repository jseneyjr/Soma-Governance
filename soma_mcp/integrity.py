"""Cell integrity verification via SHA-256 manifest.

Provides hash-based integrity checking for governance cells. A manifest file
(``.soma/cells/manifest.json``) stores SHA-256 hashes of all known cells.
During cell loading, hashes are verified to detect tampering or unauthorized
additions.

This is integrity checking (not cryptographic signing). It detects accidental
or unsophisticated changes. Key management and signatures are a follow-up.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone


_MANIFEST_FILENAME = "manifest.json"


def _hash_file(filepath: str) -> str:
    """Return the SHA-256 hex digest of a file's contents."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def generate_manifest(cells_dir: str) -> dict:
    """Generate a SHA-256 manifest of all cells under ``cells_dir``.

    Returns::

        {
            "cells": {"relative/path.md": "sha256:abc123...", ...},
            "generated_at": "2026-10-01T19:00:00Z",
            "cell_count": 42,
        }
    """
    cells = {}
    if not os.path.isdir(cells_dir):
        return {
            "cells": cells,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "cell_count": 0,
        }

    for dirpath, _dirnames, filenames in os.walk(cells_dir):
        for fn in filenames:
            if not fn.endswith(".md") or fn == "README.md":
                continue
            if fn == _MANIFEST_FILENAME:
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, cells_dir)
            cells[rel] = _hash_file(full)

    return {
        "cells": cells,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cell_count": len(cells),
    }


def verify_manifest(cells_dir: str, manifest: dict) -> list:
    """Verify cells against a manifest.

    Returns a list of issue dicts, each with keys:
    - ``type``: one of ``"added"``, ``"modified"``, ``"removed"``
    - ``path``: the relative cell path
    - ``detail``: human-readable description

    An empty list means all cells match the manifest.
    """
    issues = []
    known_cells = manifest.get("cells", {})

    # Discover current cells on disk
    current_cells = {}
    if os.path.isdir(cells_dir):
        for dirpath, _dirnames, filenames in os.walk(cells_dir):
            for fn in filenames:
                if not fn.endswith(".md") or fn == "README.md":
                    continue
                if fn == _MANIFEST_FILENAME:
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, cells_dir)
                current_cells[rel] = _hash_file(full)

    # Check for added cells (on disk but not in manifest)
    for rel in sorted(current_cells):
        if rel not in known_cells:
            issues.append({
                "type": "added",
                "path": rel,
                "detail": f"cell not in manifest (unknown origin): {rel}",
            })

    # Check for modified cells (hash mismatch)
    for rel in sorted(current_cells):
        if rel in known_cells and current_cells[rel] != known_cells[rel]:
            issues.append({
                "type": "modified",
                "path": rel,
                "detail": f"cell hash mismatch (content changed): {rel}",
            })

    # Check for removed cells (in manifest but not on disk)
    for rel in sorted(known_cells):
        if rel not in current_cells:
            issues.append({
                "type": "removed",
                "path": rel,
                "detail": f"cell in manifest but missing from disk: {rel}",
            })

    return issues


def load_manifest(workspace: str) -> dict | None:
    """Load the cell manifest from ``.soma/cells/manifest.json``.

    Returns None if the manifest file does not exist.
    """
    manifest_path = os.path.join(workspace, ".soma", "cells", _MANIFEST_FILENAME)
    if not os.path.isfile(manifest_path):
        return None
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        _warn(f"failed to load manifest: {exc}")
        return None


def save_manifest(workspace: str, manifest: dict) -> None:
    """Save a manifest to ``.soma/cells/manifest.json``."""
    manifest_path = os.path.join(workspace, ".soma", "cells", _MANIFEST_FILENAME)
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")


def _warn(message: str) -> None:
    """Emit a diagnostic on stderr (stdout is the JSON-RPC transport)."""
    try:
        print(f"[soma-integrity] {message}", file=sys.stderr, flush=True)
    except Exception:
        pass
