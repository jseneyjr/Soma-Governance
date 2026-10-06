"""1:1 mirrored contract test for soma_core.storage."""
from __future__ import annotations
import importlib
import pytest


def test_storage_module_contract():
    """Verify soma_core.storage imports cleanly and is non-null."""
    mod = importlib.import_module("soma_core.storage")
    assert mod is not None
