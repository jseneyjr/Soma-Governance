"""1:1 mirrored contract test for soma_cli.status."""
from __future__ import annotations
import importlib
import pytest


def test_status_module_contract():
    """Verify soma_cli.status imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.status")
    assert mod is not None
