"""BUG-008: soma_mcp and soma_sdk.telemetry must work where `fcntl` is unavailable.

`fcntl` is POSIX-only, so on Windows an unconditional import crashed the MCP
server at startup. Each test runs in a subprocess with `fcntl` blocked
(sys.modules entry set to None makes `import fcntl` raise ImportError), which
reproduces the Windows condition on every OS.
"""
import json
import os
import subprocess
import sys
import textwrap

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BLOCK_FCNTL = "import sys; sys.modules['fcntl'] = None\n"


def _run_without_fcntl(code, env_extra=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-c", BLOCK_FCNTL + textwrap.dedent(code)],
        capture_output=True, text=True, cwd=REPO_ROOT, env=env, timeout=60,
    )


def _make_workspace(tmp_path, cell_name="trap-example"):
    cells = tmp_path / ".soma" / "cells" / "vacuoles"
    cells.mkdir(parents=True)
    (cells / f"{cell_name}.md").write_text(
        "---\n"
        f"id: {cell_name}\n"
        "type: vacuole\n"
        "domain: testing\n"
        "hypothesis: Example hypothesis\n"
        "prediction: Example prediction\n"
        "---\n"
        "# Example\n",
        encoding="utf-8",
    )
    return tmp_path


def test_blocking_fcntl_really_raises_import_error():
    proc = _run_without_fcntl("""
        try:
            import fcntl
        except ImportError:
            print("blocked")
    """)
    assert proc.stdout.strip() == "blocked", proc.stderr


def test_mcp_server_modules_import_without_fcntl():
    proc = _run_without_fcntl("""
        import soma_mcp.server, soma_mcp.tools, soma_sdk.telemetry
        print("ok")
    """)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "ok"


def test_append_signal_writes_record_without_fcntl(tmp_path):
    proc = _run_without_fcntl(f"""
        from soma_sdk.telemetry import append_signal
        append_signal({str(tmp_path)!r}, "trap-example", "tp", "mcp")
    """)
    assert proc.returncode == 0, proc.stderr
    lines = (tmp_path / ".soma" / "evidence" / "signals.jsonl").read_text(
        encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert (record["cell"], record["signal"], record["source"]) == ("trap-example", "tp", "mcp")


def test_report_outcome_writes_outcomes_without_fcntl(tmp_path):
    workspace = _make_workspace(tmp_path)
    proc = _run_without_fcntl("""
        import json
        from soma_mcp.tools import execute_tool
        result = execute_tool("soma_report_outcome",
                              {"outcome": "success", "cells_used": ["trap-example"]})
        print(json.dumps(result))
    """, env_extra={"SOMA_ROOT": str(workspace)})
    assert proc.returncode == 0, proc.stderr
    outcomes = (workspace / ".soma" / "evidence" / "outcomes.jsonl").read_text(
        encoding="utf-8").splitlines()
    assert [json.loads(line)["cell_id"] for line in outcomes] == ["trap-example"]
