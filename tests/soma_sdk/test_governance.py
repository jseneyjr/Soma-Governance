"""1:1 mirrored contract test for soma_sdk.governance."""
from __future__ import annotations
import importlib
import pytest


def test_governance_module_contract():
    """Verify soma_sdk.governance imports cleanly and is non-null."""
    mod = importlib.import_module("soma_sdk.governance")
    assert mod is not None
