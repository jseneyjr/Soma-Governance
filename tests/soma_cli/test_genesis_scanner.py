"""1:1 mirrored contract test for soma_cli.genesis_scanner."""
from __future__ import annotations
import importlib
import pytest


def test_genesis_scanner_module_contract():
    """Verify soma_cli.genesis_scanner imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.genesis_scanner")
    assert mod is not None
