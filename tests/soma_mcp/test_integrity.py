"""1:1 mirrored contract test for soma_mcp.integrity."""
from __future__ import annotations
import importlib
import pytest


def test_integrity_module_contract():
    """Verify soma_mcp.integrity imports cleanly and is non-null."""
    mod = importlib.import_module("soma_mcp.integrity")
    assert mod is not None
