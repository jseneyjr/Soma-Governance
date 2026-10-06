"""1:1 mirrored contract test for immune_system.verification.call_graph."""
from __future__ import annotations
import importlib
import pytest


def test_call_graph_module_contract():
    """Verify immune_system.verification.call_graph imports cleanly and is non-null."""
    mod = importlib.import_module("immune_system.verification.call_graph")
    assert mod is not None
