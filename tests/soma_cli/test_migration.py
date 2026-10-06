"""1:1 mirrored contract test for soma_cli.migration."""
from __future__ import annotations
import importlib
import pytest


def test_migration_module_contract():
    """Verify soma_cli.migration imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.migration")
    assert mod is not None
