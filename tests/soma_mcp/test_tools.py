"""1:1 mirrored contract test for soma_mcp.tools."""
from __future__ import annotations
import importlib
import pytest


def test_tools_module_contract():
    """Verify soma_mcp.tools imports cleanly and is non-null."""
    mod = importlib.import_module("soma_mcp.tools")
    assert mod is not None
