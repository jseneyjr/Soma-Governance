"""1:1 mirrored contract test for soma_mcp.server."""
from __future__ import annotations
import importlib
import pytest


def test_server_module_contract():
    """Verify soma_mcp.server imports cleanly and is non-null."""
    mod = importlib.import_module("soma_mcp.server")
    assert mod is not None
