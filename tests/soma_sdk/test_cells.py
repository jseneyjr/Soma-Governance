"""1:1 mirrored contract test for soma_sdk.cells."""
from __future__ import annotations
import importlib
import pytest


def test_cells_module_contract():
    """Verify soma_sdk.cells imports cleanly and is non-null."""
    mod = importlib.import_module("soma_sdk.cells")
    assert mod is not None
