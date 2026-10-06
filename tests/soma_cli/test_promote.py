"""1:1 mirrored contract test for soma_cli.promote."""
from __future__ import annotations
import importlib
import pytest


def test_promote_module_contract():
    """Verify soma_cli.promote imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.promote")
    assert mod is not None
