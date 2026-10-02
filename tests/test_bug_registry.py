"""Tests for verify_bug_registry enzyme."""
import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from enzymes.verify_bug_registry import (
    load_registry,
    verify_regression_tests,
    verify_schema,
    verify_unique_ids,
)


def _make_registry(tmp_path, bugs, categories=None, severities=None):
    """Create a test BUG_REGISTRY.json."""
    registry = {
        "schema_version": "1.0",
        "root_cause_categories": categories or {
            "path_error": "Wrong path",
            "schema_drift": "Schema mismatch",
        },
        "severity_levels": severities or ["critical", "moderate", "low"],
        "bugs": bugs,
    }
    path = tmp_path / "docs" / "project"
    path.mkdir(parents=True, exist_ok=True)
    with open(path / "BUG_REGISTRY.json", "w") as f:
        json.dump(registry, f)
    return registry


class TestVerifySchema:
    """Schema validation tests."""

    def test_valid_bug_passes(self, tmp_path):
        bugs = [{
            "id": "BUG-001", "title": "Test bug", "discovered_in": "v0.1",
            "fixed_in": "v0.2", "root_cause": "path_error", "severity": "critical",
            "affected_files": ["foo.py"], "regression_test": "tests/test_foo.py::test_bar",
            "changelog_ref": "v0.2",
        }]
        registry = _make_registry(tmp_path, bugs)
        errors = verify_schema(registry)
        assert len(errors) == 0

    def test_missing_field_flagged(self, tmp_path):
        bugs = [{"id": "BUG-001", "title": "Incomplete"}]
        registry = _make_registry(tmp_path, bugs)
        errors = verify_schema(registry)
        assert len(errors) > 0
        assert any("missing required field" in e for e in errors)

    def test_invalid_root_cause_flagged(self, tmp_path):
        bugs = [{
            "id": "BUG-001", "title": "Bad cat", "discovered_in": "v0.1",
            "fixed_in": "v0.2", "root_cause": "nonexistent_category",
            "severity": "critical", "affected_files": ["foo.py"],
            "regression_test": "tests/test_foo.py::test", "changelog_ref": "v0.2",
        }]
        registry = _make_registry(tmp_path, bugs)
        errors = verify_schema(registry)
        assert any("unknown root_cause" in e for e in errors)

    def test_invalid_severity_flagged(self, tmp_path):
        bugs = [{
            "id": "BUG-001", "title": "Bad sev", "discovered_in": "v0.1",
            "fixed_in": "v0.2", "root_cause": "path_error",
            "severity": "supercritical", "affected_files": ["foo.py"],
            "regression_test": "tests/test_foo.py::test", "changelog_ref": "v0.2",
        }]
        registry = _make_registry(tmp_path, bugs)
        errors = verify_schema(registry)
        assert any("unknown severity" in e for e in errors)


def _open_bug(**overrides):
    bug = {
        "id": "BUG-010", "title": "Open bug", "status": "open",
        "discovered_in": "v0.3", "root_cause": "path_error",
        "severity": "moderate", "affected_files": ["foo.py"],
    }
    bug.update(overrides)
    return bug


class TestOpenBugs:
    """Open bugs are tracked before a fix exists, so fix fields are not required."""

    def test_open_bug_without_fix_fields_passes(self, tmp_path):
        registry = _make_registry(tmp_path, [_open_bug()])
        assert verify_schema(registry) == []

    def test_open_bug_still_requires_core_fields(self, tmp_path):
        bug = _open_bug()
        del bug["affected_files"]
        registry = _make_registry(tmp_path, [bug])
        errors = verify_schema(registry)
        assert any("BUG-010: missing required field 'affected_files'" == e for e in errors)

    def test_open_bug_claiming_a_fix_is_flagged(self, tmp_path):
        registry = _make_registry(tmp_path, [_open_bug(fixed_in="v0.4")])
        errors = verify_schema(registry)
        assert any("BUG-010" in e and "open" in e and "fixed_in" in e for e in errors)

    def test_invalid_status_flagged(self, tmp_path):
        registry = _make_registry(tmp_path, [_open_bug(status="wontfix")])
        errors = verify_schema(registry)
        assert any("unknown status 'wontfix'" in e for e in errors)

    def test_explicit_fixed_status_still_requires_fix_fields(self, tmp_path):
        bug = _open_bug(status="fixed")
        registry = _make_registry(tmp_path, [bug])
        errors = verify_schema(registry)
        for field in ("fixed_in", "regression_test", "changelog_ref"):
            assert f"BUG-010: missing required field '{field}'" in errors

    def test_regression_check_skips_open_bugs(self, tmp_path):
        registry = _make_registry(tmp_path, [_open_bug()])
        assert verify_regression_tests(registry, str(tmp_path)) == []

    def test_regression_check_still_applies_to_fixed_bugs(self, tmp_path):
        bug = _open_bug(status="fixed", fixed_in="v0.4", changelog_ref="v0.4",
                        regression_test="tests/test_missing.py::test_x")
        registry = _make_registry(tmp_path, [bug])
        errors = verify_regression_tests(registry, str(tmp_path))
        assert errors == ["BUG-010: regression test file not found: tests/test_missing.py"]


class TestVerifyUniqueIds:
    """ID uniqueness tests."""

    def test_unique_ids_pass(self, tmp_path):
        bugs = [
            {"id": "BUG-001", "title": "A"},
            {"id": "BUG-002", "title": "B"},
        ]
        registry = _make_registry(tmp_path, bugs)
        errors = verify_unique_ids(registry)
        assert len(errors) == 0

    def test_duplicate_ids_flagged(self, tmp_path):
        bugs = [
            {"id": "BUG-001", "title": "A"},
            {"id": "BUG-001", "title": "B"},
        ]
        registry = _make_registry(tmp_path, bugs)
        errors = verify_unique_ids(registry)
        assert len(errors) == 1
        assert "Duplicate" in errors[0]


class TestVerifyRealRegistry:
    """Integration test against the actual bug registry."""

    def test_real_registry_schema_valid(self):
        """The actual BUG_REGISTRY.json passes schema validation."""
        registry = load_registry(REPO_ROOT)
        errors = verify_schema(registry)
        assert len(errors) == 0, f"Schema errors: {errors}"

    def test_real_registry_unique_ids(self):
        """The actual BUG_REGISTRY.json has no duplicate IDs."""
        registry = load_registry(REPO_ROOT)
        errors = verify_unique_ids(registry)
        assert len(errors) == 0, f"ID errors: {errors}"

    def test_real_registry_has_bugs(self):
        """The actual BUG_REGISTRY.json has at least the 5 backfilled bugs."""
        registry = load_registry(REPO_ROOT)
        assert len(registry['bugs']) >= 5
