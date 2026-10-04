import os
import subprocess
import pytest
from conftest import REPO_ROOT

ENZYMES = os.path.join(REPO_ROOT, "enzymes")

def _env(tmp_path, **extra):
    import sys
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = {"HOME": str(home), "USERPROFILE": str(home), "SOMA_PYTHON": sys.executable,
           "SOMA_PYTHON_RESOLVED": ""}
    env.update(extra)
    return env

def test_immune_sweep_runs_without_soma_data_dir(tmp_path, bash):
    env = _env(tmp_path)
    full_env = dict(os.environ)
    full_env.pop("SOMA_DATA_DIR", None)
    full_env.update(env)
    proc = subprocess.run(
        [bash, os.path.join(ENZYMES, "immune_sweep.sh")], cwd=str(tmp_path),
        env=full_env, stdin=subprocess.DEVNULL, capture_output=True,
        encoding="utf-8", errors="replace", timeout=120)
    assert "unbound variable" not in proc.stderr, proc.stderr
    assert proc.returncode == 0, proc.stdout[-800:] + proc.stderr[-800:]
    # The default data dir lives under the isolated home, never the real one.
    assert (tmp_path / "home" / ".gemini" / "antigravity").exists()
