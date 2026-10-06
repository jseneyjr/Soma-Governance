"""1:1 mirrored contract test for soma_core.workspace."""
from __future__ import annotations
import importlib
import pytest


def test_workspace_module_contract():
    """Verify soma_core.workspace imports cleanly and is non-null."""
    mod = importlib.import_module("soma_core.workspace")
    assert mod is not None
