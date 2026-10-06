"""1:1 mirrored contract test for soma_cli.hooks."""
from __future__ import annotations
import importlib
import pytest


def test_hooks_module_contract():
    """Verify soma_cli.hooks imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.hooks")
    assert mod is not None
