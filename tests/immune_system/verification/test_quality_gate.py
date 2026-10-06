"""1:1 mirrored contract test for immune_system.verification.quality_gate."""
from __future__ import annotations
import importlib
import pytest


def test_quality_gate_module_contract():
    """Verify immune_system.verification.quality_gate imports cleanly and is non-null."""
    mod = importlib.import_module("immune_system.verification.quality_gate")
    assert mod is not None
