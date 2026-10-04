import os
import pytest
from conftest import REPO_ROOT, read, run, symlink_or_skip

ENZYMES = os.path.join(REPO_ROOT, "enzymes")

CELL = """---
id: vac-transfer-me
type: vacuole
fitness:
  triggers: 7
  true_positives: 3
---
# Vacuole: transfer me
"""

@pytest.fixture
def projects(tmp_path):
    pytest.importorskip("yaml")
    src = tmp_path / "src"
    (src / ".soma" / "cells" / "vacuoles").mkdir(parents=True)
    (src / ".soma" / "cells" / "vacuoles" / "vac-transfer-me.md").write_text(CELL, encoding="utf-8")
    (src / "sub" / "dir").mkdir(parents=True)
    dst = tmp_path / "dst"
    (dst / ".soma").mkdir(parents=True)
    return src, dst

def _env(tmp_path, **extra):
    import sys
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = {"HOME": str(home), "USERPROFILE": str(home), "SOMA_PYTHON": sys.executable,
           "SOMA_PYTHON_RESOLVED": ""}
    env.update(extra)
    return env

def _assert_transferred(src, dst, cwd):
    out = dst / ".soma" / "cells" / "vacuoles" / "vac-transfer-me.md"
    assert out.exists(), "cell was not copied"
    assert "true_positives: 0" in read(str(out))
    log = src / ".soma" / "metrics" / "transfers.jsonl"
    assert log.exists(), "transfer was not logged in the source project"
    if cwd != src:
        assert not (cwd / ".soma").exists(), "metrics written relative to CWD"

def test_cell_transfer_resolves_repo_from_subdirectory(tmp_path, projects, bash):
    src, dst = projects
    cwd = src / "sub" / "dir"
    proc = run([bash, os.path.join(ENZYMES, "cell_transfer.sh"), "transfer-me",
                "--to", str(dst)], cwd=str(cwd), env=_env(tmp_path))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "unbound variable" not in proc.stderr
    _assert_transferred(src, dst, cwd)

def test_cell_transfer_honours_soma_root(tmp_path, projects, bash):
    src, dst = projects
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    proc = run([bash, os.path.join(ENZYMES, "cell_transfer.sh"), "transfer-me",
                "--to", str(dst)], cwd=str(elsewhere),
               env=_env(tmp_path, SOMA_ROOT=str(src)))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    _assert_transferred(src, dst, elsewhere)

def test_cell_transfer_without_a_project_fails_clearly(tmp_path, bash):
    nowhere = tmp_path / "nowhere"
    nowhere.mkdir()
    dst = tmp_path / "dst"
    (dst / ".soma").mkdir(parents=True)
    proc = run([bash, os.path.join(ENZYMES, "cell_transfer.sh"), "x",
                "--to", str(dst)], cwd=str(nowhere), env=_env(tmp_path, SOMA_ROOT=""))
    assert proc.returncode != 0
    assert "unbound variable" not in proc.stderr
    assert ".soma" in proc.stderr and "SOMA_ROOT" in proc.stderr, proc.stderr

@pytest.fixture
def link_dir(tmp_path):
    d = tmp_path / "links"
    d.mkdir()
    return d

def _link(link_dir, name):
    link = link_dir / name
    symlink_or_skip(os.path.join(ENZYMES, name), link)
    return str(link)

def test_cell_transfer_via_symlink(tmp_path, projects, link_dir, bash):
    src, dst = projects
    proc = run([bash, _link(link_dir, "cell_transfer.sh"), "transfer-me",
                "--to", str(dst)], cwd=str(src), env=_env(tmp_path))
    assert "No such file" not in proc.stderr, proc.stderr
    assert proc.returncode == 0, proc.stdout + proc.stderr
    _assert_transferred(src, dst, src)
