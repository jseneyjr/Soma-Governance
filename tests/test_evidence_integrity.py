"""Cross-process integrity tests for the evidence pipeline (v0.89 audit fixes).

Covers what single-process unit tests cannot: the evidence lock really is
an OS-level lock, idempotent appends dedupe across processes, the migration
holds the lock for its whole cutover, and fcntl-less platforms keep the
idempotency/fence semantics.
"""
import json
import os
import subprocess
import sys
import textwrap
import time

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None


def _env():
    env = dict(os.environ)
    env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _spawn(code, prelude=""):
    return subprocess.Popen(
        [sys.executable, "-c", prelude + textwrap.dedent(code)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        cwd=REPO_ROOT, env=_env(),
    )


def _rows(ws):
    path = os.path.join(ws, ".soma", "evidence", "signals.jsonl")
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_idempotent_append_dedupes_across_processes(tmp_path):
    ws = str(tmp_path)
    code = f"""
        from soma_sdk.telemetry import append_signal
        for _ in range(20):
            append_signal({ws!r}, "cell-a", "tp", "ci", principal="p",
                          idempotency_scope="run", idempotency_key="op-1")
    """
    procs = [_spawn(code) for _ in range(4)]
    for p in procs:
        _, err = p.communicate(timeout=60)
        assert p.returncode == 0, err
    rows = _rows(ws)
    assert len(rows) == 1
    assert rows[0]["event_id"]


@pytest.mark.skipif(fcntl is None, reason="needs fcntl to probe the OS lock")
def test_migration_holds_evidence_lock_for_whole_cutover(tmp_path, monkeypatch):
    from soma_cli import migration

    ws = tmp_path
    ev = ws / ".soma" / "evidence"
    ev.mkdir(parents=True)
    (ev / "fitness.jsonl").write_text(
        json.dumps({"cell_id": "cell-a", "triggered_at": "2026-01-01T00:00:00Z"}) + "\n")
    lock_path = ev / ".signals.lock"
    probes = []
    real_write = migration._atomic_write_bytes

    def probing_write(path, data):
        with open(lock_path, "a+b") as fh:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                probes.append("held")
            else:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                probes.append("free")
        return real_write(path, data)

    monkeypatch.setattr(migration, "_atomic_write_bytes", probing_write)
    assert migration.run_epoch_migration(str(ws)) is True
    assert probes and set(probes) == {"held"}


def test_concurrent_writers_during_migration_lose_nothing(tmp_path):
    from soma_cli.migration import run_epoch_migration

    ws = str(tmp_path)
    ev = os.path.join(ws, ".soma", "evidence")
    os.makedirs(ev)
    with open(os.path.join(ev, "fitness.jsonl"), "w", encoding="utf-8") as f:
        for i in range(50):
            f.write(json.dumps({"cell_id": f"legacy-{i}",
                                "triggered_at": "2026-01-01T00:00:00Z"}) + "\n")

    def writer(n):
        return f"""
            from soma_sdk.telemetry import append_signal
            ok = 0
            for i in range(200):
                try:
                    append_signal({ws!r}, "live-{n}-%d" % i, "trigger", "session")
                    ok += 1
                except RuntimeError as exc:
                    assert "migration in progress" in str(exc), exc
            print(ok)
        """

    procs = [_spawn(writer(n)) for n in range(3)]
    # Wait until writers are actively appending so the cutover overlaps them.
    signals_path = os.path.join(ev, "signals.jsonl")
    deadline = time.time() + 30
    while time.time() < deadline:
        if os.path.exists(signals_path) and os.path.getsize(signals_path) > 0:
            break
        time.sleep(0.005)
    assert run_epoch_migration(ws) is True
    written = 0
    for p in procs:
        out, err = p.communicate(timeout=120)
        assert p.returncode == 0, err
        written += int(out.strip())

    rows = _rows(ws)  # every line must parse
    migrated = [r for r in rows if (r.get("metadata") or {}).get("migrated_from")]
    live = [r for r in rows if r["cell"].startswith("live-")]
    assert len(migrated) == 50
    assert len(live) == written
    assert {r["generation"] for r in live} <= {1, 2}
    assert len({r["event_id"] for r in migrated}) == 50


def test_idempotency_and_fence_without_fcntl(tmp_path):
    ws = str(tmp_path)
    code = f"""
        import json
        from soma_sdk.telemetry import (append_signal, EventConflictError,
                                        StaleGenerationError)
        a = append_signal({ws!r}, "cell-a", "tp", "mcp", idempotency_key="k")
        b = append_signal({ws!r}, "cell-a", "tp", "mcp", idempotency_key="k")
        assert a == b
        try:
            append_signal({ws!r}, "cell-a", "fp", "mcp", idempotency_key="k")
        except EventConflictError:
            pass
        else:
            raise SystemExit("expected EventConflictError")
        try:
            append_signal({ws!r}, "cell-a", "tp", "mcp", expected_generation=7)
        except StaleGenerationError:
            pass
        else:
            raise SystemExit("expected StaleGenerationError")
        print("ok")
    """
    p = _spawn(code, prelude="import sys; sys.modules['fcntl'] = None\n")
    out, err = p.communicate(timeout=60)
    assert p.returncode == 0, err
    assert out.strip() == "ok"
    assert len(_rows(ws)) == 1
