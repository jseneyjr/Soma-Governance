"""Shared security utilities for the Soma MCP server.

Provides path confinement, workspace validation, and cell name verification
used across MCP tools to prevent path traversal and input injection attacks.
"""
from __future__ import annotations

import os
from pathlib import Path


def confine_workspace(untrusted_workspace: str) -> str:
    """Validate and confine a workspace path.

    A valid workspace must:
    - Exist as a directory
    - Contain a ``.soma/cells/`` subdirectory (proof it is a real Soma workspace)

    Returns the resolved absolute path.
    Raises ValueError on invalid or malicious input.
    """
    if not untrusted_workspace or not str(untrusted_workspace).strip():
        raise ValueError("workspace path must not be empty")

    resolved = os.path.realpath(untrusted_workspace)
    if not os.path.isdir(resolved):
        raise ValueError(f"workspace does not exist or is not a directory: {resolved}")

    cells_dir = os.path.join(resolved, ".soma", "cells")
    if not os.path.isdir(cells_dir):
        raise ValueError(
            f"not a valid Soma workspace (missing .soma/cells/): {resolved}"
        )

    return resolved


def confine_path(untrusted_path: str, workspace: str) -> tuple:
    """Resolve and confine a file path within a workspace.

    Mirrors the containment logic in ``enzymes/ttc_verifier.py:_contain_path``
    but exposed as a shared utility for all MCP tools.

    Returns (resolved_absolute, relative_to_workspace).
    Raises ValueError if the path escapes the workspace boundary.
    """
    if not untrusted_path or not str(untrusted_path).strip():
        raise ValueError("file path must not be empty")

    workspace_root = Path(workspace).resolve()
    # os.path.join returns untrusted_path unchanged when it is absolute,
    # so an absolute path outside the workspace still lands in the check below.
    candidate = Path(os.path.join(workspace, untrusted_path)).resolve()

    if candidate == workspace_root:
        raise ValueError("refusing to treat the workspace root as a file")

    try:
        relative = candidate.relative_to(workspace_root)
    except ValueError:
        raise ValueError(
            f"path traversal blocked: {untrusted_path!r} resolves to {candidate} "
            f"which is outside the workspace {workspace_root}"
        )

    return str(candidate), str(relative)


def validate_cell_names(cell_names: list, workspace: str) -> list:
    """Validate that cell names reference cells that actually exist.

    Scans ``.soma/cells/`` for all ``*.md`` files and checks each name
    in ``cell_names`` against the discovered inventory.

    Returns a list of invalid names (empty list means all names are valid).
    """
    if not cell_names:
        return []

    cells_dir = os.path.join(workspace, ".soma", "cells")
    if not os.path.isdir(cells_dir):
        # No cells directory → all names are invalid
        return list(cell_names)

    # Build inventory of known cell names (filename stems)
    known = set()
    for dirpath, _dirnames, filenames in os.walk(cells_dir):
        for fn in filenames:
            if fn.endswith(".md") and fn != "README.md":
                known.add(os.path.splitext(fn)[0])

    return [name for name in cell_names if name not in known]
