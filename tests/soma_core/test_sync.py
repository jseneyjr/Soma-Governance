"""1:1 mirrored contract test for soma_core.sync."""
from __future__ import annotations
import importlib
import pytest


def test_sync_module_contract():
    """Verify soma_core.sync imports cleanly and is non-null."""
    mod = importlib.import_module("soma_core.sync")
    assert mod is not None
