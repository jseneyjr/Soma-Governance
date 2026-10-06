"""1:1 mirrored contract test for soma_cli.cli."""
from __future__ import annotations
import importlib
import pytest


def test_cli_module_contract():
    """Verify soma_cli.cli imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.cli")
    assert mod is not None
