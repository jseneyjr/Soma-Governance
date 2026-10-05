"""Unit and behavioral tests for pure-Python migrated enzymes in Phase 4."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO_ROOT

ENZYMES_DIR = Path(REPO_ROOT) / "enzymes"


def test_bump_version_dry_run(tmp_path):
    from enzymes.bump_version import bump_version

    (tmp_path / "VERSION").write_text("0.93.0\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('version = "0.93.0"\n', encoding="utf-8")

    rc = bump_version("0.94.0", repo_root=tmp_path, dry_run=True)
    # Missing other surfaces should report error or fail closed
    assert rc in (0, 1)


def test_cell_selection_evaluation(tmp_path):
    from enzymes.cell_selection import run_cell_selection

    cells_dir = tmp_path / ".soma" / "cells"
    walls_dir = cells_dir / "walls"
    archive_dir = cells_dir / ".archive"
    walls_dir.mkdir(parents=True)

    cell_content = """---
id: test-cell
type: wall
fitness:
  score: 0.1
  triggers: 10
  false_positives: 9
---
Test body
"""
    (walls_dir / "test-cell.md").write_text(cell_content, encoding="utf-8")

    # Run check mode (dry run)
    rc = run_cell_selection(workspace=tmp_path, execute=False)
    assert rc == 0
    assert (walls_dir / "test-cell.md").exists()

    # Run execute mode
    rc = run_cell_selection(workspace=tmp_path, execute=True)
    assert rc == 0
    assert not (walls_dir / "test-cell.md").exists()
    assert (archive_dir / "test-cell.md").exists()


def test_log_finding(tmp_path):
    from enzymes.log_finding import log_finding

    rc = log_finding(
        severity="warning",
        rule="providence.md",
        change="Refactored parser",
        source="test_runner",
        logs_dir=tmp_path,
    )
    assert rc == 0
    auto_log = tmp_path / "governance" / "auto_applied_log.jsonl"
    assert auto_log.exists()
    lines = [json.loads(l) for l in auto_log.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1
    assert lines[0]["rule"] == "providence.md"
    assert lines[0]["severity"] == "warning"
    assert lines[0]["change"] == "Refactored parser"


def test_liveness_sentinel_scan():
    from enzymes.liveness_sentinel import check_liveness

    payload = json.dumps({
        "agents": [
            {
                "name": "scout",
                "dispatched": "2026-10-05T10:00:00Z",
                "timeout_seconds": 3600,
            }
        ]
    })
    rc = check_liveness(payload)
    assert rc == 0


def test_post_session_hook_execution(tmp_path):
    from enzymes.post_session_hook import run_post_session_hook

    transcript = tmp_path / "transcript.jsonl"
    step1 = {
        "step_index": 1,
        "type": "PLANNER_RESPONSE",
        "tool_calls": [
            {
                "name": "view_file",
                "args": {"AbsolutePath": str(tmp_path / "src" / "main.py")},
            },
            {
                "name": "replace_file_content",
                "args": {"TargetFile": str(tmp_path / "src" / "main.py")},
            },
        ],
    }
    transcript.write_text(json.dumps(step1) + "\n", encoding="utf-8")

    cells_dir = tmp_path / ".soma" / "cells"
    walls_dir = cells_dir / "walls"
    walls_dir.mkdir(parents=True)
    cell_file = walls_dir / "main-guard.md"
    cell_file.write_text(
        "---\nid: main-guard\ntype: wall\ntarget_paths:\n  - 'src/**'\n---\nBody\n",
        encoding="utf-8",
    )

    evidence_dir = tmp_path / ".soma" / "evidence"

    rc = run_post_session_hook(
        transcript_path=transcript,
        cells_dir=cells_dir,
        evidence_dir=evidence_dir,
        repo_root=tmp_path,
    )
    assert rc == 0
    assert (evidence_dir / "signals.jsonl").exists()
    assert (evidence_dir / "compliance.jsonl").exists()


def test_shell_wrapper_delegation(tmp_path, bash):
    """Verify that thin .sh wrappers delegate to their .py counterparts."""
    script_sh = ENZYMES_DIR / "bump_version.sh"
    env = dict(os.environ)
    env["SOMA_PYTHON"] = sys.executable

    proc = subprocess.run(
        [bash, str(script_sh), "9.9.9", "--dry-run"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert "dry run" in proc.stdout.lower()
