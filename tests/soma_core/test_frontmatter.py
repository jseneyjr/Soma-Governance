"""1:1 mirrored contract test for soma_core.frontmatter."""
from __future__ import annotations
import importlib
import pytest


def test_frontmatter_module_contract():
    """Verify soma_core.frontmatter imports cleanly and is non-null."""
    mod = importlib.import_module("soma_core.frontmatter")
    assert mod is not None
