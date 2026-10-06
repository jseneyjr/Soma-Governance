"""1:1 mirrored contract test for soma_cli.platforms.claude."""
from __future__ import annotations
import importlib
import pytest


def test_claude_module_contract():
    """Verify soma_cli.platforms.claude imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.platforms.claude")
    assert mod is not None
