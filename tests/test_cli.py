"""Tests for soma_cli — Phase A test gate.

Verifies the CLI skeleton installs correctly and all subcommands
have help text and exit cleanly.
"""
import os
import subprocess
import sys

import pytest


SUBCOMMANDS = ["init", "status", "report", "doctor"]


class TestCLIImport:
    """Verify the CLI module is importable without side effects."""

    def test_cli_importable(self):
        from soma_cli.cli import main
        assert callable(main)

    def test_cli_build_parser(self):
        from soma_cli.cli import _build_parser
        parser = _build_parser()
        assert parser.prog == "soma"


class TestCLIHelp:
    """Verify --help works for the main command and all subcommands."""

    def test_main_help_exits_zero(self):
        from soma_cli.cli import main
        # No args → prints help, returns 0
        assert main([]) == 0

    @pytest.mark.parametrize("cmd", SUBCOMMANDS)
    def test_subcommand_help_exits_zero(self, cmd):
        from soma_cli.cli import main
        with pytest.raises(SystemExit) as exc_info:
            main([cmd, "--help"])
        assert exc_info.value.code == 0


class TestCLIDispatch:
    """Verify subcommands dispatch to their handlers."""

    @pytest.mark.parametrize("cmd,extra_args", [
        ("init", ["--dry-run", "--platform", "gemini", "--yes"]),
        ("status", []),
        ("report", []),
        ("doctor", []),
    ])
    def test_subcommand_runs_without_crash(self, cmd, extra_args, capsys):
        from soma_cli.cli import main
        result = main([cmd] + extra_args)
        assert result in (0, 1)
        captured = capsys.readouterr()
        assert 'Traceback' not in captured.err

    def test_unknown_command_returns_nonzero(self):
        from soma_cli.cli import main
        # argparse treats unknown subcommand as args.command = None? No,
        # it raises SystemExit(2) for unrecognized args.
        with pytest.raises(SystemExit) as exc_info:
            main(["nonexistent_command_xyz"])
        assert exc_info.value.code == 2


class TestCLIEntryPoint:
    """Verify the installed entry point resolves correctly."""

    def test_soma_dash_dash_help_via_subprocess(self):
        """Run `python -m soma_cli.cli --help` to test without requiring
        pip install."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        proc = subprocess.run(
            [sys.executable, "-m", "soma_cli.cli", "--help"],
            capture_output=True, text=True, timeout=10,
            cwd=repo_root,
        )
        assert proc.returncode == 0
        assert "Soma Governance" in proc.stdout
