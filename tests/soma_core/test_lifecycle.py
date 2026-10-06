"""1:1 mirrored contract test for soma_core.lifecycle."""
from __future__ import annotations
import importlib
import pytest


def test_lifecycle_module_contract():
    """Verify soma_core.lifecycle imports cleanly and is non-null."""
    mod = importlib.import_module("soma_core.lifecycle")
    assert mod is not None
