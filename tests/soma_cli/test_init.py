"""1:1 mirrored contract test for soma_cli.init."""
from __future__ import annotations
import importlib
import pytest


def test_init_module_contract():
    """Verify soma_cli.init imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.init")
    assert mod is not None
