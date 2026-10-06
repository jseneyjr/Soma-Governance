"""1:1 mirrored contract test for soma_cli.report."""
from __future__ import annotations
import importlib
import pytest


def test_report_module_contract():
    """Verify soma_cli.report imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.report")
    assert mod is not None
