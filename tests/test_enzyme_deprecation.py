"""Tests verifying deprecation or removal of legacy enzymes package."""
import importlib
import os
import pytest
from conftest import REPO_ROOT


def test_enzymes_package_deprecation_or_removal():
    """Importing enzymes must emit DeprecationWarning in bridge phase or raise ModuleNotFoundError when removed."""
    enzymes_dir = os.path.join(REPO_ROOT, "enzymes")
    if not os.path.exists(enzymes_dir):
        with pytest.raises(ModuleNotFoundError):
            import enzymes
    else:
        with pytest.deprecated_call(match="The 'enzymes' package and shims are deprecated"):
            import enzymes
            importlib.reload(enzymes)
