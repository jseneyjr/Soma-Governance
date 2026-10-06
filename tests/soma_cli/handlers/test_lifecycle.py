"""1:1 mirrored contract test for soma_cli.handlers.lifecycle."""
from __future__ import annotations
import importlib
import pytest


def test_lifecycle_module_contract():
    """Verify soma_cli.handlers.lifecycle imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.handlers.lifecycle")
    assert mod is not None
