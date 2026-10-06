"""1:1 mirrored contract test for soma_core.evidence_collector."""
from __future__ import annotations
import importlib
import pytest


def test_evidence_collector_module_contract():
    """Verify soma_core.evidence_collector imports cleanly and is non-null."""
    mod = importlib.import_module("soma_core.evidence_collector")
    assert mod is not None
