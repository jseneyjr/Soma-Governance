"""1:1 mirrored contract test for soma_core.receipts."""
from __future__ import annotations
import importlib
import pytest


def test_receipts_module_contract():
    """Verify soma_core.receipts imports cleanly and is non-null."""
    mod = importlib.import_module("soma_core.receipts")
    assert mod is not None
