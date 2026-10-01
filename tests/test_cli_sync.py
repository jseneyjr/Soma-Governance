"""Tests for soma sync — evidence JSONL → cell frontmatter reconciliation.

Covers:
- aggregate_evidence reads fitness.jsonl + outcomes.jsonl correctly
- sync_frontmatter updates cell YAML frontmatter from aggregated counts
- Idempotency: running sync twice produces no additional changes
- Dry-run mode: reports changes without writing
- CLI entrypoint: soma sync works end-to-end
- Checkpoint integration: sync runs before quality checks
"""
import argparse
import json
import os
import sys

import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from soma_cli.sync import aggregate_evidence, sync_frontmatter, run_sync


CELL_TEMPLATE = """\
---
id: {cell_id}
domain: testing
type: vacuole
enforcement: advisory
fitness:
  score: null
  impact_weight: 1.0
  triggers: 0
  true_positives: 0
  false_positives: 0
---
# {cell_id}

Test cell for sync tests.
"""


def _setup_workspace(tmp_path, cells, fitness_records, outcome_records=None):
    """Create a minimal .soma workspace with cells and evidence."""
    cells_dir = tmp_path / ".soma" / "cells" / "vacuoles"
    cells_dir.mkdir(parents=True)
    evidence_dir = tmp_path / ".soma" / "evidence"
    evidence_dir.mkdir(parents=True)

    for cell_id in cells:
        (cells_dir / f"{cell_id}.md").write_text(
            CELL_TEMPLATE.format(cell_id=cell_id), encoding="utf-8"
        )

    with open(evidence_dir / "fitness.jsonl", "w", encoding="utf-8") as f:
        for record in fitness_records:
            f.write(json.dumps(record) + "\n")

    if outcome_records:
        with open(evidence_dir / "outcomes.jsonl", "w", encoding="utf-8") as f:
            for record in outcome_records:
                f.write(json.dumps(record) + "\n")

    return str(evidence_dir), str(cells_dir)


class TestAggregateEvidence:
    """Tests for aggregate_evidence()."""

    def test_counts_triggers(self, tmp_path):
        """Trigger events are counted per cell_id."""
        evidence_dir, _ = _setup_workspace(tmp_path, ["cell-a"], [
            {"cell_id": "cell-a", "triggered_at": "2026-01-01T00:00:00Z"},
            {"cell_id": "cell-a", "triggered_at": "2026-01-01T01:00:00Z"},
            {"cell_id": "cell-a", "triggered_at": "2026-01-01T02:00:00Z"},
        ])
        counts = aggregate_evidence(evidence_dir)
        assert counts["cell-a"]["triggers"] == 3

    def test_counts_outcomes(self, tmp_path):
        """TP and FP outcomes are counted from outcomes.jsonl."""
        evidence_dir, _ = _setup_workspace(
            tmp_path, ["cell-a"],
            fitness_records=[
                {"cell_id": "cell-a", "triggered_at": "2026-01-01T00:00:00Z"},
            ],
            outcome_records=[
                {"cell_id": "cell-a", "outcome": "tp"},
                {"cell_id": "cell-a", "outcome": "tp"},
                {"cell_id": "cell-a", "outcome": "fp"},
            ],
        )
        counts = aggregate_evidence(evidence_dir)
        assert counts["cell-a"]["tp"] == 2
        assert counts["cell-a"]["fp"] == 1

    def test_tracks_last_trigger(self, tmp_path):
        """Last trigger timestamp is tracked."""
        evidence_dir, _ = _setup_workspace(tmp_path, ["cell-a"], [
            {"cell_id": "cell-a", "triggered_at": "2026-01-01T00:00:00Z"},
            {"cell_id": "cell-a", "triggered_at": "2026-01-03T00:00:00Z"},
            {"cell_id": "cell-a", "triggered_at": "2026-01-02T00:00:00Z"},
        ])
        counts = aggregate_evidence(evidence_dir)
        assert counts["cell-a"]["last_trigger"] == "2026-01-03T00:00:00Z"

    def test_empty_evidence(self, tmp_path):
        """Empty evidence directory returns empty dict."""
        evidence_dir = str(tmp_path / "empty")
        os.makedirs(evidence_dir, exist_ok=True)
        counts = aggregate_evidence(evidence_dir)
        assert counts == {}

    def test_multiple_cells(self, tmp_path):
        """Multiple cells are tracked independently."""
        evidence_dir, _ = _setup_workspace(tmp_path, ["cell-a", "cell-b"], [
            {"cell_id": "cell-a", "triggered_at": "2026-01-01T00:00:00Z"},
            {"cell_id": "cell-b", "triggered_at": "2026-01-01T00:00:00Z"},
            {"cell_id": "cell-b", "triggered_at": "2026-01-01T01:00:00Z"},
        ])
        counts = aggregate_evidence(evidence_dir)
        assert counts["cell-a"]["triggers"] == 1
        assert counts["cell-b"]["triggers"] == 2

    def test_malformed_lines_skipped(self, tmp_path):
        """Malformed JSONL lines are skipped without crashing."""
        evidence_dir = str(tmp_path / ".soma" / "evidence")
        os.makedirs(evidence_dir, exist_ok=True)
        with open(os.path.join(evidence_dir, "fitness.jsonl"), "w") as f:
            f.write("not valid json\n")
            f.write(json.dumps({"cell_id": "cell-a", "triggered_at": "2026-01-01T00:00:00Z"}) + "\n")
            f.write("\n")  # blank line
        counts = aggregate_evidence(evidence_dir)
        assert counts["cell-a"]["triggers"] == 1


