"""1:1 mirrored contract test for soma_cli.transfer."""
from __future__ import annotations
import importlib
import pytest


def test_transfer_module_contract():
    """Verify soma_cli.transfer imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.transfer")
    assert mod is not None
