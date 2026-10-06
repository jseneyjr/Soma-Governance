"""1:1 mirrored contract test for soma_cli.oracle."""
from __future__ import annotations
import importlib
import pytest


def test_oracle_module_contract():
    """Verify soma_cli.oracle imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.oracle")
    assert mod is not None
