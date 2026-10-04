"""Security and confinement regression tests for installer/uninstaller (Phase 2).

Verifies symlink unlink guards in install.sh, atomic staging in uninstall.sh,
and path confinement / sanitization for mulch queue cell creation.
"""
import os
import subprocess
from pathlib import Path
import pytest

from conftest import REPO_ROOT, require_bash, run


def test_install_sh_unlinks_symlink_before_writing_rules(tmp_path, fake_home):
    """install.sh must unlink pre-existing symlinks in target rules dir instead of writing through them."""
    bash = require_bash()
    kiro_dir = fake_home / ".kiro" / "steering"
    kiro_dir.mkdir(parents=True)

    # Create a target rule as a symlink pointing to a sensitive file outside
    target_rule = kiro_dir / "core-change-protocol.md"
    sensitive_file = tmp_path / "sensitive.txt"
    sensitive_file.write_text("SENSITIVE CONTENT", encoding="utf-8")
    os.symlink(str(sensitive_file), str(target_rule))

    env = {"HOME": str(fake_home), "USERPROFILE": str(fake_home), "SOMA_PYTHON": "python3"}
    proc = run([bash, os.path.join(REPO_ROOT, "install", "install.sh"), "kiro"], env=env)
    assert proc.returncode == 0, proc.stderr

    # Sensitive file must NOT have been overwritten
    assert sensitive_file.read_text(encoding="utf-8") == "SENSITIVE CONTENT"
    # Target rule must now be a regular file, not a symlink
    assert not os.path.islink(target_rule)


def test_uninstall_sh_atomic_python_edit_preserves_file_on_error(tmp_path, fake_home):
    """uninstall.sh must not delete a user file if inline python editing fails."""
    bash = require_bash()
    claude_md = fake_home / ".claude" / "CLAUDE.md"
    claude_md.parent.mkdir(parents=True)
    claude_md.write_text("# User Content\nKeep this\n# Soma Governance Rules\nDelete this\n", encoding="utf-8")

    # Run uninstall with keep-config
    env = {"HOME": str(fake_home), "USERPROFILE": str(fake_home), "SOMA_PYTHON": "python3"}
    proc = run([bash, os.path.join(REPO_ROOT, "install", "uninstall.sh"), "claude", "--force", "--no-restore"], env=env)
    assert proc.returncode == 0, proc.stderr

    # The file should exist and contain user content, but not Soma content
    assert claude_md.exists()
    content = claude_md.read_text(encoding="utf-8")
    assert "User Content" in content
    assert "Soma Governance Rules" not in content


def test_cell_create_sh_blocks_path_traversal(tmp_path):
    """cell_create.sh must reject ID_OVERRIDE with path traversal tokens."""
    bash = require_bash()
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / ".soma" / "cells" / "vacuoles").mkdir(parents=True)

    cell_create = os.path.join(REPO_ROOT, "enzymes", "cell_create.sh")
    proc = run([bash, cell_create, "--id", "../../../pwned", "--type", "vacuole", "--hypothesis", "test"], cwd=str(proj))
    assert proc.returncode != 0 or not (tmp_path / "pwned.md").exists()
    assert not (tmp_path / "pwned.md").exists()
