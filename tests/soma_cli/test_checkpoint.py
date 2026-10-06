"""1:1 mirrored contract test for soma_cli.checkpoint."""
from __future__ import annotations
import importlib
import pytest


def test_checkpoint_module_contract():
    """Verify soma_cli.checkpoint imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.checkpoint")
    assert mod is not None
