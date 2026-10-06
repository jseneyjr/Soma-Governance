"""1:1 mirrored contract test for soma_sdk.analysis."""
from __future__ import annotations
import importlib
import pytest


def test_analysis_module_contract():
    """Verify soma_sdk.analysis imports cleanly and is non-null."""
    mod = importlib.import_module("soma_sdk.analysis")
    assert mod is not None
