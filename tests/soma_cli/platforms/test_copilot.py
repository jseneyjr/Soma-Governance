"""1:1 mirrored contract test for soma_cli.platforms.copilot."""
from __future__ import annotations
import importlib
import pytest


def test_copilot_module_contract():
    """Verify soma_cli.platforms.copilot imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.platforms.copilot")
    assert mod is not None
