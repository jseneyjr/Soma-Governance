"""1:1 mirrored contract test for soma_cli.handlers.sync."""
from __future__ import annotations
import importlib
import pytest


def test_sync_module_contract():
    """Verify soma_cli.handlers.sync imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.handlers.sync")
    assert mod is not None
