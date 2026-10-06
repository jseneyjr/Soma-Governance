"""1:1 mirrored contract test for soma_sdk.errors."""
from __future__ import annotations
import importlib
import pytest


def test_errors_module_contract():
    """Verify soma_sdk.errors imports cleanly and is non-null."""
    mod = importlib.import_module("soma_sdk.errors")
    assert mod is not None
