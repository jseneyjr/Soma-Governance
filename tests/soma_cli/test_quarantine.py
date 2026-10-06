"""1:1 mirrored contract test for soma_cli.quarantine."""
from __future__ import annotations
import importlib
import pytest


def test_quarantine_module_contract():
    """Verify soma_cli.quarantine imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.quarantine")
    assert mod is not None
