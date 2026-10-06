"""1:1 mirrored contract test for soma_core.errors."""
from __future__ import annotations
import importlib
import pytest


def test_errors_module_contract():
    """Verify soma_core.errors imports cleanly and is non-null."""
    mod = importlib.import_module("soma_core.errors")
    assert mod is not None
