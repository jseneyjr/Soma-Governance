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

    (tmp_path / "soma_sdk").mkdir()
    (tmp_path / "soma_sdk_js").mkdir()
    (tmp_path / "docs").mkdir()

    (tmp_path / "VERSION").write_text("0.93.0\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('version = "0.93.0"\n', encoding="utf-8")
    (tmp_path / "soma_sdk" / "__init__.py").write_text('__version__ = "0.93.0"\n', encoding="utf-8")
    (tmp_path / "soma_sdk_js" / "package.json").write_text('{\n  "version": "0.93.0"\n}\n', encoding="utf-8")
    (tmp_path / "README.md").write_text('[![Version](https://img.shields.io/badge/Version-0.93.0-informational)\n', encoding="utf-8")
    (tmp_path / "docs" / "KNOWN_ISSUES_WINDOWS.md").write_text(
        "# Known Issues — Windows (v0.93.0)   Open Windows issues as of v0.93.0\n",
        encoding="utf-8",
    )
    (tmp_path / "SECURITY.md").write_text(
        "| 0.93.x | ✅ |\n| < 0.93 | ❌ |\n",
        encoding="utf-8",
    )

    rc = bump_version("0.94.0", repo_root=tmp_path, dry_run=True)
    assert rc == 0


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


def test_match_cells_windows_backslash_paths(tmp_path):
    """Verify that match_cells matches Windows backslash paths against POSIX target_paths."""
    from enzymes.fitness_updater import match_cells

    cells_dir = tmp_path / ".soma" / "cells"
    walls_dir = cells_dir / "walls"
    walls_dir.mkdir(parents=True)
    (walls_dir / "guard.md").write_text(
        "---\nid: guard\ntype: wall\ntarget_paths:\n  - 'src/**'\n---\nBody\n",
        encoding="utf-8",
    )

    # Simulate Windows paths with backslashes
    repo_root = r"C:\Users\runneradmin\project"
    modified_files = {r"C:\Users\runneradmin\project\src\main.py"}

    matched = match_cells(modified_files, cells_dir, repo_root=repo_root)
    assert len(matched) == 1
    assert matched[0]["cell_id"] == "guard"
    assert "src/main.py" in matched[0]["matched_files"]



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


def test_cli_transfer_subcommand(tmp_path):
    """Verify that 'soma transfer' copies a cell with reset fitness metrics."""
    from soma_cli.cli import main as cli_main

    # Setup source workspace
    source_ws = tmp_path / "source_project"
    source_cells = source_ws / ".soma" / "cells" / "walls"
    source_cells.mkdir(parents=True)
    source_cell = source_cells / "sec-guard.md"
    source_cell.write_text(
        "---\n"
        "id: sec-guard\n"
        "type: wall\n"
        "target_paths:\n"
        "  - 'src/**'\n"
        "fitness:\n"
        "  score: 0.95\n"
        "  triggers: 42\n"
        "  true_positives: 40\n"
        "  false_positives: 2\n"
        "lineage:\n"
        "  generation: 2\n"
        "---\n"
        "Wall content\n",
        encoding="utf-8",
    )

    # Setup target workspace
    target_ws = tmp_path / "target_project"
    (target_ws / ".soma").mkdir(parents=True)

    # Run soma transfer
    old_cwd = os.getcwd()
    os.chdir(str(source_ws))
    try:
        rc = cli_main(["transfer", "sec-guard", "--to", str(target_ws)])
        assert rc == 0
    finally:
        os.chdir(old_cwd)

    dest_cell = target_ws / ".soma" / "cells" / "walls" / "sec-guard.md"
    assert dest_cell.exists()

    content = dest_cell.read_text(encoding="utf-8")
    assert "Wall content" in content
    # Fitness metrics must be reset
    assert "score: null" in content or "score: None" in content
    assert "triggers: 0" in content
    assert "true_positives: 0" in content
    assert "false_positives: 0" in content
    # Lineage incremented
    assert "generation: 3" in content
    assert "created_by: transfer" in content


def test_shell_shims_forward_to_python_cli(tmp_path, bash):
    """Verify that enzymes/*.sh forwarding shims execute python cleanly."""
    env = dict(os.environ)
    env["SOMA_PYTHON"] = sys.executable

    # 1. safety_gate.sh
    safety_gate_sh = ENZYMES_DIR / "safety_gate.sh"
    payload = json.dumps({"toolCall": {"name": "run_command", "args": {"CommandLine": "ls -la"}}})
    proc_sg = subprocess.run(
        [bash, str(safety_gate_sh)],
        input=payload,
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    assert proc_sg.returncode == 0, proc_sg.stderr
    out_sg = json.loads(proc_sg.stdout)
    assert out_sg.get("decision") == "allow"

    # 2. immune_init.sh
    immune_init_sh = ENZYMES_DIR / "immune_init.sh"
    proc_ii = subprocess.run(
        [bash, str(immune_init_sh)],
        input="{}",
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert proc_ii.returncode == 0, proc_ii.stderr

    # 3. session_close.sh
    session_close_sh = ENZYMES_DIR / "session_close.sh"
    proc_sc = subprocess.run(
        [bash, str(session_close_sh)],
        input="{}",
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert proc_sc.returncode == 0, proc_sc.stderr

    # 4. cell_transfer.sh help/usage
    cell_transfer_sh = ENZYMES_DIR / "cell_transfer.sh"
    proc_ct = subprocess.run(
        [bash, str(cell_transfer_sh), "--help"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    assert proc_ct.returncode == 0, proc_ct.stderr
    assert "transfer" in proc_ct.stdout.lower()

