"""1:1 mirrored contract test for soma_mcp.security."""
from __future__ import annotations
import importlib
import pytest


def test_security_module_contract():
    """Verify soma_mcp.security imports cleanly and is non-null."""
    mod = importlib.import_module("soma_mcp.security")
    assert mod is not None
