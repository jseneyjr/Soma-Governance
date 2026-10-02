"""Generation-fenced epoch migration for the Soma evidence store.

Cutover steps (all while holding migration.lock AND evidence_lock):
  1. Read legacy evidence (fitness.jsonl, outcomes.jsonl) and signals.jsonl.
  2. Convert legacy rows to canonical signals with deterministic event ids,
     skipping rows already migrated and outcomes rows that already have an
     MCP twin in signals.jsonl (report_outcome dual-writes both files).
  3. Reconcile per-(cell, signal) counts against an independent expectation;
     abort with no changes on mismatch.
  4. Snapshot evidence into snapshot/gen-<old>/ with SHA256SUMS.
  5. Atomically rewrite signals.jsonl, then atomically bump epoch_generation.
"""
import errno
import os
import time
import json
import hashlib
import secrets
import tempfile
from collections import Counter
from pathlib import Path
from typing import Optional

from soma_sdk.telemetry import (
    evidence_lock,
    read_generation,
    compute_payload_digest,
    SIGNALS_FILENAME,
)

STALE_LOCK_TIMEOUT = 300  # seconds

FITNESS_FILENAME = "fitness.jsonl"
OUTCOMES_FILENAME = "outcomes.jsonl"
SESSIONS_FILENAME = "sessions_processed.jsonl"
SNAPSHOT_FILES = (FITNESS_FILENAME, OUTCOMES_FILENAME, SIGNALS_FILENAME, SESSIONS_FILENAME)
CHECKSUM_FILENAME = "SHA256SUMS"
MIGRATION_SOURCE = "manual"
_VALID_SIGNALS = frozenset({"tp", "fp", "fn", "trigger"})
_OUTCOME_SIGNAL_MAP = {
    "success": "tp", "tp": "tp",
    "failure": "fp", "fp": "fp",
    "partial": "trigger",
}


def _acquire_migration_lock(lock_path: Path) -> Optional[str]:
    """Acquire the migration lock and return its unpredictable owner token."""
    lock_str = str(lock_path)
    pid = os.getpid()
    owner = secrets.token_hex(32)
    payload = f"{pid}:{time.time()}:{owner}\n".encode("utf-8")
    for _ in range(2):
        try:
            fd = os.open(lock_str, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, payload)
            finally:
                os.close(fd)
            return owner
        except FileExistsError:
            try:
                content = lock_path.read_text(encoding="utf-8").strip()
                lock_pid = int(content.split(":", 1)[0])
            except (OSError, ValueError):
                try:
                    stale = time.time() - lock_path.stat().st_mtime > STALE_LOCK_TIMEOUT
                except OSError:
                    stale = False
                if not stale:
                    return None
            else:
                try:
                    os.kill(lock_pid, 0)
                except ProcessLookupError:
                    stale = True
                except PermissionError:
                    return None
                except OSError as exc:
                    if exc.errno != errno.ESRCH:
                        return None
                    stale = True
                else:
                    # Age alone must never allow stealing from a live owner.
                    return None

            if stale:
                try:
                    lock_path.unlink()
                except FileNotFoundError:
                    pass
                except OSError:
                    return None
                continue
            return None
    return None


def _release_migration_lock(lock_path: Path, owner: str) -> None:
    """Release only when the path still names the caller's lock token."""
    try:
        content = lock_path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return
    parts = content.split(":", 2)
    if len(parts) != 3 or parts[2] != owner:
        return
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass


# ── Helpers ───────────────────────────────────────────────────────────

