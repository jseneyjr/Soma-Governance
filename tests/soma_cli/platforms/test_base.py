"""1:1 mirrored contract test for soma_cli.platforms.base."""
from __future__ import annotations
import importlib
import pytest


def test_base_module_contract():
    """Verify soma_cli.platforms.base imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.platforms.base")
    assert mod is not None
