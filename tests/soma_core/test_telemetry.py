"""1:1 mirrored contract test for soma_core.telemetry."""
from __future__ import annotations
import importlib
import pytest


def test_telemetry_module_contract():
    """Verify soma_core.telemetry imports cleanly and is non-null."""
    mod = importlib.import_module("soma_core.telemetry")
    assert mod is not None
