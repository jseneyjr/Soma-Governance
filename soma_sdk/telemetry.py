"""Unified telemetry signal writer for the Soma evidence pipeline.

All fitness signal producers (CI reporter, outcome engine, MCP tools,
cell_signal.sh, fitness_updater) should call append_signal() to write
to the canonical evidence log at .soma/evidence/signals.jsonl.

Integrity guarantees (v0.89):
  * Every check-then-write runs under ``evidence_lock(workspace)`` — a
    dedicated, cross-process lock file at .soma/evidence/.signals.lock.
  * Records written with an ``idempotency_key`` carry a deterministic
    ``event_id`` plus a ``payload_digest``. Replaying the same event is a
    no-op; replaying the same event id with a different payload raises
    ``EventConflictError``.
  * Every new record is stamped with the current epoch ``generation``
    (.soma/epoch_generation). Callers can fence on ``expected_generation``
    so writers from before an epoch migration are rejected.
"""
try:
    import fcntl
except ImportError:
    fcntl = None  # Windows / restricted platforms: fall back to msvcrt or best effort
try:
    import msvcrt
except ImportError:
    msvcrt = None
import json
import os
import hashlib
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone

VALID_SIGNAL_TYPES = frozenset({'tp', 'fp', 'fn', 'trigger'})
VALID_SOURCES = frozenset({'ci', 'session', 'mcp', 'manual'})
SIGNALS_FILENAME = 'signals.jsonl'
LOCK_FILENAME = '.signals.lock'
EPOCH_FILENAME = 'epoch_generation'
DEFAULT_GENERATION = 1
_MSVCRT_RETRY_SECONDS = 0.05


class EventConflictError(ValueError):
    """An event_id already exists in the log with a different payload."""


class StaleGenerationError(RuntimeError):
    """The caller's expected epoch generation no longer matches the workspace."""


# Process-local locks complement the OS file lock: they serialise threads
# in one process even on platforms where no OS lock is available.
_thread_locks = {}
_thread_locks_guard = threading.Lock()


def _thread_lock_for(path):
    key = os.path.realpath(path)
    with _thread_locks_guard:
        lock = _thread_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _thread_locks[key] = lock
        return lock


def _os_lock(fh):
    if fcntl is not None:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
    elif msvcrt is not None:
        fh.seek(0)
        while True:
            try:
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                time.sleep(_MSVCRT_RETRY_SECONDS)
    # else: best effort — only the process-local thread lock applies


def _os_unlock(fh):
    if fcntl is not None:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    elif msvcrt is not None:
        fh.seek(0)
        try:
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass


@contextmanager
def evidence_lock(workspace):
    """Exclusive, cross-process lock over the workspace evidence log.

    Not re-entrant: do not call append_signal() while holding it.
    """
    evidence_dir = os.path.join(workspace, '.soma', 'evidence')
    os.makedirs(evidence_dir, exist_ok=True)
    lock_path = os.path.join(evidence_dir, LOCK_FILENAME)
    with _thread_lock_for(lock_path):
        with open(lock_path, 'a+b') as fh:
            _os_lock(fh)
            try:
                yield lock_path
            finally:
                _os_unlock(fh)


def read_generation(workspace):
    """Return the workspace epoch generation (default 1 if absent/invalid)."""
    path = os.path.join(workspace, '.soma', EPOCH_FILENAME)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            value = int(f.read().strip())
    except (OSError, ValueError):
        return DEFAULT_GENERATION
    return value if value >= 1 else DEFAULT_GENERATION


