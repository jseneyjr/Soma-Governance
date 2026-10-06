"""1:1 mirrored contract test for soma_core.schemas.cells."""
from __future__ import annotations
import importlib
import pytest


def test_cells_module_contract():
    """Verify soma_core.schemas.cells imports cleanly and is non-null."""
    mod = importlib.import_module("soma_core.schemas.cells")
    assert mod is not None
