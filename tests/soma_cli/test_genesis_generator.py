"""1:1 mirrored contract test for soma_cli.genesis_generator."""
from __future__ import annotations
import importlib
import pytest


def test_genesis_generator_module_contract():
    """Verify soma_cli.genesis_generator imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.genesis_generator")
    assert mod is not None
