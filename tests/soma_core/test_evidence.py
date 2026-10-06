"""1:1 mirrored contract test for soma_core.evidence."""
from __future__ import annotations
import importlib
import pytest


def test_evidence_module_contract():
    """Verify soma_core.evidence imports cleanly and is non-null."""
    mod = importlib.import_module("soma_core.evidence")
    assert mod is not None
