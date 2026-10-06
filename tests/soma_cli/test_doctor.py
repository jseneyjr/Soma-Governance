"""1:1 mirrored contract test for soma_cli.doctor."""
from __future__ import annotations
import importlib
import pytest


def test_doctor_module_contract():
    """Verify soma_cli.doctor imports cleanly and is non-null."""
    mod = importlib.import_module("soma_cli.doctor")
    assert mod is not None
