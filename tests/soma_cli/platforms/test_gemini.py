"""1:1 mirrored contract test for soma_cli.platforms.gemini."""
from __future__ import annotations
import importlib
import pytest


def test_gemini_module_contract():
    """Verify soma_cli.platforms.gemini imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.platforms.gemini")
    assert mod is not None
