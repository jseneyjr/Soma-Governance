"""Tests for Maelstrom Round 2 hardening & security audit findings."""
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Ensure REPO_ROOT and enzymes/ are in sys.path for importing modules under test
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "enzymes") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "enzymes"))

def test_cell_create_sh_id_override_traversal_blocked_with_description(tmp_path):
    """cell_create.sh with --from-description must reject path traversal in --id."""
    env = dict(os.environ, SOMA_ROOT=str(tmp_path))
    (tmp_path / ".soma" / "cells" / "vacuoles").mkdir(parents=True, exist_ok=True)
    script = REPO_ROOT / "enzymes" / "cell_create.sh"
    
    proc = subprocess.run(
        ["bash", str(script), "--from-description", "test desc", "--id", "../../../evil"],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "traversal" in proc.stderr.lower() or "invalid" in proc.stderr.lower()

def test_cell_create_nl_py_id_traversal_blocked(tmp_path):
    """cell_create_nl.py must reject path traversal in --id."""
    env = dict(os.environ, SOMA_ROOT=str(tmp_path))
    (tmp_path / ".soma" / "cells" / "vacuoles").mkdir(parents=True, exist_ok=True)
    script = REPO_ROOT / "enzymes" / "cell_create_nl.py"
    
    proc = subprocess.run(
        [sys.executable, str(script), "test desc", "--id", "../../evil"],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "traversal" in proc.stderr.lower() or "invalid" in proc.stderr.lower() or "error" in proc.stderr.lower()

def test_cell_create_sh_unlinks_preexisting_symlink(tmp_path):
    """cell_create.sh must unlink pre-existing symlinks at target cell path."""
    cells_dir = tmp_path / ".soma" / "cells" / "vacuoles"
    cells_dir.mkdir(parents=True, exist_ok=True)
    
    target_file = tmp_path / "victim.txt"
    target_file.write_text("IMPORTANT DATA", encoding="utf-8")
    
    symlink_file = cells_dir / "test-symlink.md"
    try:
        symlink_file.symlink_to(target_file)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported on this platform/user")
        
    script = REPO_ROOT / "enzymes" / "cell_create.sh"
    env = dict(os.environ, SOMA_ROOT=str(tmp_path))
    
    proc = subprocess.run(
        ["bash", str(script), "--type", "vacuole", "--id", "test-symlink", "--hypothesis", "test hypo"],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    # The victim file must be untouched!
    assert target_file.read_text(encoding="utf-8") == "IMPORTANT DATA"
    # The cell file is a regular file now
    assert not symlink_file.is_symlink()

def test_cell_create_sh_escapes_quotes_in_hypothesis(tmp_path):
    """cell_create.sh must safely quote double quotes in hypothesis."""
    (tmp_path / ".soma" / "cells" / "vacuoles").mkdir(parents=True, exist_ok=True)
    script = REPO_ROOT / "enzymes" / "cell_create.sh"
    env = dict(os.environ, SOMA_ROOT=str(tmp_path))
    
    proc = subprocess.run(
        ["bash", str(script), "--type", "vacuole", "--id", "quote-test", "--hypothesis", 'hypo with "quotes" and -- markers'],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    cell_file = tmp_path / ".soma" / "cells" / "vacuoles" / "quote-test.md"
    assert cell_file.exists()
    content = cell_file.read_text(encoding="utf-8")
    assert content.startswith("---")
    # Verify YAML parsing
    import yaml
    fm_text = content[3:content.find("---", 3)]
    data = yaml.safe_load(fm_text)
    assert data["hypothesis"] == 'hypo with "quotes" and -- markers'

def test_load_cell_uses_created_field(tmp_path):
    """load_cell must read 'created' field from cell frontmatter."""
    from soma_sdk.cells import load_cell
    cell_file = tmp_path / ".soma" / "cells" / "vacuoles" / "created-test.md"
    cell_file.parent.mkdir(parents=True, exist_ok=True)
    cell_file.write_text("""---
id: created-test
type: vacuole
hypothesis: test
created: "2025-01-01T00:00:00Z"
---
body
""", encoding="utf-8")
    cell = load_cell("created-test", cells_dir=str(tmp_path / ".soma" / "cells"))
    assert cell.created_date == "2025-01-01T00:00:00Z" or getattr(cell.created_date, "year", None) == 2025

def test_cell_enforce_handles_null_target_paths():
    """generate_precommit_check must handle target_paths=None without crashing."""
    from cell_enforce import generate_precommit_check
    cell = {
        "_name": "test-null-targets",
        "type": "wall",
        "hypothesis": "test",
        "target_paths": None,
    }
    check_code = generate_precommit_check(cell, "/tmp")
    assert "TARGET_PATTERNS=()" in check_code

def test_pathcheck_on_path_handles_windows_colons():
    """on_path with sep=';' should not corrupt Windows drive paths containing colons."""
    from soma_cli.pathcheck import on_path
    path_env = r"C:\Python312\Scripts;C:\Windows\System32"
    assert on_path(r"C:\Python312\Scripts", path_env, sep=";", casefold=True)

def test_publish_workflow_isolates_release_assets():
    """publish.yml must isolate github release asset uploads to a separate job."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")
    assert "release-assets:" in workflow
    assert "RELEASE_TAG:" in workflow
    assert "|| true" not in workflow
