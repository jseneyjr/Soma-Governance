"""1:1 mirrored contract test for soma_cli.pathcheck."""
from __future__ import annotations
import importlib
import pytest


def test_pathcheck_module_contract():
    """Verify soma_cli.pathcheck imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.pathcheck")
    assert mod is not None
