"""1:1 mirrored contract test for soma_cli.platforms.mcp."""
from __future__ import annotations
import importlib
import pytest


def test_mcp_module_contract():
    """Verify soma_cli.platforms.mcp imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.platforms.mcp")
    assert mod is not None
