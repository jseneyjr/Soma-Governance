"""1:1 mirrored contract test for soma_cli.platforms.kiro."""
from __future__ import annotations
import importlib
import pytest


def test_kiro_module_contract():
    """Verify soma_cli.platforms.kiro imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.platforms.kiro")
    assert mod is not None
