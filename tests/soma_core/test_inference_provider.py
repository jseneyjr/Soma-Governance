"""1:1 mirrored contract test for soma_core.inference_provider."""
from __future__ import annotations
import importlib
import pytest


def test_inference_provider_module_contract():
    """Verify soma_core.inference_provider imports cleanly and is non-null."""
    mod = importlib.import_module("soma_core.inference_provider")
    assert mod is not None
