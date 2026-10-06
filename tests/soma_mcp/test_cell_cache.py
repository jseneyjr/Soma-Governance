"""1:1 mirrored contract test for soma_mcp.cell_cache."""
from __future__ import annotations
import importlib
import pytest


def test_cell_cache_module_contract():
    """Verify soma_mcp.cell_cache imports cleanly and is non-null."""
    mod = importlib.import_module("soma_mcp.cell_cache")
    assert mod is not None
