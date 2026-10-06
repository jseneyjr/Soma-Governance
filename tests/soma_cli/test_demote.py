"""1:1 mirrored contract test for soma_cli.demote."""
from __future__ import annotations
import importlib
import pytest


def test_demote_module_contract():
    """Verify soma_cli.demote imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.demote")
    assert mod is not None
