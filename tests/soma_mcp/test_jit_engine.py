"""1:1 mirrored contract test for soma_mcp.jit_engine."""
from __future__ import annotations
import importlib
import pytest


def test_jit_engine_module_contract():
    """Verify soma_mcp.jit_engine imports cleanly and is non-null."""
    mod = importlib.import_module("soma_mcp.jit_engine")
    assert mod is not None
