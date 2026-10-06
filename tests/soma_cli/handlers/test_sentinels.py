"""1:1 mirrored contract test for soma_cli.handlers.sentinels."""
from __future__ import annotations
import importlib
import pytest


def test_sentinels_module_contract():
    """Verify soma_cli.handlers.sentinels imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.handlers.sentinels")
    assert mod is not None