def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fsync_dir(directory: Path) -> None:
    """Best-effort directory fsync so os.replace survives power loss (POSIX)."""
    if os.name != "posix":
        return
    try:
        fd = os.open(str(directory), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write via temp file in the same dir + flush + fsync + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    _fsync_dir(path.parent)


def _split_lines(data: bytes):
    """Yield (line_index, raw_line_without_newline) for every non-empty line."""
    for index, raw in enumerate(data.split(b"\n")):
        if raw.strip():
            yield index, raw


def _parse(raw: bytes):
    try:
        record = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return record if isinstance(record, dict) else None


def _migration_event_id(filename: str, line_index: int, raw_line: bytes) -> str:
    return _sha256_hex(
        f"migration:{filename}:{line_index}:{_sha256_hex(raw_line)}".encode("utf-8")
    )


def _legacy_key(filename: str, record: dict):
    """Independent expectation: (cell, signal, timestamp) for a legacy row, or None."""
    if filename == FITNESS_FILENAME:
        cell = record.get("cell_id") or record.get("cell")
        signal = record.get("signal")
        if signal not in _VALID_SIGNALS:
            signal = "trigger"
        timestamp = record.get("triggered_at") or record.get("timestamp")
    else:
        cell = record.get("cell_id") or record.get("cell")
        outcome = record.get("outcome")
        signal = _OUTCOME_SIGNAL_MAP.get(outcome.strip().lower()) if isinstance(outcome, str) else None
        timestamp = record.get("timestamp")
    if not isinstance(cell, str) or not cell or signal is None:
        return None
    return cell, signal, timestamp


def _convert_row(filename: str, line_index: int, raw_line: bytes, record: dict, generation: int):
    """Convert one legacy row into a canonical signals.jsonl record (or None)."""
    key = _legacy_key(filename, record)
    if key is None:
        return None
    cell, signal, timestamp = key
    metadata = {"migrated_from": filename}
    return {
        "timestamp": timestamp,
        "cell": cell,
        "signal": signal,
        "source": MIGRATION_SOURCE,
        "event_id": _migration_event_id(filename, line_index, raw_line),
        "payload_digest": compute_payload_digest(cell, signal, MIGRATION_SOURCE, metadata),
        "generation": generation,
        "metadata": metadata,
    }


def _plan(raw: dict, new_epoch: int):
    """Compute new records + reconciliation verdict. Pure: no filesystem access."""
    existing_by_id = {}
    mcp_twins = Counter()   # legacy twins: matched on (cell, signal, timestamp)
    # v0.89+ twins: remaining matches grouped by outcome_id, then (cell, signal).
    mcp_linked = {}
    for _, line in _split_lines(raw.get(SIGNALS_FILENAME, b"")):
        rec = _parse(line)
        if rec is None:
            continue
        if rec.get("event_id"):
            existing_by_id.setdefault(rec["event_id"], rec)
        if rec.get("source") == "mcp":
            metadata = rec.get("metadata")
            linked = metadata.get("outcome_id") if isinstance(metadata, dict) else None
            if linked:
                matches = mcp_linked.setdefault(linked, Counter())
                matches[(rec.get("cell"), rec.get("signal"))] += 1
            else:
                mcp_twins[(rec.get("cell"), rec.get("signal"), rec.get("timestamp"))] += 1

    expected = Counter()
    actual = Counter()
    new_records = []
    new_by_id = {}
    stats = {
        "converted": 0,
        "skipped_existing": 0,
        "skipped_twin": 0,
        "unconvertible": 0,
        "linked_mismatch": False,
    }

    for filename in (FITNESS_FILENAME, OUTCOMES_FILENAME):
        for line_index, line in _split_lines(raw.get(filename, b"")):
            rec = _parse(line)
            key = _legacy_key(filename, rec) if rec is not None else None
            if key is None:
                stats["unconvertible"] += 1
                continue
            cell, signal, timestamp = key
            expected[(cell, signal)] += 1

            outcome_id = rec.get("outcome_id") if filename == OUTCOMES_FILENAME else None
            linked_matches = mcp_linked.get(outcome_id) if outcome_id else None
            exact = (cell, signal)
            if linked_matches and any(key != exact and count > 0
                                      for key, count in linked_matches.items()):
                stats["linked_mismatch"] = True
                continue

            event_id = _migration_event_id(filename, line_index, line)
            if event_id in existing_by_id:
                prior = existing_by_id[event_id]
                actual[(prior.get("cell"), prior.get("signal"))] += 1
                stats["skipped_existing"] += 1
                continue
            if linked_matches and linked_matches[exact] > 0:
                linked_matches[exact] -= 1
                actual[(cell, signal)] += 1
                stats["skipped_twin"] += 1
                continue
            if (filename == OUTCOMES_FILENAME and not outcome_id
                    and mcp_twins[(cell, signal, timestamp)] > 0):
                mcp_twins[(cell, signal, timestamp)] -= 1
                actual[(cell, signal)] += 1
                stats["skipped_twin"] += 1
                continue

            converted = _convert_row(filename, line_index, line, rec, new_epoch)
            if converted is None:
                continue  # counted as missing → reconciliation fails
            new_records.append(converted)
            new_by_id[converted["event_id"]] = converted
            stats["converted"] += 1

    # Count what will actually be written (re-parse the serialised bytes).
    payload = b"".join(
        (json.dumps(r, ensure_ascii=False) + "\n").encode("utf-8") for r in new_records
    )
    for _, line in _split_lines(payload):
        rec = _parse(line)
        if rec is not None:
            actual[(rec.get("cell"), rec.get("signal"))] += 1

    stats["reconciled"] = (expected == actual and not stats["linked_mismatch"])
    return payload, stats


def run_epoch_migration(workspace: str) -> bool:
    """Run an atomic, generation-fenced epoch cutover. Returns True on success."""
    ws = Path(workspace)
    soma_dir = ws / ".soma"
    migration_lock = soma_dir / "migration.lock"
    epoch_file = soma_dir / "epoch_generation"
    evidence_dir = soma_dir / "evidence"

    soma_dir.mkdir(parents=True, exist_ok=True)

    # 1. Acquire exclusive migration lease atomically.
    owner = _acquire_migration_lock(migration_lock)
    if owner is None:
        return False

    try:
        # 2. Hold the evidence lock for the whole cutover: no append interleaves.
        with evidence_lock(str(ws)):
            old_epoch = read_generation(str(ws))
            new_epoch = old_epoch + 1

            raw = {}
            for name in SNAPSHOT_FILES:
                path = evidence_dir / name
                if path.is_file():
                    raw[name] = path.read_bytes()

            payload, stats = _plan(raw, new_epoch)
            if not stats["reconciled"]:
                return False  # abort: nothing has been written yet

            # 3. Snapshot exactly the bytes we processed, with checksums.
            snapshot_dir = evidence_dir / "snapshot" / f"gen-{old_epoch}"
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            sums = []
            for name in sorted(raw):
                _atomic_write_bytes(snapshot_dir / name, raw[name])
                sums.append(f"{_sha256_hex(raw[name])}  {name}\n")
            _atomic_write_bytes(snapshot_dir / CHECKSUM_FILENAME, "".join(sums).encode("utf-8"))

            # 4. Atomically publish converted signals (skip if nothing new).
            if payload:
                existing = raw.get(SIGNALS_FILENAME, b"")
                if existing and not existing.endswith(b"\n"):
                    existing += b"\n"
                _atomic_write_bytes(evidence_dir / SIGNALS_FILENAME, existing + payload)

            # 5. Bump the generation last: old-generation writers are now fenced.
            _atomic_write_bytes(epoch_file, f"{new_epoch}\n".encode("utf-8"))
            return True
    finally:
        _release_migration_lock(migration_lock, owner)
