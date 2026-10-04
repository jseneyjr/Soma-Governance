import os
import json
import hashlib
import pytest
from pathlib import Path
from soma_cli import migration
from soma_cli.migration import run_epoch_migration
from soma_sdk.telemetry import append_signal, StaleGenerationError

def test_epoch_migration_lifecycle(tmp_path):
    ws = tmp_path / "workspace"
    evidence_dir = ws / ".soma" / "evidence"
    evidence_dir.mkdir(parents=True)
    
    # 1. Start with epoch 1
    (ws / ".soma" / "epoch_generation").write_text("1")
    
    # Write some legacy evidence
    legacy_file = evidence_dir / "fitness.jsonl"
    legacy_file.write_text('{"cell": "foo", "signal": "tp"}\n')
    
    # Run migration
    assert run_epoch_migration(str(ws)) == True
    
    # Check that generation is now 2
    assert (ws / ".soma" / "epoch_generation").read_text().strip() == "2"
    
    # Check that legacy file was snapshotted (per-generation snapshot dir)
    assert (evidence_dir / "snapshot" / "gen-1" / "fitness.jsonl").exists()
    
    # New writes should require the correct epoch (this is internal to telemetry)
    # append_signal should work if no epoch generation is passed or if we pass the right one
    
def test_migration_blocks_telemetry(tmp_path):
    ws = tmp_path / "workspace"
    (ws / ".soma" / "evidence").mkdir(parents=True)
    (ws / ".soma" / "migration.lock").touch()
    
    # Telemetry should fail if migration lock is active
    with pytest.raises(RuntimeError, match="migration in progress"):
        append_signal(str(ws), "foo", "tp", "manual")


# ── Generation-fenced cutover ──────────────────────────────────────────

