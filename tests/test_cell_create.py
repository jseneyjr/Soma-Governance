import os
import pytest
from conftest import REPO_ROOT, run, symlink_or_skip

ENZYMES = os.path.join(REPO_ROOT, "enzymes")

def _env(tmp_path, **extra):
    import sys
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = {"HOME": str(home), "USERPROFILE": str(home), "SOMA_PYTHON": sys.executable,
           "SOMA_PYTHON_RESOLVED": ""}
    env.update(extra)
    return env

@pytest.fixture
def link_dir(tmp_path):
    d = tmp_path / "links"
    d.mkdir()
    return d

def _link(link_dir, name):
    link = link_dir / name
    symlink_or_skip(os.path.join(ENZYMES, name), link)
    return str(link)

def test_cell_create_via_symlink(tmp_path, link_dir, bash):
    proj = tmp_path / "proj"
    (proj / ".soma" / "cells").mkdir(parents=True)
    proc = run([bash, _link(link_dir, "cell_create.sh"), "--type", "vacuole",
                "--hypothesis", "linked", "--id", "vac-linked"],
               cwd=str(proj), env=_env(tmp_path))
    assert "No such file" not in proc.stderr, proc.stderr
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert list((proj / ".soma" / "cells").rglob("*vac-linked*"))
