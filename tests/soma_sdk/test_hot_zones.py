"""1:1 mirrored contract test for soma_sdk.hot_zones."""
from __future__ import annotations
import importlib
import pytest


def test_hot_zones_module_contract():
    """Verify soma_sdk.hot_zones imports cleanly and is non-null."""
    mod = importlib.import_module("soma_sdk.hot_zones")
    assert mod is not None
