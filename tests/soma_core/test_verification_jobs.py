"""1:1 mirrored contract test for soma_core.verification_jobs."""
from __future__ import annotations
import importlib
import pytest


def test_verification_jobs_module_contract():
    """Verify soma_core.verification_jobs imports cleanly and is non-null."""
    mod = importlib.import_module("soma_core.verification_jobs")
    assert mod is not None
