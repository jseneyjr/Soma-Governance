"""1:1 mirrored contract test for immune_system.verification.mutation_tester."""
from __future__ import annotations
import importlib
import pytest


def test_mutation_tester_module_contract():
    """Verify immune_system.verification.mutation_tester imports cleanly and is non-null."""
    mod = importlib.import_module("immune_system.verification.mutation_tester")
    assert mod is not None
