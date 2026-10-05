"""Unit tests for soma_core.enforcement."""
import os
import tempfile
import pytest

from soma_core.enforcement import (
    load_bug_registry,
    bug_status,
    verify_bug_schema,
    verify_unique_ids,
    generate_ci_report,
    _match_cells,
    _compute_credit_weights,
    _format_markdown,
)


def test_enforcement_ci_report_generation(tmp_path):
    cells_dir = tmp_path / ".soma" / "cells"
    cells_dir.mkdir(parents=True)
    cell_path = cells_dir / "membrane-test.md"
    cell_path.write_text(
        "---\nname: membrane-test\ntype: membrane\ntarget_paths:\n  - 'src/*'\n---\n# Membrane\n",
        encoding="utf-8",
    )

    report = generate_ci_report(
        workspace=str(tmp_path),
        changed_files=["src/test.py"],
        test_passed=True,
        commit_sha="c0ffee",
    )
    assert len(report["matched_cells"]) == 1
    assert report["matched_cells"][0]["cell"] == "membrane-test"
    assert report["matched_cells"][0]["credit_weight"] == 1.0
    assert report["matched_cells"][0]["proposed_signal"] == "trigger"
    assert "c0ffee" in report["summary"]


def test_enforcement_credit_weights_conservation():
    matched = [
        {"cell": "cell-a", "path": "/fake/a.md"},
        {"cell": "cell-b", "path": "/fake/b.md"},
    ]
    # No files or cells -> default weight 1.0
    weights = _compute_credit_weights(matched, [])
    assert weights["cell-a"] == 1.0
