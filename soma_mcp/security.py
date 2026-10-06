"""Shared security utilities for the Soma MCP server.

Delegates path confinement, workspace validation, and cell name verification
to the canonical single-authority implementation in soma_core.workspace.
"""
from __future__ import annotations

from soma_core.workspace import (
    _WINDOWS_DEVICE_NAMES,
    confine_path,
    confine_workspace,
    validate_cell_names,
)

__all__ = [
    "_WINDOWS_DEVICE_NAMES",
    "confine_workspace",
    "confine_path",
    "validate_cell_names",
]
