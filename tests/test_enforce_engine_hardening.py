"""Enforcement & Engine Script Hardening Tests (Phase 3).

Verifies cell_enforce.py generated bash hooks under set -u with empty patterns,
correct cell_signal.sh path, and soma_py CWD isolation.
"""
import os
import subprocess
import pytest
import sys
from pathlib import Path

from conftest import REPO_ROOT, require_bash, run

from soma_core.enforcement import generate_precommit_check


def test_cell_enforce_empty_target_patterns_bash_syntax(tmp_path):
    """Generated bash hook with empty target_patterns must execute without set -u unbound variable error."""
    bash = require_bash()
    cell = {
        "_name": "test_empty_patterns",
        "type": "wall",
        "hypothesis": "Test hypothesis",
        "target_paths": []
    }
    hook_code = generate_precommit_check(cell, ".")

    assert "../../enzymes" in hook_code, "Script dir should point to enzymes, not scripts"

    # Write hook code to temp script inside tmp_path and execute under bash
    tmp_script = tmp_path / "test_hook.sh"
    tmp_script.write_text(hook_code, encoding="utf-8")
    proc = subprocess.run([bash, str(tmp_script)], capture_output=True, text=True)
    # Should exit 0 without any bash unbound variable error
    assert proc.returncode == 0
    assert "unbound variable" not in proc.stderr


def test_soma_py_cwd_isolation(tmp_path, fake_home):
    """soma_py must isolate CWD from sys.path when running -c or -."""
    if not os.path.exists(f"{REPO_ROOT}/enzymes/soma_python.sh"):
        pytest.skip("enzymes directory purged in v0.97.0")
    bash = require_bash()
    
    # Create a dummy json.py in tmp_path (simulating malicious/accidental CWD file)
    bad_module = tmp_path / "json.py"
    bad_module.write_text("raise RuntimeError('CWD module executed!')", encoding="utf-8")

    env = {
        "HOME": str(fake_home),
        "USERPROFILE": str(fake_home),
        "PATH": os.environ.get("PATH", ""),
        "SOMA_PYTHON": "python3"
    }

    # Execute soma_py -c 'import json; print("OK")' in tmp_path
    cmd = [
        bash, "-c",
        f"source '{REPO_ROOT}/enzymes/soma_python.sh' && soma_resolve_python && soma_py -c 'import json; print(\"OK\")'"
    ]
    proc = run(cmd, cwd=str(tmp_path), env=env)
    assert proc.returncode == 0, proc.stderr
    assert "OK" in proc.stdout

def test_cell_enforce_handles_null_target_paths():
    """generate_precommit_check must handle target_paths=None without crashing."""
    from soma_core.enforcement import generate_precommit_check
    cell = {
        "_name": "test-null-targets",
        "type": "wall",
        "hypothesis": "test",
        "target_paths": None,
    }
    check_code = generate_precommit_check(cell, "/tmp")
    assert "TARGET_PATTERNS=()" in check_code