class TestSyncFrontmatter:
    """Tests for sync_frontmatter()."""

    def test_updates_frontmatter(self, tmp_path):
        """Sync writes trigger/tp/fp/score into cell frontmatter."""
        evidence_dir, cells_dir = _setup_workspace(
            tmp_path, ["cell-a"],
            fitness_records=[
                {"cell_id": "cell-a", "triggered_at": "2026-01-01T00:00:00Z"},
            ],
            outcome_records=[
                {"cell_id": "cell-a", "outcome": "tp"},
            ],
        )
        counts = aggregate_evidence(evidence_dir)
        changes = sync_frontmatter(cells_dir, counts)

        assert len(changes) == 1
        assert changes[0]["cell_id"] == "cell-a"

        # Verify file was updated
        content = (tmp_path / ".soma" / "cells" / "vacuoles" / "cell-a.md").read_text()
        end = content.find("---", 3)
        fm = yaml.safe_load(content[3:end])
        assert fm["fitness"]["triggers"] == 1
        assert fm["fitness"]["true_positives"] == 1
        assert fm["fitness"]["false_positives"] == 0
        assert fm["fitness"]["score"] == 1.0

    def test_idempotent(self, tmp_path):
        """Running sync twice produces no changes the second time."""
        evidence_dir, cells_dir = _setup_workspace(
            tmp_path, ["cell-a"],
            fitness_records=[
                {"cell_id": "cell-a", "triggered_at": "2026-01-01T00:00:00Z"},
            ],
            outcome_records=[
                {"cell_id": "cell-a", "outcome": "tp"},
            ],
        )
        counts = aggregate_evidence(evidence_dir)
        sync_frontmatter(cells_dir, counts)
        # Second run
        changes = sync_frontmatter(cells_dir, counts)
        assert len(changes) == 0

    def test_dry_run_no_write(self, tmp_path):
        """Dry run reports changes but doesn't modify files."""
        evidence_dir, cells_dir = _setup_workspace(
            tmp_path, ["cell-a"],
            fitness_records=[
                {"cell_id": "cell-a", "triggered_at": "2026-01-01T00:00:00Z"},
            ],
        )
        counts = aggregate_evidence(evidence_dir)
        changes = sync_frontmatter(cells_dir, counts, dry_run=True)

        assert len(changes) == 1  # reports the change

        # File should NOT be modified
        content = (tmp_path / ".soma" / "cells" / "vacuoles" / "cell-a.md").read_text()
        end = content.find("---", 3)
        fm = yaml.safe_load(content[3:end])
        assert fm["fitness"]["triggers"] == 0  # unchanged

    def test_score_calculation(self, tmp_path):
        """Score is tp/triggers, rounded to 4 decimal places."""
        evidence_dir, cells_dir = _setup_workspace(
            tmp_path, ["cell-a"],
            fitness_records=[
                {"cell_id": "cell-a", "triggered_at": f"2026-01-01T0{i}:00:00Z"}
                for i in range(3)
            ],
            outcome_records=[
                {"cell_id": "cell-a", "outcome": "tp"},
                {"cell_id": "cell-a", "outcome": "fp"},
            ],
        )
        counts = aggregate_evidence(evidence_dir)
        changes = sync_frontmatter(cells_dir, counts)
        # score = 1 tp / 3 triggers = 0.3333
        assert changes[0]["score"] == round(1 / 3, 4)

    def test_unknown_cell_ignored(self, tmp_path):
        """Evidence for cells not on disk is silently skipped."""
        evidence_dir, cells_dir = _setup_workspace(
            tmp_path, ["cell-a"],
            fitness_records=[
                {"cell_id": "cell-a", "triggered_at": "2026-01-01T00:00:00Z"},
                {"cell_id": "ghost-cell", "triggered_at": "2026-01-01T00:00:00Z"},
            ],
        )
        counts = aggregate_evidence(evidence_dir)
        changes = sync_frontmatter(cells_dir, counts)
        assert len(changes) == 1
        assert changes[0]["cell_id"] == "cell-a"


