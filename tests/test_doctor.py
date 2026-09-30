"""Tests for soma doctor health checks."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from soma_cli.doctor import (
    _check_python_version,
    _check_pyyaml,
    run_doctor,
)


# ── Individual check tests ──────────────────────────────────────────────────


def test_doctor_python_version_passes():
    """On any 3.9+ interpreter this must pass."""
    assert sys.version_info >= (3, 9), "Test suite requires Python ≥ 3.9"
    assert _check_python_version() is True


def test_doctor_pyyaml_check():
    """pyyaml should be importable in the test environment."""
    assert _check_pyyaml() is True


# ── Integration: full run_doctor ─────────────────────────────────────────────


def test_doctor_returns_zero_in_valid_env(tmp_path, monkeypatch):
    """run_doctor returns 0 when every check is mocked to pass."""
    # Set up a fake project with a recognized platform and evidence dir
    (tmp_path / ".gemini").mkdir()
    evidence = tmp_path / ".soma" / "evidence"
    evidence.mkdir(parents=True)

    # Fake rules directory with at least one .md file
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "example.md").write_text("# rule")

    monkeypatch.chdir(tmp_path)

    # Mock get_rules_dir to return our fake rules dir
    with patch("soma_cli.doctor.shutil.which", return_value="/usr/local/bin/soma"):
        from soma_cli.init import get_rules_dir as _orig  # noqa: F811
        with patch(
            "soma_cli.init.get_rules_dir",
            return_value=rules_dir,
        ):
            args = argparse.Namespace()
            result = run_doctor(args)

    assert result == 0


def test_doctor_returns_one_on_failure(tmp_path, monkeypatch):
    """Monkeypatch sys.version_info to (3, 8) and verify exit code 1."""
    # Even with a valid environment, a failing Python version check → exit 1
    (tmp_path / ".gemini").mkdir()
    evidence = tmp_path / ".soma" / "evidence"
    evidence.mkdir(parents=True)

    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "example.md").write_text("# rule")

    monkeypatch.chdir(tmp_path)

    from collections import namedtuple
    _VersionInfo = namedtuple("version_info", "major minor micro releaselevel serial")
    fake_version = _VersionInfo(3, 8, 0, "final", 0)

    monkeypatch.setattr("soma_cli.doctor.sys.version_info", fake_version)
    with patch("soma_cli.doctor.shutil.which", return_value="/usr/local/bin/soma"), \
         patch("soma_cli.init.get_rules_dir", return_value=rules_dir):
        args = argparse.Namespace()
        result = run_doctor(args)

    assert result == 1
