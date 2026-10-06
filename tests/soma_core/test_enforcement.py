"""1:1 mirrored contract test for soma_core.enforcement."""
from __future__ import annotations
import importlib
import pytest


def test_enforcement_module_contract():
    """Verify soma_core.enforcement imports cleanly and is non-null."""
    mod = importlib.import_module("soma_core.enforcement")
    assert mod is not None
