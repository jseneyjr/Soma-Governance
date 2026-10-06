"""1:1 mirrored contract test for soma_core.sweep_session."""
from __future__ import annotations
import importlib
import pytest


def test_sweep_session_module_contract():
    """Verify soma_core.sweep_session imports cleanly and is non-null."""
    mod = importlib.import_module("soma_core.sweep_session")
    assert mod is not None
