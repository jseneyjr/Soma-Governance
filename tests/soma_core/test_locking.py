"""1:1 mirrored contract test for soma_core.locking."""
from __future__ import annotations
import importlib
import pytest


def test_locking_module_contract():
    """Verify soma_core.locking imports cleanly and is non-null."""
    mod = importlib.import_module("soma_core.locking")
    assert mod is not None
