"""1:1 mirrored contract test for soma_cli.completion."""
from __future__ import annotations
import importlib
import pytest


def test_completion_module_contract():
    """Verify soma_cli.completion imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.completion")
    assert mod is not None
