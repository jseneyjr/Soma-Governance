"""1:1 mirrored contract test for soma_sdk.scoring."""
from __future__ import annotations
import importlib
import pytest


def test_scoring_module_contract():
    """Verify soma_sdk.scoring imports cleanly and is non-null."""
    mod = importlib.import_module("soma_sdk.scoring")
    assert mod is not None
