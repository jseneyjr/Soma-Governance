"""1:1 mirrored contract test for soma_core.quarantine."""
from __future__ import annotations
import importlib
import pytest


def test_quarantine_module_contract():
    """Verify soma_core.quarantine imports cleanly and is non-null."""
    mod = importlib.import_module("soma_core.quarantine")
    assert mod is not None