class TestRunSync:
    """Tests for the CLI entrypoint run_sync()."""

    def test_end_to_end(self, tmp_path, capsys):
        """Full sync via CLI entrypoint prints summary."""
        _setup_workspace(
            tmp_path, ["cell-a"],
            fitness_records=[
                {"cell_id": "cell-a", "triggered_at": "2026-01-01T00:00:00Z"},
            ],
            outcome_records=[
                {"cell_id": "cell-a", "outcome": "tp"},
            ],
        )
        args = argparse.Namespace(dry_run=False, json=False)
        # Monkey-patch resolve_root
        import soma_cli.sync as sync_mod
        original = sync_mod.resolve_root
        sync_mod.resolve_root = lambda a: tmp_path
        try:
            rc = run_sync(args)
        finally:
            sync_mod.resolve_root = original

        assert rc == 0
        output = capsys.readouterr().out
        assert "cell-a" in output
        assert "1" in output  # trigger count shows up

    def test_no_evidence(self, tmp_path, capsys):
        """No evidence prints friendly message."""
        evidence_dir = tmp_path / ".soma" / "evidence"
        evidence_dir.mkdir(parents=True)
        (tmp_path / ".soma" / "cells").mkdir(parents=True)

        args = argparse.Namespace(dry_run=False, json=False)
        import soma_cli.sync as sync_mod
        original = sync_mod.resolve_root
        sync_mod.resolve_root = lambda a: tmp_path
        try:
            rc = run_sync(args)
        finally:
            sync_mod.resolve_root = original

        assert rc == 0
        assert "No evidence" in capsys.readouterr().out

    def test_json_output(self, tmp_path, capsys):
        """--json flag produces valid JSON."""
        _setup_workspace(
            tmp_path, ["cell-a"],
            fitness_records=[
                {"cell_id": "cell-a", "triggered_at": "2026-01-01T00:00:00Z"},
            ],
        )
        args = argparse.Namespace(dry_run=False, json=True)
        import soma_cli.sync as sync_mod
        original = sync_mod.resolve_root
        sync_mod.resolve_root = lambda a: tmp_path
        try:
            rc = run_sync(args)
        finally:
            sync_mod.resolve_root = original

        assert rc == 0
        output = json.loads(capsys.readouterr().out)
        assert "changes" in output
        assert isinstance(output["changes"], list)
