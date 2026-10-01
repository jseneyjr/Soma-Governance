"""TDD Gate 1 tests for `soma demote` CLI command.

Wires lifecycle engine's evaluate_demotions into a CLI subcommand.
"""
import argparse
import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from tests.helpers_cell import make_cell, write_evidence


class TestDemoteCLI:
    """Tests for soma demote subcommand."""

    def test_run_demote_importable(self):
        from soma_cli.demote import run_demote
        assert callable(run_demote)

    def test_demote_registered_in_cli(self):
        from soma_cli.cli import _build_parser
        parser = _build_parser()
        args = parser.parse_args(["demote", "--dry-run"])
        assert args.command == "demote"
        assert args.dry_run is True

    def test_demote_dry_run_shows_candidates(self, tmp_path, capsys):
        """--dry-run lists demotion candidates."""
        from soma_cli.demote import run_demote

        cells_dir = tmp_path / ".soma" / "cells" / "walls"
        cells_dir.mkdir(parents=True)
        evidence_dir = tmp_path / ".soma" / "evidence"
        evidence_dir.mkdir(parents=True)

        make_cell(str(cells_dir), "bad-wall", cell_type="wall", created_days_ago=60)
        write_evidence(str(evidence_dir), "bad-wall", triggers=20, tp=6, fp=14)

        args = argparse.Namespace(dry_run=True, json=False, _project_root=tmp_path)
        exit_code = run_demote(args)

        assert exit_code == 0
        output = capsys.readouterr().out
        assert "bad-wall" in output

    def test_demote_no_candidates_exits_zero(self, tmp_path):
        """No demotion candidates → exit 0."""
        from soma_cli.demote import run_demote

        (tmp_path / ".soma" / "cells").mkdir(parents=True)
        (tmp_path / ".soma" / "evidence").mkdir(parents=True)

        args = argparse.Namespace(dry_run=True, json=False, _project_root=tmp_path)
        exit_code = run_demote(args)
        assert exit_code == 0

    def test_demote_json_output(self, tmp_path, capsys):
        """--json returns structured output."""
        from soma_cli.demote import run_demote

        cells_dir = tmp_path / ".soma" / "cells" / "walls"
        cells_dir.mkdir(parents=True)
        evidence_dir = tmp_path / ".soma" / "evidence"
        evidence_dir.mkdir(parents=True)

        make_cell(str(cells_dir), "noisy-wall", cell_type="wall", created_days_ago=60)
        write_evidence(str(evidence_dir), "noisy-wall", triggers=20, tp=5, fp=15)

        args = argparse.Namespace(dry_run=True, json=True, _project_root=tmp_path)
        run_demote(args)

        output = capsys.readouterr().out
        data = json.loads(output)
        assert "candidates" in data
        assert len(data["candidates"]) == 1
