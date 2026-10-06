"""1:1 mirrored contract test for soma_sdk.invariants."""
from __future__ import annotations
import importlib
import pytest


def test_invariants_module_contract():
    """Verify soma_sdk.invariants imports cleanly and is non-null."""
    mod = importlib.import_module("soma_sdk.invariants")
    assert mod is not None
