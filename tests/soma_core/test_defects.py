"""1:1 mirrored contract test for soma_core.defects."""
from __future__ import annotations
import importlib
import pytest


def test_defects_module_contract():
    """Verify soma_core.defects imports cleanly and is non-null."""
    mod = importlib.import_module("soma_core.defects")
    assert mod is not None
