"""Tests for centralized test runner discovery in soma_core/verification/test_runner.py."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from soma_core.errors import NoTestRunnerFoundError
from soma_core.verification.test_runner import resolve_pytest_cmd
from soma_core.workspace import Workspace


class TestPytestResolution:
    """Test resolution of pytest runner across environments."""

    def test_prefers_active_virtual_env(self, tmp_path: Path):
        fake_venv = tmp_path / "active_venv"
        fake_bin = fake_venv / ("Scripts" if os.name == "nt" else "bin")
        fake_bin.mkdir(parents=True)
        fake_pytest = fake_bin / ("pytest.exe" if os.name == "nt" else "pytest")
        fake_pytest.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        if os.name != "nt":
            fake_pytest.chmod(0o755)

        with patch.dict(os.environ, {"VIRTUAL_ENV": str(fake_venv)}):
            cmd = resolve_pytest_cmd()
            assert cmd == [str(fake_pytest)]

    def test_falls_back_to_local_workspace_venv(self, tmp_path: Path):
        ws_dir = tmp_path / "my_project"
        ws_dir.mkdir()
        fake_local_venv = ws_dir / ".venv"
        fake_bin = fake_local_venv / ("Scripts" if os.name == "nt" else "bin")
        fake_bin.mkdir(parents=True)
        fake_pytest = fake_bin / ("pytest.exe" if os.name == "nt" else "pytest")
        fake_pytest.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        if os.name != "nt":
            fake_pytest.chmod(0o755)

        with patch.dict(os.environ, {"VIRTUAL_ENV": ""}):
            cmd = resolve_pytest_cmd(workspace=ws_dir)
            assert cmd == [str(fake_pytest)]

            # Also works with Workspace value object
            ws = Workspace(ws_dir)
            cmd_ws = resolve_pytest_cmd(workspace=ws)
            assert cmd_ws == [str(fake_pytest)]

    def test_falls_back_to_system_which(self, tmp_path: Path):
        with patch.dict(os.environ, {"VIRTUAL_ENV": ""}):
            with patch("soma_core.verification.test_runner.shutil.which", return_value="/usr/local/bin/pytest"):
                cmd = resolve_pytest_cmd(workspace=tmp_path)
                assert cmd == ["/usr/local/bin/pytest"]

    def test_falls_back_to_sys_executable(self, tmp_path: Path):
        with patch.dict(os.environ, {"VIRTUAL_ENV": ""}):
            with patch("soma_core.verification.test_runner.shutil.which", return_value=None):
                with patch("importlib.util.find_spec", return_value=object()):
                    cmd = resolve_pytest_cmd(workspace=tmp_path)
                    assert cmd == [sys.executable, "-m", "pytest"]

    def test_returns_empty_when_no_runner_and_not_required(self, tmp_path: Path):
        with patch.dict(os.environ, {"VIRTUAL_ENV": ""}):
            with patch("soma_core.verification.test_runner.shutil.which", return_value=None):
                with patch("importlib.util.find_spec", return_value=None):
                    cmd = resolve_pytest_cmd(workspace=tmp_path, required=False)
                    assert cmd == []

    def test_raises_when_no_runner_and_required(self, tmp_path: Path):
        with patch.dict(os.environ, {"VIRTUAL_ENV": ""}):
            with patch("soma_core.verification.test_runner.shutil.which", return_value=None):
                with patch("importlib.util.find_spec", return_value=None):
                    with pytest.raises(NoTestRunnerFoundError) as exc:
                        resolve_pytest_cmd(workspace=tmp_path, required=True)
                    assert "No pytest runner found" in str(exc.value)
