"""Tests verifying deprecation warnings on legacy enzymes shims for v0.96.2."""
import importlib
import warnings
import pytest


def test_enzymes_package_emits_deprecation_warning():
    """Importing enzymes package must raise a DeprecationWarning."""
    with pytest.deprecated_call(match="The 'enzymes' package and shims are deprecated"):
        import enzymes
        importlib.reload(enzymes)
