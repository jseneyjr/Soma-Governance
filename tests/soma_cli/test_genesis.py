"""1:1 mirrored contract test for soma_cli.genesis."""
from __future__ import annotations
import importlib
import pytest


def test_genesis_module_contract():
    """Verify soma_cli.genesis imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.genesis")
    assert mod is not None
