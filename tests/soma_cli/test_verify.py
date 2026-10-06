"""1:1 mirrored contract test for soma_cli.verify."""
from __future__ import annotations
import importlib
import pytest


def test_verify_module_contract():
    """Verify soma_cli.verify imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.verify")
    assert mod is not None
