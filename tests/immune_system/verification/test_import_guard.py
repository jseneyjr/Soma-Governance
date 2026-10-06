"""1:1 mirrored contract test for immune_system.verification.import_guard."""
from __future__ import annotations
import importlib
import pytest


def test_import_guard_module_contract():
    """Verify immune_system.verification.import_guard imports cleanly and is non-null."""
    mod = importlib.import_module("immune_system.verification.import_guard")
    assert mod is not None
