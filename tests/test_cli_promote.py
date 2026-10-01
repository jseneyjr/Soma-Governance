"""TDD Gate 1 tests for `soma promote` CLI command.

Wires lifecycle engine's evaluate_promotions into a CLI subcommand.
"""
import argparse
import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from tests.helpers_cell import make_cell, write_evidence


class TestPromoteCLI:
    """Tests for soma promote subcommand."""

    def test_run_promote_importable(self):
        from soma_cli.promote import run_promote
        assert callable(run_promote)

    def test_promote_registered_in_cli(self):
        from soma_cli.cli import _build_parser
        parser = _build_parser()
        args = parser.parse_args(["promote", "--dry-run"])
        assert args.command == "promote"
        assert args.dry_run is True

    def test_promote_dry_run_shows_candidates(self, tmp_path, capsys):
        """--dry-run lists candidates without performing mutations."""
        from soma_cli.promote import run_promote

        cells_dir = tmp_path / ".soma" / "cells" / "vacuoles"
        cells_dir.mkdir(parents=True)
        evidence_dir = tmp_path / ".soma" / "evidence"
        evidence_dir.mkdir(parents=True)

        make_cell(str(cells_dir), "ready-cell", created_days_ago=45)
        write_evidence(str(evidence_dir), "ready-cell", triggers=25, tp=23, fp=2)

        args = argparse.Namespace(dry_run=True, json=False, _project_root=tmp_path)
        exit_code = run_promote(args)

        assert exit_code == 0
        output = capsys.readouterr().out
        assert "ready-cell" in output

    def test_promote_no_candidates_exits_zero(self, tmp_path):
        """No promotion candidates → exit 0."""
        from soma_cli.promote import run_promote

        (tmp_path / ".soma" / "cells").mkdir(parents=True)
        (tmp_path / ".soma" / "evidence").mkdir(parents=True)

        args = argparse.Namespace(dry_run=True, json=False, _project_root=tmp_path)
        exit_code = run_promote(args)
        assert exit_code == 0

    def test_promote_json_output(self, tmp_path, capsys):
        """--json returns structured output."""
        from soma_cli.promote import run_promote

        cells_dir = tmp_path / ".soma" / "cells" / "vacuoles"
        cells_dir.mkdir(parents=True)
        evidence_dir = tmp_path / ".soma" / "evidence"
        evidence_dir.mkdir(parents=True)

        make_cell(str(cells_dir), "promo-cell", created_days_ago=45)
        write_evidence(str(evidence_dir), "promo-cell", triggers=25, tp=23, fp=2)

        args = argparse.Namespace(dry_run=True, json=True, _project_root=tmp_path)
        run_promote(args)

        output = capsys.readouterr().out
        data = json.loads(output)
        assert "candidates" in data
        assert len(data["candidates"]) == 1