def compute_payload_digest(cell_name, signal_type, source, metadata):
    """sha256 of the canonical event payload (timestamp excluded)."""
    payload = {
        'cell': cell_name,
        'signal': signal_type,
        'source': source,
        'metadata': metadata or None,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def compute_event_id(principal, idempotency_scope, idempotency_key, cell_name):
    """Deterministic event identity. Excludes signal type and metadata by design."""
    identity = f"{principal}:{idempotency_scope}:{idempotency_key}:{cell_name}"
    return hashlib.sha256(identity.encode('utf-8')).hexdigest()


def _read_existing_events(log_path):
    """Return raw ledger bytes and the first record for each event id."""
    try:
        with open(log_path, 'rb') as f:
            raw = f.read()
    except FileNotFoundError:
        return b'', {}

    by_id = {}
    for line in raw.splitlines():
        try:
            record = json.loads(line.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(record, dict) and record.get('event_id'):
            by_id.setdefault(record['event_id'], record)
    return raw, by_id


def _fsync_dir(directory):
    """Best-effort directory fsync after an atomic replace on POSIX."""
    if os.name != 'posix':
        return
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _atomic_replace_bytes(path, data):
    """Durably replace *path* using a temporary file in the same directory."""
    import tempfile

    directory = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(
        dir=directory, prefix=f'.{os.path.basename(path)}.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    _fsync_dir(directory)


def _migration_in_progress(workspace):
    return os.path.exists(os.path.join(workspace, '.soma', 'migration.lock'))


def _validate_event(event):
    """Validate and normalize one append_signals event specification."""
    if not isinstance(event, dict):
        raise ValueError('each event must be a mapping')

    cell_name = event.get('cell_name')
    signal_type = event.get('signal_type')
    source = event.get('source')
    metadata = event.get('metadata')
    principal = event.get('principal', 'unknown')
    scope = event.get('idempotency_scope', 'global')
    key = event.get('idempotency_key', '')

    if not isinstance(cell_name, str) or not cell_name:
        raise ValueError('cell_name must be a nonempty string')
    if signal_type not in VALID_SIGNAL_TYPES:
        raise ValueError(
            f'signal_type must be one of {sorted(VALID_SIGNAL_TYPES)}, '
            f'got {signal_type!r}'
        )
    if source not in VALID_SOURCES:
        raise ValueError(
            f'source must be one of {sorted(VALID_SOURCES)}, got {source!r}'
        )
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError('metadata must be a mapping or None')
    for name, value in (
        ('principal', principal), ('idempotency_scope', scope),
        ('idempotency_key', key),
    ):
        if not isinstance(value, str):
            raise ValueError(f'{name} must be a string')
    # Validate JSON serializability during planning, before any publication.
    try:
        json.dumps(metadata, sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValueError('metadata must be JSON serializable') from exc

    return cell_name, signal_type, source, metadata, principal, scope, key


def append_signals(workspace, events, expected_generation=None):
    """Atomically append a logical batch of canonical evidence events.

    Every event is validated and deduplicated while holding ``evidence_lock``.
    Any invalid event, idempotency conflict, stale generation, or publication
    failure leaves ``signals.jsonl`` byte-identical. Returned records preserve
    input order; idempotent replays return their previously persisted records.
    """
    if _migration_in_progress(workspace):
        raise RuntimeError('migration in progress')

    evidence_dir = os.path.join(workspace, '.soma', 'evidence')
    log_path = os.path.join(evidence_dir, SIGNALS_FILENAME)

    with evidence_lock(workspace):
        if _migration_in_progress(workspace):
            raise RuntimeError('migration in progress')

        generation = read_generation(workspace)
        if expected_generation is not None and expected_generation != generation:
            raise StaleGenerationError(
                f'expected generation {expected_generation}, workspace is at {generation}'
            )

        if isinstance(events, (str, bytes)):
            raise ValueError('events must be an iterable of mappings')
        try:
            event_specs = list(events)
        except TypeError as exc:
            raise ValueError('events must be an iterable of mappings') from exc

        raw, existing_by_id = _read_existing_events(log_path)
        planned_by_id = dict(existing_by_id)
        new_records = []
        results = []

        for event in event_specs:
            (cell_name, signal_type, source, metadata, principal,
             scope, key) = _validate_event(event)
            event_id = None
            payload_digest = None
            if key:
                event_id = compute_event_id(principal, scope, key, cell_name)
                payload_digest = compute_payload_digest(
                    cell_name, signal_type, source, metadata)
                existing = planned_by_id.get(event_id)
                if existing is not None:
                    existing_digest = existing.get('payload_digest') or compute_payload_digest(
                        existing.get('cell'), existing.get('signal'),
                        existing.get('source'), existing.get('metadata'))
                    if existing_digest != payload_digest:
                        raise EventConflictError(
                            f'event {event_id} already recorded with a different payload'
                        )
                    results.append(existing)
                    continue

            record = {
                'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'cell': cell_name,
                'signal': signal_type,
                'source': source,
            }
            if event_id is not None:
                record['event_id'] = event_id
                record['payload_digest'] = payload_digest
            record['generation'] = generation
            if metadata:
                record['metadata'] = metadata

            # Serialization is part of planning: no write can precede an error.
            json.dumps(record, ensure_ascii=False)
            new_records.append(record)
            results.append(record)
            if event_id is not None:
                planned_by_id[event_id] = record

        if new_records:
            prefix = raw
            if prefix and not prefix.endswith(b'\n'):
                prefix += b'\n'
            payload = b''.join(
                (json.dumps(record, ensure_ascii=False) + '\n').encode('utf-8')
                for record in new_records
            )
            _atomic_replace_bytes(log_path, prefix + payload)
        return results


def append_signal(workspace, cell_name, signal_type, source, metadata=None, principal="unknown",
                  idempotency_scope="global", idempotency_key="", expected_generation=None):
    """Append one signal through the atomic multi-event writer."""
    records = append_signals(
        workspace,
        [{
            'cell_name': cell_name,
            'signal_type': signal_type,
            'source': source,
            'metadata': metadata,
            'principal': principal,
            'idempotency_scope': idempotency_scope,
            'idempotency_key': idempotency_key,
        }],
        expected_generation=expected_generation,
    )
    return records[0]


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Append a signal to the Soma evidence log')
    parser.add_argument('--workspace', default='.', help='Workspace root')
    parser.add_argument('--cell', required=True, help='Cell name')
    parser.add_argument('--signal', required=True, choices=sorted(VALID_SIGNAL_TYPES),
                        help='Signal type')
    parser.add_argument('--source', required=True, choices=sorted(VALID_SOURCES),
                        help='Signal source')
    parser.add_argument('--meta', nargs='*', help='Metadata key=value pairs')

    args = parser.parse_args()

    metadata = {}
    if args.meta:
        for item in args.meta:
            k, _, v = item.partition('=')
            metadata[k] = v

    append_signal(
        workspace=args.workspace,
        cell_name=args.cell,
        signal_type=args.signal,
        source=args.source,
        metadata=metadata or None,
    )
    print(f'Signal recorded: {args.cell} / {args.signal} / {args.source}')