def _lines(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _workspace(tmp_path):
    ws = tmp_path / "ws"
    ev = ws / ".soma" / "evidence"
    ev.mkdir(parents=True)
    (ws / ".soma" / "epoch_generation").write_text("1")
    return ws, ev


def _migrated(ev):
    return [r for r in _lines(ev / "signals.jsonl")
            if isinstance(r.get("metadata"), dict) and "migrated_from" in r["metadata"]]


def test_converts_fitness_and_outcomes_rows(tmp_path):
    ws, ev = _workspace(tmp_path)
    _write_jsonl(ev / "fitness.jsonl", [
        {"cell_id": "cell-a", "triggered_at": "2026-01-01T00:00:00Z", "matched_files": ["x.py"]},
        {"cell_id": "cell-a", "triggered_at": "2026-01-02T00:00:00Z"},
    ])
    _write_jsonl(ev / "outcomes.jsonl", [
        {"cell_id": "cell-b", "outcome": "success", "timestamp": "2026-01-03T00:00:00Z"},
        {"cell_id": "cell-b", "outcome": "tp", "timestamp": "2026-01-03T00:00:01Z"},
        {"cell_id": "cell-b", "outcome": "failure", "timestamp": "2026-01-03T00:00:02Z"},
        {"cell_id": "cell-b", "outcome": "fp", "timestamp": "2026-01-03T00:00:03Z"},
        {"cell_id": "cell-b", "outcome": "partial", "timestamp": "2026-01-03T00:00:04Z"},
    ])

    assert run_epoch_migration(str(ws)) is True

    rows = _migrated(ev)
    pairs = sorted((r["cell"], r["signal"]) for r in rows)
    assert pairs == sorted([
        ("cell-a", "trigger"), ("cell-a", "trigger"),
        ("cell-b", "tp"), ("cell-b", "tp"), ("cell-b", "fp"), ("cell-b", "fp"),
        ("cell-b", "trigger"),
    ])
    for r in rows:
        assert r["source"] == "manual"
        assert r["generation"] == 2
        assert r["metadata"]["migrated_from"] in ("fitness.jsonl", "outcomes.jsonl")
    # Original timestamps preserved
    assert {r["timestamp"] for r in rows if r["cell"] == "cell-a"} == {
        "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"}

    # Deterministic event id: sha256("migration:<file>:<line_index>:<sha256(raw_line)>")
    raw0 = (ev / "fitness.jsonl").read_bytes().split(b"\n")[0]
    expected_id = hashlib.sha256(
        f"migration:fitness.jsonl:0:{hashlib.sha256(raw0).hexdigest()}".encode("utf-8")
    ).hexdigest()
    assert expected_id in {r["event_id"] for r in rows}


def test_preserves_existing_signals_and_appends(tmp_path):
    ws, ev = _workspace(tmp_path)
    append_signal(str(ws), "cell-z", "tp", "ci")
    before = (ev / "signals.jsonl").read_bytes()
    _write_jsonl(ev / "fitness.jsonl", [{"cell_id": "cell-a", "triggered_at": "2026-01-01T00:00:00Z"}])

    assert run_epoch_migration(str(ws)) is True

    after = (ev / "signals.jsonl").read_bytes()
    assert after.startswith(before)
    assert len(_lines(ev / "signals.jsonl")) == 2


def test_mcp_twin_rows_are_not_double_counted(tmp_path):
    ws, ev = _workspace(tmp_path)
    ts = "2026-02-01T10:00:00Z"
    # report_outcome dual-writes: outcomes.jsonl row + mcp twin in signals.jsonl
    _write_jsonl(ev / "outcomes.jsonl", [
        {"cell_id": "cell-m", "outcome": "success", "timestamp": ts},
        {"cell_id": "cell-m", "outcome": "success", "timestamp": ts},   # only one twin exists
        {"cell_id": "cell-n", "outcome": "failure", "timestamp": ts},   # no twin
    ])
    _write_jsonl(ev / "signals.jsonl", [
        {"timestamp": ts, "cell": "cell-m", "signal": "tp", "source": "mcp"},
        {"timestamp": ts, "cell": "cell-n", "signal": "fp", "source": "ci"},  # not mcp → not a twin
    ])

    assert run_epoch_migration(str(ws)) is True

    rows = _migrated(ev)
    assert sorted((r["cell"], r["signal"]) for r in rows) == [("cell-m", "tp"), ("cell-n", "fp")]
    all_rows = _lines(ev / "signals.jsonl")
    assert sum(1 for r in all_rows if r["cell"] == "cell-m" and r["signal"] == "tp") == 2


def test_rerun_converts_zero_new_rows(tmp_path):
    ws, ev = _workspace(tmp_path)
    _write_jsonl(ev / "fitness.jsonl", [{"cell_id": "cell-a", "triggered_at": "2026-01-01T00:00:00Z"}])
    _write_jsonl(ev / "outcomes.jsonl", [{"cell_id": "cell-b", "outcome": "success",
                                          "timestamp": "2026-01-01T00:00:00Z"}])

    assert run_epoch_migration(str(ws)) is True
    first = (ev / "signals.jsonl").read_bytes()
    assert len(_migrated(ev)) == 2

    assert run_epoch_migration(str(ws)) is True
    assert (ev / "signals.jsonl").read_bytes() == first
    assert (ws / ".soma" / "epoch_generation").read_text().strip() == "3"
    assert (ev / "snapshot" / "gen-2" / "SHA256SUMS").exists()


def test_new_legacy_rows_after_first_run_are_picked_up(tmp_path):
    ws, ev = _workspace(tmp_path)
    fitness = ev / "fitness.jsonl"
    _write_jsonl(fitness, [{"cell_id": "cell-a", "triggered_at": "2026-01-01T00:00:00Z"}])
    assert run_epoch_migration(str(ws)) is True
    with open(fitness, "a", encoding="utf-8") as f:
        f.write(json.dumps({"cell_id": "cell-a", "triggered_at": "2026-01-05T00:00:00Z"}) + "\n")
    assert run_epoch_migration(str(ws)) is True
    rows = _migrated(ev)
    assert len(rows) == 2
    assert [r["generation"] for r in rows] == [2, 3]


def _snapshot_state(ws):
    state = {}
    for p in sorted((ws / ".soma").rglob("*")):
        if p.is_file() and ".signals.lock" not in p.name:
            state[str(p.relative_to(ws))] = p.read_bytes()
    return state


def test_reconciliation_mismatch_aborts_without_changes(tmp_path, monkeypatch):
    ws, ev = _workspace(tmp_path)
    _write_jsonl(ev / "fitness.jsonl", [{"cell_id": "cell-a", "triggered_at": "2026-01-01T00:00:00Z"}])
    _write_jsonl(ev / "outcomes.jsonl", [{"cell_id": "cell-b", "outcome": "failure",
                                          "timestamp": "2026-01-01T00:00:00Z"}])
    append_signal(str(ws), "cell-z", "tp", "ci")
    before = _snapshot_state(ws)

    real_convert = migration._convert_row

    def corrupt(*args, **kwargs):
        rec = real_convert(*args, **kwargs)
        if rec is not None and rec["signal"] == "fp":
            rec["signal"] = "tp"   # wrong mapping → must be caught
        return rec

    monkeypatch.setattr(migration, "_convert_row", corrupt)
    assert run_epoch_migration(str(ws)) is False
    assert _snapshot_state(ws) == before
    assert not (ws / ".soma" / "migration.lock").exists()


def test_reconciliation_dropped_rows_abort(tmp_path, monkeypatch):
    ws, ev = _workspace(tmp_path)
    _write_jsonl(ev / "fitness.jsonl", [{"cell_id": "cell-a", "triggered_at": "2026-01-01T00:00:00Z"}])
    before = _snapshot_state(ws)
    monkeypatch.setattr(migration, "_convert_row", lambda *a, **k: None)
    assert run_epoch_migration(str(ws)) is False
    assert _snapshot_state(ws) == before


def test_stale_generation_writer_rejected_after_cutover(tmp_path):
    ws, ev = _workspace(tmp_path)
    old = 1
    append_signal(str(ws), "cell-a", "tp", "ci", expected_generation=old)
    assert run_epoch_migration(str(ws)) is True
    with pytest.raises(StaleGenerationError):
        append_signal(str(ws), "cell-a", "tp", "ci", expected_generation=old)
    rec = append_signal(str(ws), "cell-a", "tp", "ci", expected_generation=2)
    assert rec["generation"] == 2


def test_snapshot_has_checksums_for_every_evidence_file(tmp_path):
    ws, ev = _workspace(tmp_path)
    _write_jsonl(ev / "fitness.jsonl", [{"cell_id": "cell-a", "triggered_at": "2026-01-01T00:00:00Z"}])
    _write_jsonl(ev / "outcomes.jsonl", [{"cell_id": "cell-b", "outcome": "success",
                                          "timestamp": "2026-01-01T00:00:00Z"}])
    _write_jsonl(ev / "sessions_processed.jsonl", [{"session": "s1"}])
    append_signal(str(ws), "cell-z", "tp", "ci")
    originals = {name: (ev / name).read_bytes() for name in
                 ("fitness.jsonl", "outcomes.jsonl", "signals.jsonl", "sessions_processed.jsonl")}

    assert run_epoch_migration(str(ws)) is True

    snap = ev / "snapshot" / "gen-1"
    sums = {}
    for line in (snap / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        sums[name] = digest
    assert set(sums) == set(originals)
    for name, data in originals.items():
        assert (snap / name).read_bytes() == data
        assert sums[name] == hashlib.sha256(data).hexdigest()


def test_held_migration_lock_returns_false_and_changes_nothing(tmp_path):
    ws, ev = _workspace(tmp_path)
    _write_jsonl(ev / "fitness.jsonl", [{"cell_id": "cell-a", "triggered_at": "2026-01-01T00:00:00Z"}])
    (ws / ".soma" / "migration.lock").write_text(f"{os.getpid()}:9999999999\n")
    before = _snapshot_state(ws)
    assert run_epoch_migration(str(ws)) is False
    assert _snapshot_state(ws) == before

def test_migration_dedupes_linked_twin_even_when_timestamps_differ(tmp_path):
    from soma_cli.migration import run_epoch_migration
    ev = tmp_path / ".soma" / "evidence"
    ev.mkdir(parents=True)
    with open(ev / "outcomes.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({"cell_id": "cell-m", "outcome": "success",
                            "timestamp": "2026-02-01T10:00:00Z", "outcome_id": "oid-1"}) + "\n")
    with open(ev / "signals.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({"timestamp": "2026-02-01T10:00:01Z", "cell": "cell-m",
                            "signal": "tp", "source": "mcp",
                            "metadata": {"outcome_id": "oid-1"}}) + "\n")
    assert run_epoch_migration(str(tmp_path)) is True
    rows = _lines(ev / "signals.jsonl")
    assert sum(1 for r in rows if r["cell"] == "cell-m" and r["signal"] == "tp") == 1
