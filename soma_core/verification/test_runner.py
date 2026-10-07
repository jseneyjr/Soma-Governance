"""Centralized test runner discovery for Soma verification subsystem."""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from soma_core.errors import NoTestRunnerFoundError


def resolve_pytest_cmd(
    workspace: Any = None,
    required: bool = False,
) -> list[str]:
    """Resolve the appropriate pytest command for the workspace.

    Probing order:
    1. Active virtual environment ($VIRTUAL_ENV/bin/pytest or Scripts/pytest.exe)
    2. Local workspace virtual environment (.venv/bin/pytest or Scripts/pytest.exe)
    3. System pytest executable on PATH (shutil.which("pytest"))
    4. Current Python interpreter if pytest package is installed

    Args:
        workspace: Optional Workspace instance or root Path/str.
        required: If True, raises NoTestRunnerFoundError if no runner is found.

    Returns:
        List of command arguments, e.g. ["/path/to/pytest"] or [sys.executable, "-m", "pytest"].
        Returns empty list [] if not found and required is False.

    Raises:
        NoTestRunnerFoundError: If required is True and no runner is discovered.
    """
    # 1. Active virtual environment
    venv_str = os.environ.get("VIRTUAL_ENV")
    if venv_str:
        venv_path = Path(venv_str)
        for cand in (venv_path / "bin" / "pytest", venv_path / "Scripts" / "pytest.exe"):
            if cand.is_file():
                if os.name == "nt" or os.access(cand, os.X_OK):
                    return [str(cand)]

    # 2. Local workspace virtual environment (.venv)
    root = None
    if workspace is not None:
        if hasattr(workspace, "cells_dir") and hasattr(workspace, "root"):
            # Soma Workspace instance
            root = Path(workspace.root)
        else:
            try:
                root = Path(workspace)
            except Exception:
                root = None

    if root is not None:
        local_venv = Path(root) / ".venv"
        for cand in (local_venv / "bin" / "pytest", local_venv / "Scripts" / "pytest.exe"):
            if cand.is_file():
                if os.name == "nt" or os.access(cand, os.X_OK):
                    return [str(cand)]

    # 3. System pytest executable on PATH
    which_pytest = shutil.which("pytest")
    if which_pytest:
        return [which_pytest]

    # 4. Current Python interpreter if pytest module is importable
    try:
        spec = importlib.util.find_spec("pytest")
        if spec is not None:
            return [sys.executable, "-m", "pytest"]
    except Exception:
        pass

    if required:
        raise NoTestRunnerFoundError("No pytest runner found in virtual environment, .venv, or PATH")

    return []


__all__ = [
    "NoTestRunnerFoundError",
    "resolve_pytest_cmd",
]
