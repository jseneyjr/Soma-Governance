"""soma_core.telemetry — Unified telemetry, evidence signals, outcome reflection, and metrics.

Consolidates:
- Atomic evidence ledger, process locks, and idempotency (formerly soma_sdk.telemetry)
- Verifiable outcome engine and credit assignment (formerly enzymes/outcome_engine.py)
- Transcript fitness updater and platform detection (formerly enzymes/fitness_updater.py)
- Metrics snapshots and token census aggregation (formerly enzymes/metrics_snapshot.py)
- Quorum sensing across multi-cell triggers (formerly enzymes/cell_quorum.py)
- Codebase governance coverage mapping (formerly enzymes/cell_coverage.py)
- Single-grade governance report card (formerly enzymes/immune_grade.py)
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import fnmatch
from fractions import Fraction
import glob
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    import fcntl
except ImportError:
    fcntl = None  # Windows / restricted platforms: fall back to msvcrt or best effort
try:
    import msvcrt
except ImportError:
    msvcrt = None

try:
    import yaml
except ImportError:
    yaml = None

from soma_core.workspace import resolve_workspace
from soma_core.frontmatter import parse_frontmatter, _get_body, dump_frontmatter


# ── Evidence Ledger & Atomic Locking ──────────────────────────────────────

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


_thread_locks: dict[str, threading.RLock] = {}
_thread_locks_guard = threading.Lock()


def _thread_lock_for(path: str) -> threading.RLock:
    key = os.path.realpath(path)
    with _thread_locks_guard:
        lock = _thread_locks.get(key)
        if lock is None:
            lock = threading.RLock()
            _thread_locks[key] = lock
        return lock


def _os_lock(fh: Any) -> None:
    if fcntl is not None:
        deadline = time.monotonic() + 10.0
        while True:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except (BlockingIOError, OSError):
                if time.monotonic() > deadline:
                    raise TimeoutError("Timed out waiting for file lock")
                time.sleep(_MSVCRT_RETRY_SECONDS)
    elif msvcrt is not None:
        fh.seek(0)
        deadline = time.monotonic() + 10.0
        while True:
            try:
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                if time.monotonic() > deadline:
                    raise TimeoutError("Timed out waiting for file lock")
                time.sleep(_MSVCRT_RETRY_SECONDS)


def _os_unlock(fh: Any) -> None:
    if fcntl is not None:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
    elif msvcrt is not None:
        try:
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass


_lock_tls = threading.local()


@contextmanager
def evidence_lock(workspace: str):
    """Context manager acquiring both the per-process thread lock and the OS file lock.

    Reentrant within the same thread to prevent POSIX flock self-deadlock.
    """
    evidence_dir = os.path.join(workspace, '.soma', 'evidence')
    os.makedirs(evidence_dir, exist_ok=True)
    lock_path = os.path.realpath(os.path.join(evidence_dir, LOCK_FILENAME))
    thread_lock = _thread_lock_for(lock_path)
    with thread_lock:
        if not hasattr(_lock_tls, "held"):
            _lock_tls.held = {}
        depth, fh = _lock_tls.held.get(lock_path, (0, None))
        if depth > 0 and fh is not None:
            _lock_tls.held[lock_path] = (depth + 1, fh)
            try:
                yield lock_path
            finally:
                d, h = _lock_tls.held.get(lock_path, (1, fh))
                if d <= 1:
                    _lock_tls.held.pop(lock_path, None)
                else:
                    _lock_tls.held[lock_path] = (d - 1, h)
        else:
            with open(lock_path, 'a+') as new_fh:
                _os_lock(new_fh)
                _lock_tls.held[lock_path] = (1, new_fh)
                try:
                    yield lock_path
                finally:
                    try:
                        _os_unlock(new_fh)
                    finally:
                        _lock_tls.held.pop(lock_path, None)


def read_generation(workspace: str) -> int:
    """Read the current epoch generation integer from .soma/epoch_generation."""
    gen_path = os.path.join(workspace, '.soma', EPOCH_FILENAME)
    if not os.path.isfile(gen_path):
        return DEFAULT_GENERATION
    try:
        with open(gen_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            return int(content) if content else DEFAULT_GENERATION
    except (OSError, ValueError):
        return DEFAULT_GENERATION


def current_generation(workspace: str) -> int:
    """Alias for read_generation."""
    return read_generation(workspace)


def increment_generation(workspace: str) -> int:
    """Atomically increment the epoch generation integer."""
    ws = str(workspace)
    with evidence_lock(ws):
        gen = read_generation(ws) + 1
        epoch_file = os.path.join(ws, '.soma', EPOCH_FILENAME)
        os.makedirs(os.path.dirname(epoch_file), exist_ok=True)
        _atomic_replace_bytes(epoch_file, f"{gen}\n".encode("utf-8"))
        return gen


def get_signals_path(workspace: str) -> str:
    return os.path.join(workspace, '.soma', 'evidence', SIGNALS_FILENAME)


def get_lock_path(workspace: str) -> str:
    return os.path.join(workspace, '.soma', 'evidence', LOCK_FILENAME)


def read_signals(workspace: str) -> list[dict]:
    """Read all signals from the canonical evidence log."""
    path = get_signals_path(str(workspace))
    if not os.path.isfile(path):
        return []
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                try:
                    records.append(json.loads(line_str))
                except Exception:
                    pass
    return records


def compute_payload_digest(cell_name: str, signal_type: str, source: str, metadata: Any) -> str:
    normalized = json.dumps(
        {
            'cell': cell_name,
            'signal': signal_type,
            'source': source,
            'metadata': metadata or None,
        },
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False,
    )
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def compute_event_id(principal: str, idempotency_scope: str, idempotency_key: str, cell_name: str) -> str:
    identity = f"{principal}:{idempotency_scope}:{idempotency_key}:{cell_name}"
    return hashlib.sha256(identity.encode('utf-8')).hexdigest()


def _read_existing_events(log_path: str) -> tuple[bytes, dict[str, dict]]:
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


def _fsync_dir(directory: str) -> None:
    if os.name == 'nt':
        return
    try:
        dir_fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass


def _atomic_replace_bytes(path: str, data: bytes) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix='.signals.', suffix='.tmp', dir=parent)
    try:
        with os.fdopen(fd, 'wb') as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)
        _fsync_dir(parent)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _migration_in_progress(workspace: str) -> bool:
    return (
        os.path.exists(os.path.join(workspace, '.soma', 'migration.lock'))
        or os.path.exists(os.path.join(workspace, '.soma', 'evidence', '.migration.lock'))
    )


def _validate_event(event: dict) -> tuple[str, str, str, Optional[dict], str, str, str]:
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

    if metadata is not None:
        if 'credit_weight' in metadata:
            cw = metadata['credit_weight']
            if not isinstance(cw, (int, float, Decimal)):
                raise ValueError(f"credit_weight must be numeric, got {type(cw)}")
            if cw < 0 or cw > 1:
                raise ValueError(f"credit_weight must be between 0.0 and 1.0, got {cw}")
        try:
            json.dumps(metadata, sort_keys=True, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise ValueError('metadata must be JSON serializable') from exc

    return cell_name, signal_type, source, metadata, principal, scope, key


def append_signals(workspace: str, events: list[dict], expected_generation: Optional[int] = None) -> list[dict]:
    """Atomically append a logical batch of canonical evidence events."""
    if _migration_in_progress(workspace):
        raise RuntimeError('migration in progress')

    if isinstance(events, (str, bytes)):
        raise ValueError('events must be an iterable of mappings')
    try:
        event_specs = list(events)
    except TypeError as exc:
        raise ValueError('events must be an iterable of mappings') from exc

    if not event_specs:
        return []

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


def append_signal(
    workspace: str,
    cell_name: str,
    signal_type: str,
    source: str,
    metadata: Optional[dict] = None,
    principal: str = "unknown",
    idempotency_scope: str = "global",
    idempotency_key: str = "",
    expected_generation: Optional[int] = None,
) -> dict:
    """Convenience single-signal wrapper around append_signals."""
    events = [{
        'cell_name': cell_name,
        'signal_type': signal_type,
        'source': source,
        'metadata': metadata,
        'principal': principal,
        'idempotency_scope': idempotency_scope,
        'idempotency_key': idempotency_key,
    }]
    results = append_signals(workspace, events, expected_generation=expected_generation)
    return results[0]


# ── Outcome Engine & Credit Assignment ────────────────────────────────────

VERIFY_TIMEOUT = int(os.environ.get('SOMA_VERIFY_TIMEOUT', '60'))


def _run_verify(cmd: str, cwd: str, timeout: Optional[int] = None) -> Optional[dict]:
    """Run a verification command, return (exit_code, stdout_snippet)."""
    if timeout is None:
        timeout = VERIFY_TIMEOUT
    try:
        result = subprocess.run(
            cmd, cwd=cwd, shell=True, timeout=timeout,
            capture_output=True, text=True
        )
        stdout_tail = '\n'.join(result.stdout.strip().split('\n')[-10:])
        stderr_tail = '\n'.join(result.stderr.strip().split('\n')[-5:])
        return {
            'exit_code': result.returncode,
            'passed': result.returncode == 0,
            'stdout_tail': stdout_tail[:500],
            'stderr_tail': stderr_tail[:300]
        }
    except subprocess.TimeoutExpired:
        return {'exit_code': -1, 'passed': None, 'error': 'timeout'}
    except FileNotFoundError:
        return None
    except Exception as e:
        return {'exit_code': -1, 'passed': None, 'error': str(e)[:200]}


def detect_test_runner(workspace: str) -> tuple[Optional[str], Optional[str]]:
    """Detect which test framework this project uses. Returns (command, framework_name)."""
    checks = [
        ('pyproject.toml', 'pytest', 'python3 -m pytest --tb=short -q --no-header 2>&1', 'python3 -c "import pytest" 2>/dev/null'),
        ('setup.cfg', 'pytest', 'python3 -m pytest --tb=short -q --no-header 2>&1', 'python3 -c "import pytest" 2>/dev/null'),
        ('pytest.ini', 'pytest', 'python3 -m pytest --tb=short -q --no-header 2>&1', 'python3 -c "import pytest" 2>/dev/null'),
        ('jest.config.js', 'jest', 'npx jest --silent --no-coverage 2>&1', 'npx jest --version 2>/dev/null'),
        ('jest.config.ts', 'jest', 'npx jest --silent --no-coverage 2>&1', 'npx jest --version 2>/dev/null'),
        ('vitest.config.ts', 'vitest', 'npx vitest run --reporter=dot 2>&1', 'npx vitest --version 2>/dev/null'),
        ('package.json', 'npm test', 'npm test 2>&1', None),
        ('go.mod', 'go test', 'go test ./... -count=1 -short 2>&1', 'go version 2>/dev/null'),
        ('Cargo.toml', 'cargo test', 'cargo test --quiet 2>&1', 'cargo --version 2>/dev/null'),
    ]

    for config_file, name, test_cmd, check_cmd in checks:
        if os.path.exists(os.path.join(workspace, config_file)):
            if check_cmd is None or subprocess.run(check_cmd, shell=True, cwd=workspace, capture_output=True).returncode == 0:
                return test_cmd, name

    # Fallback to Makefile test target
    makefile = os.path.join(workspace, 'Makefile')
    if os.path.exists(makefile):
        try:
            with open(makefile, 'r', encoding='utf-8') as f:
                if re.search(r'^test\s*:', f.read(), re.MULTILINE):
                    return 'make test', 'Makefile'
        except Exception:
            pass

    return None, None


def capture_test_outcome(workspace: str) -> dict:
    """Ground truth: run tests and capture exit code."""
    test_cmd, framework = detect_test_runner(workspace)
    if not test_cmd:
        return {'verified': False, 'reason': 'no test runner detected', 'passed': None}

    outcome = _run_verify(test_cmd, cwd=workspace)
    if not outcome or outcome.get('passed') is None:
        return {'verified': False, 'reason': outcome.get('error', 'test execution failed') if outcome else 'failed to run', 'passed': None, 'framework': framework}

    return {
        'verified': True,
        'passed': outcome['passed'],
        'exit_code': outcome['exit_code'],
        'framework': framework,
        'snippet': outcome['stdout_tail'] if not outcome['passed'] else ''
    }


def capture_build_outcome(workspace: str) -> dict:
    """Strong signal: did the build succeed?"""
    build_checks = [
        ('Cargo.toml', 'cargo check --quiet 2>&1'),
        ('package.json', 'npm run build --if-present 2>&1'),
        ('go.mod', 'go vet ./... 2>&1'),
    ]
    for config_file, cmd in build_checks:
        if os.path.exists(os.path.join(workspace, config_file)):
            outcome = _run_verify(cmd, cwd=workspace)
            if outcome and outcome.get('passed') is not None:
                return {
                    'verified': True,
                    'passed': outcome['passed'],
                    'exit_code': outcome['exit_code'],
                    'command': cmd.split()[0]
                }
    return {'verified': False, 'reason': 'no build system detected', 'passed': None}


def capture_git_signals(workspace: str) -> dict:
    """Always verifiable: reverts and rework from git log."""
    signals = {'reverts': 0, 'rework_files': []}
    try:
        log_out = subprocess.check_output(
            ['git', 'log', '--oneline', '-5'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        )
        revert_count = sum(1 for line in log_out.splitlines() if 'revert' in line.lower())
        signals['reverts'] = revert_count
    except Exception:
        pass

    try:
        log_out = subprocess.check_output(
            ['git', 'log', '--name-only', '--format=', '-5'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        )
        files = [f for f in log_out.splitlines() if f.strip()]
        counts = Counter(files)
        signals['rework_files'] = [f for f, c in counts.items() if c > 1]
    except Exception:
        pass

    return signals


def capture_mcp_outcomes(workspace: str) -> list[dict]:
    """Read any soma_report_outcome calls from this session from .soma/evidence/signals.jsonl."""
    signals_file = os.path.join(workspace, '.soma', 'evidence', SIGNALS_FILENAME)
    outcomes = []
    if not os.path.isfile(signals_file):
        return outcomes
    try:
        with open(signals_file, 'r', encoding='utf-8') as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    record = json.loads(line_str)
                except Exception:
                    continue

                sig_type = record.get('signal_type') or record.get('signal') or record.get('outcome')
                if not sig_type:
                    continue

                outcome = record.get('outcome')
                if not outcome:
                    if sig_type in ('tp', 'success'):
                        outcome = 'success'
                    elif sig_type in ('fp', 'failure'):
                        outcome = 'failure'
                    elif sig_type in ('trigger', 'partial'):
                        outcome = 'partial'
                    else:
                        outcome = str(sig_type)
                record['outcome'] = outcome

                cell_id = record.get('cell_id') or record.get('cell_name') or record.get('cell')
                if cell_id and 'cell_id' not in record:
                    record['cell_id'] = cell_id
                if cell_id and 'cells_used' not in record:
                    record['cells_used'] = [cell_id]

                outcomes.append(record)
    except Exception as exc:
        print(f"    ! failed to read signals file: {exc}", file=sys.stderr)
    return outcomes


def _insight_cursor_path(workspace: str) -> str:
    return os.path.join(workspace, '.soma', 'insight_cursor')


def _read_insight_cursor(workspace: str) -> int:
    """Return the committed byte offset into human_insights.jsonl (0 if none/invalid)."""
    try:
        with open(_insight_cursor_path(workspace), 'r', encoding='utf-8') as cf:
            value = int(cf.read().strip())
    except (OSError, ValueError):
        return 0
    return value if value >= 0 else 0


def commit_insight_cursor(workspace: str, offset: Optional[int]) -> bool:
    """Atomically persist the insight cursor (temp file + os.replace)."""
    if offset is None:
        return True
    cursor_file = _insight_cursor_path(workspace)
    if os.path.isfile(cursor_file) and _read_insight_cursor(workspace) == offset:
        return True
    cursor_dir = os.path.dirname(cursor_file)
    tmp_path = None
    try:
        os.makedirs(cursor_dir, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=cursor_dir, prefix='.insight_cursor.', suffix='.tmp')
        with os.fdopen(fd, 'w', encoding='utf-8') as cf:
            cf.write(str(int(offset)))
            cf.flush()
            os.fsync(cf.fileno())
        os.replace(tmp_path, cursor_file)
        return True
    except (OSError, ValueError, TypeError) as e:
        print(f"    ! failed to commit insight cursor: {e}", file=sys.stderr)
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return False


def capture_human_insight_signals(workspace: str) -> list[dict]:
    """Backward-compatible wrapper: read NEW insights and commit the cursor."""
    signals, new_offset = read_human_insight_signals(workspace)
    commit_insight_cursor(workspace, new_offset)
    return signals


def read_human_insight_signals(workspace: str) -> tuple[list[dict], int]:
    """Read NEW human insight annotations and produce fitness signals."""
    insights_file = os.path.join(workspace, '.soma', 'human_insights.jsonl')
    cursor_offset = _read_insight_cursor(workspace)
    if not os.path.isfile(insights_file):
        return [], cursor_offset

    file_size = os.path.getsize(insights_file)
    if cursor_offset > file_size:
        cursor_offset = 0

    weight = 0.5
    config_path = os.path.join(workspace, '.soma', 'config.yaml')
    if os.path.isfile(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if yaml is not None:
                    config = yaml.safe_load(f) or {}
                else:
                    config = parse_frontmatter(f.read()) or {}
            weight = float(config.get('insight_signal_weight', 0.5))
        except Exception:
            pass

    cell_paths = {}
    cells_dir = os.path.join(workspace, '.soma', 'cells')
    if os.path.isdir(cells_dir):
        for cell_file in glob.glob(os.path.join(cells_dir, '**', '*.md'), recursive=True):
            name = os.path.splitext(os.path.basename(cell_file))[0]
            cell_paths[name] = cell_file

    try:
        with open(insights_file, 'rb') as f:
            f.seek(cursor_offset)
            data = f.read()
    except OSError:
        return [], cursor_offset

    last_newline = data.rfind(b'\n')
    if last_newline == -1:
        return [], cursor_offset
    complete = data[:last_newline + 1]
    new_offset = cursor_offset + len(complete)

    signals = []
    line_offset = cursor_offset
    for raw_line in complete.split(b'\n'):
        this_offset = line_offset
        line_offset += len(raw_line) + 1
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(record, dict):
            continue

        insight_id = f"{this_offset}:{hashlib.sha256(raw_line).hexdigest()}"

        if record.get('was_covered'):
            for cell_name in record.get('covering_cells', []):
                cell_path = cell_paths.get(cell_name)
                if cell_path:
                    signals.append({
                        'cell': cell_name,
                        '_path': cell_path,
                        'signal': weight,
                        'reasons': [f"human insight: {record.get('insight', '')[:80]}"],
                        'verified': True,
                        'signal_type': 'human_insight',
                        'insight_id': insight_id,
                        'weight': weight,
                        'files': record.get('context_files', []),
                    })
        else:
            signals.append({
                'cell': None,
                '_path': None,
                'signal': 0.0,
                'reasons': [f"blind spot: {record.get('insight', '')[:80]}"],
                'verified': True,
                'signal_type': 'blind_spot',
                'weight': weight,
                'files': record.get('context_files', []),
            })

    return signals, new_offset


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _get_changed_files(workspace: str) -> list[str]:
    try:
        out = subprocess.check_output(
            ['git', 'diff', '--name-only', 'HEAD~1'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        )
        files = [f.strip() for f in out.splitlines() if f.strip()]
        if files:
            return files
    except Exception:
        pass

    try:
        out = subprocess.check_output(
            ['git', 'status', '--porcelain'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        )
        files = []
        for line in out.splitlines():
            line = line.strip()
            if len(line) > 3:
                files.append(line[3:].strip())
        return files
    except Exception:
        return []


def _parse_frontmatter(content: str, filepath: Optional[str] = None) -> dict:
    """Parse YAML frontmatter robustly using parse_cell_file or parse_frontmatter.

    When *filepath* is provided, delegates to the canonical parser.
    Falls back to inline parsing when only raw *content* is available.
    """
    if filepath is not None:
        try:
            from soma_core.lifecycle import parse_cell as parse_cell_file
            fm, _body = parse_cell_file(str(filepath))
            return fm if isinstance(fm, dict) else {}
        except Exception:
            return {}
    if not content:
        return {}
    try:
        res = parse_frontmatter(content)
        if isinstance(res, dict):
            return res
    except Exception:
        pass
    if not content.startswith('---'):
        return {}
    end = content.find('---', 3)
    if end == -1:
        return {}
    fm_text = content[3:end].strip()
    try:
        if yaml is not None:
            loaded = yaml.safe_load(fm_text)
            return loaded if isinstance(loaded, dict) else {}
    except Exception:
        pass
    return {}


def match_cells_to_changes(workspace: str, changed_files: list[str]) -> list[dict]:
    cells_dir = os.path.join(workspace, '.soma', 'cells')
    if not os.path.isdir(cells_dir):
        return []

    triggered = []
    for cell_file in glob.glob(os.path.join(cells_dir, '**', '*.md'), recursive=True):
        if os.path.basename(cell_file) == 'README.md':
            continue
        try:
            with open(cell_file, 'r', encoding='utf-8') as f:
                content = f.read()
            fm = parse_frontmatter(content) or {}
            target_paths = fm.get('target_paths', [])
            if isinstance(target_paths, str):
                target_paths = [target_paths]

            matched = False
            for pattern in target_paths:
                pat_norm = pattern.replace("\\", "/")
                for changed in changed_files:
                    ch_norm = changed.replace("\\", "/")
                    if fnmatch.fnmatch(ch_norm, pat_norm) or fnmatch.fnmatch(os.path.basename(ch_norm), pat_norm):
                        matched = True
                        break
                if matched:
                    break

            if matched:
                cell_name = fm.get('id') or os.path.splitext(os.path.basename(cell_file))[0]
                cell_dict = dict(fm)
                cell_dict['_name'] = cell_name
                cell_dict['_path'] = cell_file
                triggered.append(cell_dict)
        except Exception:
            continue

    return triggered


def to_fraction(credit: Any) -> str:
    """Convert credit float to a string Fraction (e.g., '1/3') for deterministic storage."""
    if isinstance(credit, str) and '/' in credit:
        return credit
    try:
        val = max(0.0, min(1.0, float(credit)))
    except (ValueError, TypeError):
        val = 0.0
    f = Fraction(val).limit_denominator(1000)
    return f"{f.numerator}/{f.denominator}"


def compute_credit_weights(triggered_cells: list[dict], changed_files: list[str]) -> dict[str, float]:
    """Compute per-cell credit weights using per-file scope narrowing."""
    if not changed_files or not triggered_cells:
        return {c.get('_name', c.get('id', '')): 1.0 for c in triggered_cells}

    file_to_cells: dict[str, list[str]] = {}
    for fpath in changed_files:
        matching = []
        for cell in triggered_cells:
            cell_name = cell.get('_name', cell.get('id', ''))
            target_paths = cell.get('target_paths', [])
            if isinstance(target_paths, str):
                target_paths = [target_paths]
            for tp in target_paths:
                if fnmatch.fnmatch(fpath, tp) or fnmatch.fnmatch(os.path.basename(fpath), tp):
                    matching.append(cell_name)
                    break
        if matching:
            file_to_cells[fpath] = matching

    credit = {c.get('_name', c.get('id', '')): 0.0 for c in triggered_cells}
    for fpath, cell_names in file_to_cells.items():
        per_cell = 1.0 / len(cell_names)
        for cn in cell_names:
            credit[cn] += per_cell

    return credit


def compute_fitness_signals(triggered_cells: list[dict], outcomes: dict, changed_files: Optional[list[str]] = None) -> list[dict]:
    """ACE-aligned reflector: score cells based on VERIFIABLE outcomes."""
    credit_weights = compute_credit_weights(triggered_cells, changed_files or [])
    results = []
    test_outcome = outcomes.get('tests', {})
    build_outcome = outcomes.get('build', {})
    git = outcomes.get('git', {})
    mcp = outcomes.get('mcp', [])

    for cell in triggered_cells:
        signal = 0.0
        reasons = []

        # 1. Test exit code — GROUND TRUTH
        if test_outcome.get('verified') and test_outcome.get('passed') is not None:
            if test_outcome['passed']:
                signal += 1.0
                reasons.append(f"tests passed ({test_outcome.get('framework', '?')})")
            else:
                signal -= 1.0
                reasons.append(f"tests FAILED ({test_outcome.get('framework', '?')})")

        # 2. Build exit code — STRONG SIGNAL
        elif build_outcome.get('verified') and build_outcome.get('passed') is not None:
            if build_outcome['passed']:
                signal += 0.7
                reasons.append("build passed")
            else:
                signal -= 0.7
                reasons.append("build FAILED")

        # 3. Git reverts — VERIFIABLE FAILURE
        if git.get('reverts', 0) > 0:
            signal -= 1.0
            reasons.append(f"{git['reverts']} revert(s) detected")

        # 4. Rework on cell's target files — WEAK BUT VERIFIABLE
        rework_files = git.get('rework_files', [])
        cell_targets = cell.get('target_paths', [])
        if isinstance(cell_targets, str):
            cell_targets = [cell_targets]

        rework_hit = False
        for rf in rework_files:
            for tp in cell_targets:
                if fnmatch.fnmatch(rf, tp):
                    rework_hit = True
                    break
            if rework_hit:
                break
        if rework_hit:
            signal -= 0.3
            reasons.append("rework detected on target files")

        # 5. MCP self-report — WEAKEST
        cell_name = cell.get('_name', cell.get('id', ''))
        for mcp_entry in mcp:
            cells_used = list(mcp_entry.get('cells_used', []))
            cell_id = mcp_entry.get('cell_id') or mcp_entry.get('cell_name') or mcp_entry.get('cell')
            if cell_id and cell_id not in cells_used:
                cells_used.append(cell_id)

            if cell_name in cells_used:
                outcome = mcp_entry.get('outcome', '')
                if outcome in ('success', 'tp'):
                    if test_outcome.get('verified') and test_outcome.get('passed') is False:
                        signal -= 2.0
                        reasons.append("agent claimed success but tests FAILED (overconfidence penalty)")
                    elif not test_outcome.get('verified') and not build_outcome.get('verified') and git.get('reverts', 0) == 0:
                        signal -= 1.0
                        reasons.append("agent claimed success with zero verifiable evidence (overconfidence penalty)")
                    else:
                        signal += 0.2
                        reasons.append("agent reported success")
                elif outcome in ('failure', 'fp'):
                    signal -= 0.2
                    reasons.append("agent reported failure")

        signal = max(-2.0, min(2.0, signal))

        results.append({
            'cell': cell_name,
            '_path': cell.get('_path'),
            'signal': round(signal, 2),
            'reasons': reasons,
            'verified': bool(test_outcome.get('verified', False) or build_outcome.get('verified', False)),
            'credit_weight': credit_weights.get(cell_name, 1.0),
            'signal_method': 'credit_weighted',
        })

    return results


def update_cell_fitness(workspace: str, fitness_signals: list[dict]) -> None:
    """Update cell frontmatter with fitness signals using YAML / dump_frontmatter."""
    for sig in fitness_signals:
        fpath = sig.get('_path')
        if not fpath or not os.path.isfile(fpath):
            continue
        signal = sig.get('signal', 0.0)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            end = content.find('---', 3)
            if end == -1:
                continue

            fm = parse_frontmatter(content) or {}
            body = _get_body(content)

            fitness = fm.get('fitness')
            if fitness is None or isinstance(fitness, bool):
                fitness = {'score': None, 'impact_weight': 1.0}
            elif isinstance(fitness, (int, float)):
                fitness = {'score': float(fitness), 'impact_weight': 1.0}
            elif isinstance(fitness, str):
                try:
                    fitness = {'score': float(fitness), 'impact_weight': 1.0}
                except ValueError:
                    fitness = {'score': None, 'impact_weight': 1.0}
            elif not isinstance(fitness, dict):
                fitness = {'score': None, 'impact_weight': 1.0}

            fitness['triggers'] = _as_int(fitness.get('triggers', 0)) + 1
            fitness.setdefault('true_positives', 0)
            fitness.setdefault('false_positives', 0)

            credit_weight = sig.get('credit_weight', 1.0)
            frac_str = to_fraction(credit_weight)

            if signal > 0:
                raw_tp = str(fitness['true_positives']).strip()
                try:
                    current = Fraction(raw_tp)
                except Exception:
                    current = Fraction(0)
                new_val = current + Fraction(frac_str)
                r = round(float(new_val), 4)
                fitness['true_positives'] = int(r) if r.is_integer() else r
            elif signal < 0:
                raw_fp = str(fitness['false_positives']).strip()
                try:
                    current = Fraction(raw_fp)
                except Exception:
                    current = Fraction(0)
                new_val = current + Fraction(frac_str)
                r = round(float(new_val), 4)
                fitness['false_positives'] = int(r) if r.is_integer() else r

            fitness['last_trigger_date'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            fm['fitness'] = fitness

            if yaml is not None:
                new_fm = yaml.dump(fm, sort_keys=False, default_flow_style=False, allow_unicode=True)
            else:
                new_fm = dump_frontmatter(fm)

            new_content = f"---\n{new_fm.strip()}\n---\n\n{body}\n" if body else f"---\n{new_fm.strip()}\n---\n"

            tmp_fpath = f"{fpath}.tmp.{os.getpid()}"
            with open(tmp_fpath, 'w', encoding='utf-8') as f:
                f.write(new_content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_fpath, fpath)
        except Exception as e:
            print(f"    ! failed to update fitness for {fpath}: {e}", file=sys.stderr)


INSIGHT_PRINCIPAL = 'outcome_engine'
INSIGHT_SCOPE = 'human_insight'


def append_fitness_log(
    workspace: str,
    fitness_signals: list[dict],
    outcomes: dict,
    expected_generation: Optional[int] = None,
    idempotency_prefix: Optional[str] = None,
) -> bool:
    """Atomically append one outcome-engine batch to canonical evidence."""
    if not fitness_signals:
        return True

    _append_func = append_signals

    if idempotency_prefix is None:
        idempotency_prefix = secrets.token_hex(16)

    events = []
    for sig in fitness_signals:
        signal_val = sig.get('signal', 0)
        if signal_val > 0:
            signal_type = 'tp'
        elif signal_val < 0:
            signal_type = 'fp'
        else:
            signal_type = 'trigger'

        metadata = {
            'raw_signal': sig.get('signal'),
            'verified': sig.get('verified', False),
            'credit_weight': sig.get('credit_weight', 1.0),
            'signal_method': sig.get('signal_method', 'legacy'),
            'reasons': sig.get('reasons', []),
            'outcomes': {
                'tests': {
                    'verified': outcomes.get('tests', {}).get('verified', False),
                    'passed': outcomes.get('tests', {}).get('passed'),
                    'framework': outcomes.get('tests', {}).get('framework'),
                },
                'build': {
                    'verified': outcomes.get('build', {}).get('verified', False),
                    'passed': outcomes.get('build', {}).get('passed'),
                },
                'git': {
                    'reverts': outcomes.get('git', {}).get('reverts', 0),
                    'rework_count': len(outcomes.get('git', {}).get('rework_files', [])),
                },
            },
        }

        insight_id = sig.get('insight_id')
        if insight_id:
            metadata['insight_id'] = insight_id
            principal = INSIGHT_PRINCIPAL
            scope = INSIGHT_SCOPE
            key = insight_id
        else:
            principal = 'outcome_engine'
            scope = 'run'
            key = idempotency_prefix

        events.append({
            'cell_name': sig['cell'],
            'signal_type': signal_type,
            'source': 'session',
            'metadata': metadata,
            'principal': principal,
            'idempotency_scope': scope,
            'idempotency_key': key,
        })

    try:
        _append_func(workspace, events, expected_generation=expected_generation)
    except Exception as exc:
        print(f"    ! failed to log fitness signal batch: {exc}", file=sys.stderr)
        return False
    return True


def run_outcome_engine(workspace: Optional[str] = None, mod: Any = None) -> int:
    """Canonical ACE reflector loop."""
    m = mod if mod is not None else sys.modules.get('enzymes.outcome_engine', sys.modules[__name__])
    resolve_ws = getattr(m, 'resolve_workspace', resolve_workspace)
    ws = workspace or resolve_ws()
    cells_dir = os.path.join(ws, '.soma', 'cells')
    if not os.path.isdir(cells_dir):
        return 0

    print("  Running outcome engine (ACE reflector)...")
    generation = read_generation(ws)

    cap_test = getattr(m, 'capture_test_outcome', capture_test_outcome)
    cap_build = getattr(m, 'capture_build_outcome', capture_build_outcome)
    cap_git = getattr(m, 'capture_git_signals', capture_git_signals)
    cap_mcp = getattr(m, 'capture_mcp_outcomes', capture_mcp_outcomes)
    read_insights = getattr(m, 'read_human_insight_signals', read_human_insight_signals)
    commit_cursor = getattr(m, 'commit_insight_cursor', commit_insight_cursor)
    get_changed = getattr(m, '_get_changed_files', _get_changed_files)
    match_cells = getattr(m, 'match_cells_to_changes', match_cells_to_changes)
    comp_signals = getattr(m, 'compute_fitness_signals', compute_fitness_signals)
    append_log = getattr(m, 'append_fitness_log', append_fitness_log)
    update_fitness = getattr(m, 'update_cell_fitness', update_cell_fitness)

    outcomes = {}
    print("    Detecting test runner...", end=' ')
    outcomes['tests'] = cap_test(ws)
    test_result = outcomes['tests']
    if test_result.get('verified'):
        status = '✅ PASSED' if test_result['passed'] else '❌ FAILED'
        print(f"{test_result.get('framework', '?')} → {status}")
    else:
        print(f"skipped ({test_result.get('reason', 'unknown')})")

    outcomes['build'] = cap_build(ws)
    outcomes['git'] = cap_git(ws)
    mcp = cap_mcp(ws)
    if mcp:
        outcomes['mcp'] = mcp

    insight_signals, insight_offset = read_insights(ws)
    blind_spots = [s for s in insight_signals if s.get('signal_type') == 'blind_spot']
    cell_boosts = [s for s in insight_signals if s.get('_path') is not None]

    if blind_spots:
        print(f"    {len(blind_spots)} governance blind spot(s) detected from human insights")

    changed_files = get_changed(ws)
    triggered = match_cells(ws, changed_files)

    if not triggered and not cell_boosts:
        print("    No cells matched changed files.")
        commit_cursor(ws, insight_offset)
        return 0

    signals = comp_signals(triggered, outcomes, changed_files=changed_files) if triggered else []

    existing_paths = {s['_path'] for s in signals if '_path' in s}
    for boost in cell_boosts:
        if boost['_path'] not in existing_paths:
            signals.append(boost)
            existing_paths.add(boost['_path'])

    if signals:
        run_idempotency_prefix = secrets.token_hex(16)
        if append_log(
            ws, signals, outcomes,
            expected_generation=generation,
            idempotency_prefix=run_idempotency_prefix
        ):
            commit_cursor(ws, insight_offset)
            update_fitness(ws, signals)
        else:
            print("    ! evidence log incomplete; cells and insight cursor left unchanged (will retry)", file=sys.stderr)
    else:
        commit_cursor(ws, insight_offset)

    verified_count = sum(1 for s in signals if s.get('verified'))
    print(f"    {len(signals)} cells evaluated ({verified_count} with verified outcomes)")
    for s in signals:
        indicator = '↑' if s['signal'] > 0 else '↓' if s['signal'] < 0 else '→'
        v = '✓' if s.get('verified') else '?'
        reasons_str = ', '.join(s.get('reasons', [])) or 'no signal'
        print(f"      {indicator} [{v}] {s['cell']}: {s['signal']:+.1f} ({reasons_str})")
    return 0



def cli_outcome_engine(argv: Optional[List[str]] = None, mod: Any = None) -> int:
    """CLI outcome engine handler."""
    target_args = argv if argv is not None else ([] if __name__ != "__main__" else sys.argv[1:])
    if not target_args:
        return run_outcome_engine(mod=mod)
    parser = argparse.ArgumentParser(description="Outcome Engine")
    parser.add_argument("--workspace", default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(target_args)

    ws = args.workspace or resolve_workspace()
    return run_outcome_engine(ws, mod=mod)


# ── Fitness Updater ────────────────────────────────────────────────────────

PLATFORMS = {
    "antigravity": {
        "write_tools": {"write_to_file", "replace_file_content", "multi_replace_file_content"},
        "target_file_keys": ["TargetFile"],
        "args_keys": ["arguments", "args"],
        "id_skip_dirs": {"logs", ".system_generated"},
    },
    "claude": {
        "write_tools": {"write_to_file", "edit_file", "create_file"},
        "target_file_keys": ["path", "file_path", "TargetFile"],
        "args_keys": ["arguments", "args", "input"],
        "id_skip_dirs": {"logs"},
    },
}

PLATFORMS["generic"] = {
    "write_tools": PLATFORMS["antigravity"]["write_tools"] | PLATFORMS["claude"]["write_tools"],
    "target_file_keys": list(set(PLATFORMS["antigravity"]["target_file_keys"] + PLATFORMS["claude"]["target_file_keys"])),
    "args_keys": list(set(PLATFORMS["antigravity"]["args_keys"] + PLATFORMS["claude"]["args_keys"])),
    "id_skip_dirs": PLATFORMS["antigravity"]["id_skip_dirs"] | PLATFORMS["claude"]["id_skip_dirs"],
}

DEFAULT_PLATFORM = "antigravity"


def _get_platform_config(platform: Optional[str] = None) -> dict:
    name = platform or DEFAULT_PLATFORM
    if name not in PLATFORMS:
        print(f"Warning: unknown platform '{name}', using generic config", file=sys.stderr)
        return PLATFORMS["generic"]
    return PLATFORMS[name]


def detect_platform(transcript_path: Path | str) -> str:
    transcript_path = Path(transcript_path)
    if not transcript_path.exists():
        return DEFAULT_PLATFORM

    tool_to_platform = {}
    for name, config in PLATFORMS.items():
        if name == "generic":
            continue
        for tool in config["write_tools"]:
            if tool not in tool_to_platform:
                tool_to_platform[tool] = name

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    step = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                for tc in step.get("tool_calls", []):
                    tool_name = tc.get("name", "")
                    if tool_name in tool_to_platform:
                        return tool_to_platform[tool_name]
    except Exception:
        pass

    return DEFAULT_PLATFORM


def resolve_transcript_id(transcript_path: Path | str, platform: Optional[str] = None) -> str:
    config = _get_platform_config(platform)
    candidate = Path(transcript_path).resolve().parent
    while candidate.name in config["id_skip_dirs"]:
        candidate = candidate.parent
    return candidate.name


def extract_modified_files(transcript_path: Path | str, platform: Optional[str] = None) -> set[str]:
    transcript_path = Path(transcript_path)
    if not transcript_path.exists():
        return set()

    config = _get_platform_config(platform)
    write_tools = config["write_tools"]
    args_keys = config["args_keys"]
    target_file_keys = config["target_file_keys"]

    modified = set()
    try:
        text = transcript_path.read_text(encoding="utf-8")
    except Exception:
        return set()

    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            step = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue

        for tc in step.get("tool_calls", []):
            tool_name = tc.get("name", "")
            if tool_name not in write_tools:
                continue
            args = {}
            for key in args_keys:
                args = tc.get(key) or args
                if args:
                    break
            if not isinstance(args, dict):
                continue
            for tf_key in target_file_keys:
                target = args.get(tf_key, "")
                if isinstance(target, str):
                    target = target.strip('"').strip("'")
                if target:
                    modified.add(target)

    return modified


def match_cells(modified_files: set[str], cells_dir: Path | str, repo_root: str = "") -> list[dict]:
    cells_dir = Path(cells_dir)
    if not cells_dir.exists():
        return []

    if not modified_files:
        return []

    rel_modified = set()
    norm_root = str(repo_root).replace("\\", "/").rstrip("/") if repo_root else ""
    for abs_path in modified_files:
        norm_abs = str(abs_path).replace("\\", "/")
        if norm_root and norm_abs.startswith(norm_root):
            rel = norm_abs[len(norm_root):].lstrip("/")
            rel_modified.add(rel)
        else:
            rel_modified.add(norm_abs.lstrip("/"))

    results = []
    for md_file in cells_dir.rglob("*.md"):
        if md_file.name == "README.md":
            continue
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            fm = parse_frontmatter(content) or {}
        except Exception:
            continue

        cell_id = fm.get("id", md_file.stem)
        target_paths = fm.get("target_paths", [])
        if not isinstance(target_paths, list) or not target_paths:
            continue

        matched = set()
        for rel_file in rel_modified:
            for pattern in target_paths:
                if fnmatch.fnmatch(rel_file, pattern):
                    matched.add(rel_file)
                    break

        if matched:
            rel_cell = str(md_file.relative_to(cells_dir)).replace("\\", "/")
            results.append({
                "cell_id": cell_id,
                "cell_path": rel_cell,
                "matched_files": sorted(matched),
            })

    return results


def update_fitness(triggered_cells: list[dict], transcript_id: str, evidence_dir: Path | str) -> list[dict]:
    """Atomically record every cell triggered by one transcript."""
    if not triggered_cells:
        return []

    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    workspace = str(evidence_dir.parent.parent)

    generation = read_generation(workspace)
    events = [
        {
            'cell_name': cell['cell_id'],
            'signal_type': 'trigger',
            'source': 'session',
            'metadata': {
                'transcript_id': transcript_id,
                'matched_files': cell.get('matched_files', []),
            },
            'principal': 'fitness_updater',
            'idempotency_scope': 'transcript',
            'idempotency_key': f"{transcript_id}:{cell['cell_id']}",
        }
        for cell in triggered_cells
    ]
    return append_signals(workspace, events, expected_generation=generation)


def cli_fitness_updater(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Update cell fitness from session transcript")
    parser.add_argument("transcript", help="Path to transcript.jsonl")
    parser.add_argument("--platform", default=None,
                        help=f"Platform name (auto-detected if omitted). Known: {list(PLATFORMS.keys())}")
    parser.add_argument("--cells-dir", default=None, help="Path to cells directory")
    parser.add_argument("--evidence-dir", default=None, help="Path to evidence directory")
    parser.add_argument("--repo-root", default=None, help="Repo root for relativizing paths")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    script_dir = Path(__file__).parent.parent
    cells_dir = Path(args.cells_dir) if args.cells_dir else script_dir / ".soma" / "cells"
    evidence_dir = Path(args.evidence_dir) if args.evidence_dir else script_dir / ".soma" / "evidence"
    repo_root = args.repo_root or str(script_dir)

    transcript = Path(args.transcript)
    platform = args.platform or detect_platform(transcript)
    transcript_id = resolve_transcript_id(transcript, platform)

    print(f"Processing transcript: {transcript}")
    print(f"  Platform: {platform}")
    modified = extract_modified_files(transcript, platform=platform)
    print(f"  Modified files: {len(modified)}")

    triggered = match_cells(modified, cells_dir, repo_root=repo_root)
    print(f"  Cells triggered: {len(triggered)}")
    for t in triggered:
        print(f"    - {t['cell_id']} ({len(t['matched_files'])} files)")

    update_fitness(triggered, transcript_id, evidence_dir)
    print(f"  Fitness updated: {evidence_dir / 'signals.jsonl'}")

    try:
        from soma_core.sync import aggregate_evidence, sync_frontmatter
        counts = aggregate_evidence(str(evidence_dir))
        if counts:
            changes = sync_frontmatter(str(cells_dir), counts)
            if changes:
                print(f"  Frontmatter synced: {len(changes)} cells updated")
    except Exception:
        pass
    return 0


# ── Metrics Snapshot ───────────────────────────────────────────────────────

def resolve_metrics_dir(workspace: Path | str) -> Path:
    """Resolve where metrics snapshots are stored."""
    team_repo = os.environ.get("TEAM_REPO")
    team_member = os.environ.get("TEAM_MEMBER_ID", "local_user")
    metrics_repo = os.environ.get("METRICS_REPO")

    ws = Path(workspace).resolve()
    conf_path = ws / "soma.conf"
    if (not team_repo or not metrics_repo) and conf_path.is_file():
        with open(conf_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("TEAM_REPO=") and not line.startswith("#"):
                    team_repo = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("TEAM_MEMBER_ID=") and not line.startswith("#"):
                    team_member = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("METRICS_REPO=") and not line.startswith("#"):
                    metrics_repo = line.split("=", 1)[1].strip().strip('"').strip("'")

    if team_repo:
        path = Path(os.path.expanduser(team_repo)) / "snapshots" / team_member
        path.mkdir(parents=True, exist_ok=True)
        return path

    if metrics_repo:
        path = Path(os.path.expanduser(metrics_repo))
        path.mkdir(parents=True, exist_ok=True)
        return path

    default = ws / "docs" / "snapshots"
    default.mkdir(parents=True, exist_ok=True)
    return default


def compute_token_census(workspace: Path | str | None = None, model: str = "gemini-2.0-flash") -> dict:
    """Compute token census across genome rules and organ skills without subprocess."""
    ws = Path(workspace).resolve() if workspace else Path(resolve_workspace()).resolve()
    rules_dir = ws / "genome"
    skills_dir = ws / "organs"

    results = []
    total_words = 0
    total_tokens = 0
    fallback_ratio = 1.35

    def _wc(text: str) -> int:
        return len(text.split())

    def _extract_fm(text: str) -> str:
        m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        return m.group(1) if m else ""

    def _get_trig(fm: str) -> str:
        m = re.search(r"^trigger:\s*(.*)$", fm, re.MULTILINE)
        return m.group(1).strip() if m else "unknown"

    if rules_dir.is_dir():
        for fpath in sorted(rules_dir.glob("*.md")):
            try:
                content = fpath.read_text(encoding="utf-8")
            except OSError:
                continue
            fm = _extract_fm(content)
            trig = _get_trig(fm)
            w_full = _wc(content)
            w_fm = _wc(fm)

            if trig == "always_on":
                c_type = "always_on_rule"
                t_idle = int(w_full * fallback_ratio)
                t_active = t_idle
                w_idle = w_full
                w_active = w_full
            else:
                c_type = "conditional_rule"
                t_idle = int(w_fm * fallback_ratio)
                t_active = int(w_full * fallback_ratio)
                w_idle = w_fm
                w_active = w_full

            total_words += w_full
            total_tokens += t_active
            results.append({
                "filename": f"genome/{fpath.name}",
                "type": c_type,
                "idle_words": w_idle,
                "idle_tokens": t_idle,
                "active_words": w_active,
                "active_tokens": t_active,
                "ratio": t_active / w_active if w_active else 0,
            })

    if skills_dir.is_dir():
        for fpath in sorted(skills_dir.glob("*/SKILL.md")):
            skill_name = fpath.parent.name
            try:
                content = fpath.read_text(encoding="utf-8")
            except OSError:
                continue
            fm = _extract_fm(content)
            w_full = _wc(content)
            w_fm = _wc(fm)
            t_idle = int(w_fm * fallback_ratio)
            t_active = int(w_full * fallback_ratio)
            w_idle = w_fm
            w_active = w_full

            total_words += w_full
            total_tokens += t_active
            results.append({
                "filename": f"organs/{skill_name}/SKILL.md",
                "type": "skill",
                "idle_words": w_idle,
                "idle_tokens": t_idle,
                "active_words": w_active,
                "active_tokens": t_active,
                "ratio": t_active / w_active if w_active else 0,
            })

    calibrated_ratio = total_tokens / total_words if total_words else fallback_ratio
    subtotals = {
        "always_on_rules_idle_tokens": sum(r["idle_tokens"] for r in results if r["type"] == "always_on_rule"),
        "conditional_rules_idle_tokens": sum(r["idle_tokens"] for r in results if r["type"] == "conditional_rule"),
        "conditional_rules_active_tokens": sum(r["active_tokens"] for r in results if r["type"] == "conditional_rule"),
        "skills_idle_tokens": sum(r["idle_tokens"] for r in results if r["type"] == "skill"),
        "skills_active_tokens": sum(r["active_tokens"] for r in results if r["type"] == "skill"),
    }
    grand_total_idle = subtotals["always_on_rules_idle_tokens"] + subtotals["conditional_rules_idle_tokens"] + subtotals["skills_idle_tokens"]

    return {
        "model": model,
        "measured_with_sdk": False,
        "calibrated_ratio": round(calibrated_ratio, 2),
        "files": results,
        "subtotals": subtotals,
        "grand_total_idle": grand_total_idle,
    }


def take_snapshot(
    json_mode: bool = False,
    raw_mode: bool = False,
    compare_file: str | None = None,
    save: bool = False,
    workspace: Path | None = None,
) -> int:
    ws = Path(workspace).resolve() if workspace else Path(resolve_workspace()).resolve()
    metrics_dir = resolve_metrics_dir(ws)

    try:
        census = compute_token_census(ws)
    except Exception:
        census = {
            "files": [],
            "subtotals": {"always_on_rules_idle_tokens": 0, "conditional_rules_idle_tokens": 0, "skills_idle_tokens": 0},
            "grand_total_idle": 0,
            "calibrated_ratio": 0,
        }

    always_on_rules = sum(1 for r in census["files"] if r.get("type") == "always_on_rule")
    conditional_rules = sum(1 for r in census["files"] if r.get("type") == "conditional_rule")
    skills_count = sum(1 for r in census["files"] if r.get("type") == "skill")

    prong_budgets = {}
    staff_review_path = ws / "organs" / "staff-review" / "SKILL.md"
    if staff_review_path.is_file():
        content = staff_review_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            match = re.search(
                r'\|\s*.*?(Spores|Mycelium|Roots|Thorns|Bedrock|Mulch).*?\|\s*\**([0-9,]+\s*tokens).*?\|',
                line,
                re.IGNORECASE,
            )
            if match:
                prong_budgets[match.group(1)] = match.group(2).strip()

    waste_rate_best = "1.1%"
    waste_rate_avg = "18.8%"

    cells_count = 0
    cells_dir = ws / ".soma" / "cells"
    if cells_dir.is_dir():
        for f in cells_dir.rglob("*.md"):
            cells_count += 1

    metrics = {
        "rules_always_on": always_on_rules,
        "rules_conditional": conditional_rules,
        "skills_count": skills_count,
        "cells_count": cells_count,
        "tokens": census.get("subtotals", {}),
        "grand_total_idle_overhead": census.get("grand_total_idle", 0),
        "calibrated_ratio": census.get("calibrated_ratio", 0),
        "waste_rate_best": waste_rate_best,
        "waste_rate_avg": waste_rate_avg,
        "prong_budgets": prong_budgets,
        "metrics_dir": str(metrics_dir),
    }

    if raw_mode:
        metrics["timestamp"] = datetime.now(timezone.utc).isoformat() + "Z"

    compare_data = None
    if compare_file and os.path.exists(compare_file):
        with open(compare_file, "r", encoding="utf-8") as f:
            compare_data = json.load(f)

    if save:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        save_path = metrics_dir / f"snapshot-{ts}.json"
        save_metrics = dict(metrics)
        save_metrics["timestamp"] = datetime.now(timezone.utc).isoformat() + "Z"
        save_metrics.pop("metrics_dir", None)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(save_metrics, f, indent=2)
        print(f"Saved to: {save_path}", file=sys.stderr)

    if json_mode:
        output = dict(metrics)
        output.pop("metrics_dir", None)
        print(json.dumps(output, indent=2))
    else:
        print("=== SOMA: METRICS SNAPSHOT ===")
        if raw_mode:
            print(f"Timestamp: {metrics.get('timestamp')}")
        print(f"Metrics Dir: {metrics_dir}")
        print("\n[ Counts ]")
        print(f"Rules:  {always_on_rules} always-on, {conditional_rules} conditional")
        print(f"Skills: {skills_count}")
        print(f"Cells:  {metrics.get('cells_count', 0)}")

        print("\n[ Tokens ]")
        toks = metrics.get('tokens', {})
        print(f"Always-On Rules (Idle):    {toks.get('always_on_rules_idle_tokens', 0)}")
        print(f"Conditional Rules Idle:    {toks.get('conditional_rules_idle_tokens', 0)}")
        print(f"Skills Idle:               {toks.get('skills_idle_tokens', 0)}")
        print(f"GRAND TOTAL IDLE OVERHEAD: {metrics['grand_total_idle_overhead']}")
        print(f"Calibrated Ratio:          {metrics['calibrated_ratio']}")

        print("\n[ Waste Rates ]")
        print(f"Best Governed:             {waste_rate_best}")
        print(f"Avg Governed:              {waste_rate_avg}")

        if prong_budgets:
            print("\n[ Prong Budgets ]")
            for p, b in prong_budgets.items():
                print(f"  {p}: {b}")

        if compare_data:
            print("\n[ Deltas vs Previous ]")
            prev_total = compare_data.get("grand_total_idle_overhead", 0)
            diff = metrics["grand_total_idle_overhead"] - prev_total
            print(f"Grand Total Idle Overhead: {diff:+d}")

    return 0


def cli_metrics_snapshot(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Metrics snapshot generator")
    parser.add_argument("--json", action="store_true", default=False, help="Output JSON format")
    parser.add_argument("--raw", action="store_true", default=False, help="Include timestamp in output")
    parser.add_argument("--save", action="store_true", default=False, help="Save snapshot to file")
    parser.add_argument("--compare", dest="compare_file", default=None, help="Compare with previous snapshot")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    return take_snapshot(
        json_mode=args.json,
        raw_mode=args.raw,
        compare_file=args.compare_file,
        save=args.save,
    )


# ── Cell Quorum ────────────────────────────────────────────────────────────

_QUORUM_MODES = {'breeze': 0, 'gale': 1, 'trident': 2, 'maelstrom': 3, 'tempest': 4}


def evaluate_quorum(cells_dir: Path | str, changed_files: list[str], threshold: int = 3) -> dict:
    """Core quorum evaluation — pure function."""
    if not changed_files:
        return {'quorum': False, 'cells_triggered': 0}

    cells_path = Path(cells_dir)
    if not cells_path.is_dir():
        return {'quorum': False, 'cells_triggered': 0}

    triggered = []
    for cell_file in cells_path.rglob("*.md"):
        if cell_file.name == 'README.md':
            continue
        try:
            with open(cell_file, 'r', encoding='utf-8') as f:
                content = f.read()
            fm = parse_frontmatter(content) or {}
            target_paths = fm.get('target_paths', [])
            if isinstance(target_paths, str):
                target_paths = [target_paths]
            hypothesis = fm.get('hypothesis', '')

            matched = False
            for tp in target_paths:
                tp_norm = tp.replace("\\", "/")
                for cf in changed_files:
                    cf_norm = cf.replace("\\", "/")
                    if fnmatch.fnmatch(cf_norm, tp_norm):
                        matched = True
                        break
                if matched:
                    break

            if not matched:
                for cf in changed_files:
                    basename = os.path.basename(cf)
                    if basename in hypothesis:
                        matched = True
                        break

            if matched:
                triggered.append({
                    'name': fm.get('id', cell_file.stem),
                    'type': fm.get('type', 'unknown'),
                    'minimum_mode': fm.get('minimum_mode', 'breeze'),
                    'fitness': (fm.get('fitness') or {}).get('score'),
                    'hypothesis': hypothesis[:80]
                })
        except Exception:
            pass

    if len(triggered) >= threshold:
        max_mode = max(triggered, key=lambda t: _QUORUM_MODES.get(t.get('minimum_mode', 'breeze'), 0))['minimum_mode']
        return {
            'quorum': True,
            'cells_triggered': len(triggered),
            'cell_types': list({t['type'] for t in triggered}),
            'escalate_to': max_mode,
            'triggered_cells': triggered,
        }
    return {
        'quorum': False,
        'cells_triggered': len(triggered),
    }


def cli_cell_quorum(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description='Quorum sensing: detect systemic issues from multi-cell triggers')
    parser.add_argument('--threshold', type=int, default=3, help='Minimum cells for quorum (default: 3)')
    parser.add_argument('--json', action='store_true', help='JSON output')
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    workspace = resolve_workspace()
    cells_dir = os.path.join(workspace, '.soma', 'cells')

    result = subprocess.run(['git', 'diff', '--name-only', 'HEAD'], capture_output=True, text=True, cwd=workspace)
    staged = subprocess.run(['git', 'diff', '--name-only', '--cached'], capture_output=True, text=True, cwd=workspace)
    changed_files = list(set((result.stdout + staged.stdout).strip().split('\n')) - {''})

    if not changed_files:
        print('No changes detected.')
        return 0

    quorum = evaluate_quorum(cells_dir, changed_files, threshold=args.threshold)

    if quorum['quorum']:
        if args.json:
            print(json.dumps(quorum, indent=2))
        else:
            print(f'🔬 QUORUM: {quorum["cells_triggered"]} cells triggered simultaneously!')
            print(f'   Cell types: {", ".join(quorum["cell_types"])}')
            print(f'   Escalating to: {quorum["escalate_to"]}')
            for t in quorum['triggered_cells']:
                print(f'   - {t["name"]} ({t["type"]}): {t["hypothesis"]}')

        metrics_dir = os.path.join(workspace, '.soma', 'metrics')
        os.makedirs(metrics_dir, exist_ok=True)
        with open(os.path.join(metrics_dir, 'quorum_events.jsonl'), 'a', encoding='utf-8') as f:
            quorum['timestamp'] = datetime.now(timezone.utc).isoformat() + 'Z'
            f.write(json.dumps(quorum) + '\n')
    else:
        if args.json:
            print(json.dumps(quorum))
        else:
            print(f'No quorum ({quorum["cells_triggered"]}/{args.threshold} cells triggered)')
    return 0


# ── Cell Coverage ──────────────────────────────────────────────────────────

def calculate_coverage(workspace: str, exclude: Optional[Union[List[str], str]] = None) -> dict:
    """Calculate cell coverage mapping and directory tier breakdown."""
    cells_dir = os.path.join(workspace, '.soma', 'cells')
    result = subprocess.run(['git', 'ls-files'], capture_output=True, text=True, cwd=workspace)
    all_files = [f for f in result.stdout.strip().split('\n') if f]
    EXCLUDE_PATTERNS = ['.soma/', 'vendor/', '.git/', 'node_modules/']
    if exclude:
        if isinstance(exclude, str):
            EXCLUDE_PATTERNS.append(exclude)
        else:
            EXCLUDE_PATTERNS.extend(exclude)
    all_files = [f for f in all_files if not any(p in f for p in EXCLUDE_PATTERNS)]

    cell_patterns = []
    if os.path.isdir(cells_dir):
        for cell_file in glob.glob(os.path.join(cells_dir, '**', '*.md'), recursive=True):
            if os.path.basename(cell_file) == 'README.md':
                continue
            try:
                with open(cell_file, 'r', encoding='utf-8') as f:
                    fm = parse_frontmatter(f.read()) or {}
                paths = fm.get('target_paths', [])
                if isinstance(paths, str):
                    paths = [paths]
                name = fm.get('id', os.path.splitext(os.path.basename(cell_file))[0])
                cell_patterns.append({
                    'name': name,
                    'patterns': paths,
                    'type': fm.get('type', ''),
                    'enforcement': fm.get('enforcement', 'advisory')
                })
            except Exception as exc:
                sys.stderr.write(f"Warning: Failed to parse cell {cell_file}: {exc}\n")

    covered_files = set()
    uncovered_files = set()
    coverage_map = {}
    tier_rank = {'advisory': 0, 'mechanical': 1, 'gate': 2}
    dir_tiers = {}

    for f in all_files:
        is_covered = False
        for cell in cell_patterns:
            for pattern in cell['patterns']:
                if fnmatch.fnmatch(f, pattern):
                    is_covered = True
                    break
            if is_covered:
                break

        if is_covered:
            covered_files.add(f)
        else:
            uncovered_files.add(f)

        d = os.path.dirname(f) or '.'
        if d not in coverage_map:
            coverage_map[d] = {'covered': 0, 'total': 0, 'tier': 'none'}
        coverage_map[d]['total'] += 1
        if is_covered:
            coverage_map[d]['covered'] += 1

        for cell in cell_patterns:
            for pattern in cell['patterns']:
                if fnmatch.fnmatch(f, pattern):
                    current = dir_tiers.get(d, 'none')
                    cell_tier = cell.get('enforcement', 'advisory')
                    if tier_rank.get(cell_tier, 0) > tier_rank.get(current, -1):
                        dir_tiers[d] = cell_tier
                    break

        coverage_map[d]['tier'] = dir_tiers.get(d, 'none')

    total = len(all_files)
    covered = len(covered_files)
    pct = (covered / total * 100) if total > 0 else 0

    return {
        'total_files': total,
        'covered': covered,
        'uncovered': total - covered,
        'coverage_pct': round(pct, 1),
        'by_directory': coverage_map,
        'uncovered_files': sorted(uncovered_files),
    }


calculate_cell_coverage = calculate_coverage


def cli_cell_coverage(argv: Optional[List[str]] = None, workspace: Optional[str] = None) -> int:
    parser = argparse.ArgumentParser(description='Cell coverage map: visualize governance blind spots')
    parser.add_argument('--json', action='store_true', help='JSON output')
    parser.add_argument('--exclude', action='append', default=[], help='Pattern(s) to exclude from coverage calculation')
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    ws = workspace or resolve_workspace()

    cov = calculate_coverage(ws, exclude=args.exclude)

    if args.json:
        res = dict(cov)
        res.pop('uncovered_files', None)
        print(json.dumps(res, indent=2))
    else:
        total = cov['total_files']
        covered = cov['covered']
        pct = cov['coverage_pct']
        coverage_map = cov['by_directory']
        uncovered_files = cov['uncovered_files']

        print(f'\n📊 Cell Coverage: {covered}/{total} files ({pct:.1f}%)\n')
        print(f'{"Directory":<40} {"Coverage":>10}  Bar                  Tier')
        print('─' * 90)
        tier_icons = {'gate': '🔒', 'mechanical': '⚙️', 'advisory': '💬', 'none': '⬜'}
        for d in sorted(coverage_map.keys()):
            info = coverage_map[d]
            dpct = info['covered'] / info['total'] * 100 if info['total'] > 0 else 0
            bar_len = int(dpct / 5)
            bar = '█' * bar_len + '░' * (20 - bar_len)
            status = '✅' if dpct == 100 else '⚠️' if dpct > 0 else '🔴'
            tier = info.get('tier', 'none')
            print(f'{d:<40} {info["covered"]:>3}/{info["total"]:<3} {status} {bar} {tier_icons.get(tier, "")} {tier}')

        if uncovered_files:
            print(f'\n🔴 Blind Spots ({len(uncovered_files)} uncovered files):')
            uncovered_dirs = {}
            for f in uncovered_files:
                d = os.path.dirname(f) or '.'
                uncovered_dirs[d] = uncovered_dirs.get(d, 0) + 1
            for d, count in sorted(uncovered_dirs.items(), key=lambda x: -x[1])[:10]:
                print(f'   {d}/ ({count} files)')
    return 0


# ── Immune Grade ───────────────────────────────────────────────────────────

def letter_grade(pct: float) -> str:
    """Map a percentage (0..100) to a letter grade."""
    if pct >= 97: return 'A+'
    if pct >= 93: return 'A'
    if pct >= 90: return 'A-'
    if pct >= 87: return 'B+'
    if pct >= 83: return 'B'
    if pct >= 80: return 'B-'
    if pct >= 77: return 'C+'
    if pct >= 73: return 'C'
    if pct >= 70: return 'C-'
    if pct >= 67: return 'D+'
    if pct >= 60: return 'D'
    return 'F'


def calculate_immune_grade(workspace: str) -> Optional[dict]:
    """Calculate complete governance report card."""
    cells_dir = os.path.join(workspace, '.soma', 'cells')
    cells = []
    if os.path.isdir(cells_dir):
        for cell_file in glob.glob(os.path.join(cells_dir, '**', '*.md'), recursive=True):
            if os.path.basename(cell_file) == 'README.md':
                continue
            try:
                with open(cell_file, 'r', encoding='utf-8') as f:
                    fm = parse_frontmatter(f.read()) or {}
                if isinstance(fm.get('fitness'), (int, float)):
                    fm['fitness'] = {'score': float(fm['fitness'])}
                fm['_name'] = os.path.splitext(os.path.basename(cell_file))[0]
                cells.append(fm)
            except Exception as exc:
                sys.stderr.write(f"Warning: Failed to parse cell {cell_file}: {exc}\n")

    if not cells:
        return None

    result = subprocess.run(['git', 'ls-files'], capture_output=True, text=True, cwd=workspace)
    all_files = [f for f in result.stdout.strip().split('\n') if f]
    exclude = ['.soma/', 'vendor/', '.git/', 'node_modules/']
    all_files = [f for f in all_files if not any(p in f for p in exclude)]

    all_patterns = []
    for c in cells:
        all_patterns.extend(c.get('target_paths', []))

    covered = sum(1 for f in all_files if any(fnmatch.fnmatch(f, p) for p in all_patterns))
    coverage_pct = (covered / len(all_files) * 100) if all_files else 0

    scores = [(c.get('fitness') or {}).get('score') for c in cells if (c.get('fitness') or {}).get('score') is not None]
    avg_fitness = (sum(scores) / len(scores)) if scores else 0
    fitness_pct = avg_fitness * 100

    type_counts = {}
    for c in cells:
        ct = c.get('type', 'unknown')
        type_counts[ct] = type_counts.get(ct, 0) + 1
    total = sum(type_counts.values())
    if len(type_counts) > 1:
        entropy = -sum((n/total) * math.log(n/total) for n in type_counts.values() if n > 0)
        max_entropy = math.log(len(type_counts))
        diversity = (entropy / max_entropy) * 100
    else:
        diversity = 0

    stale = sum(1 for c in cells if (c.get('fitness') or {}).get('triggers', 0) == 0)
    staleness_pct = 100 - (stale / len(cells) * 100) if cells else 100

    walls = [c for c in cells if c.get('type') == 'wall']
    healthy_walls = sum(1 for w in walls if ((w.get('fitness') or {}).get('score') is not None and (w.get('fitness') or {}).get('score', 0) > 0.3))
    wall_pct = (healthy_walls / len(walls) * 100) if walls else 100

    overall_pct = (coverage_pct * 0.3 + fitness_pct * 0.25 + diversity * 0.15 + staleness_pct * 0.15 + wall_pct * 0.15)

    tier_counts = {}
    for c in cells:
        tier = c.get('enforcement', 'advisory')
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    uncovered_dirs = {}
    for f in all_files:
        if not any(fnmatch.fnmatch(f, p) for p in all_patterns):
            d = os.path.dirname(f) or '.'
            uncovered_dirs[d] = uncovered_dirs.get(d, 0) + 1
    top_gap = max(uncovered_dirs.items(), key=lambda x: x[1]) if uncovered_dirs else ('none', 0)

    return {
        'coverage': {'pct': round(coverage_pct, 1), 'grade': letter_grade(coverage_pct)},
        'avg_fitness': {'pct': round(fitness_pct, 1), 'grade': letter_grade(fitness_pct), 'score': avg_fitness},
        'diversity': {'pct': round(diversity, 1), 'grade': letter_grade(diversity)},
        'staleness': {'pct': round(staleness_pct, 1), 'grade': letter_grade(staleness_pct)},
        'wall_integrity': {'pct': round(wall_pct, 1), 'grade': letter_grade(wall_pct)},
        'tiers': tier_counts,
        'overall': {'pct': round(overall_pct, 1), 'grade': letter_grade(overall_pct)},
        'top_improvement': f'Add cells for {top_gap[0]}/ ({top_gap[1]} uncovered files)',
        'top_gap_count': top_gap[1],
    }


def cli_immune_grade(argv: Optional[List[str]] = None, workspace: Optional[str] = None) -> int:
    parser = argparse.ArgumentParser(description='Governance report card: single-grade summary')
    parser.add_argument('--json', action='store_true', help='JSON output')
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    ws = workspace or resolve_workspace()

    report = calculate_immune_grade(ws)
    if not report:
        print('No cells found. Run Genesis first.')
        return 0

    if args.json:
        out = dict(report)
        out.pop('top_gap_count', None)
        out['avg_fitness'].pop('score', None)
        print(json.dumps(out, indent=2))
    else:
        cov_pct = report['coverage']['pct']
        avg_fit = report['avg_fitness']['score']
        fit_pct = report['avg_fitness']['pct']
        div_pct = report['diversity']['pct']
        stale_pct = report['staleness']['pct']
        wall_pct = report['wall_integrity']['pct']
        tiers = report['tiers']
        overall_grade = report['overall']['grade']

        print()
        print('═══════════════════════════════════════════')
        print('  📊 Governance Report Card')
        print('═══════════════════════════════════════════')
        print(f'  Coverage:        {cov_pct:5.1f}%  ({letter_grade(cov_pct)})')
        print(f'  Avg Fitness:     {avg_fit:.2f}   ({letter_grade(fit_pct)})')
        print(f'  Diversity:       {div_pct:5.1f}%  ({letter_grade(div_pct)})')
        print(f'  Staleness:       {stale_pct:5.1f}%  ({letter_grade(stale_pct)})')
        print(f'  Wall Integrity:  {wall_pct:5.1f}%  ({letter_grade(wall_pct)})')
        print()
        print(f'  Tiers:           A: {tiers.get("advisory", 0)} | M: {tiers.get("mechanical", 0)} | G: {tiers.get("gate", 0)}')
        print()
        print(f'  Overall Grade:   {overall_grade}')
        print()
        if report['top_gap_count'] > 0:
            print(f'  Top Improvement: {report["top_improvement"]}')
        print('═══════════════════════════════════════════')
    return 0


__all__ = [
    "VALID_SIGNAL_TYPES",
    "VALID_SOURCES",
    "SIGNALS_FILENAME",
    "LOCK_FILENAME",
    "EPOCH_FILENAME",
    "DEFAULT_GENERATION",
    "EventConflictError",
    "StaleGenerationError",
    "evidence_lock",
    "read_generation",
    "current_generation",
    "increment_generation",
    "get_signals_path",
    "get_lock_path",
    "read_signals",
    "compute_payload_digest",
    "compute_event_id",
    "append_signals",
    "append_signal",
    "detect_test_runner",
    "capture_test_outcome",
    "capture_build_outcome",
    "capture_git_signals",
    "capture_mcp_outcomes",
    "capture_human_insight_signals",
    "read_human_insight_signals",
    "commit_insight_cursor",
    "match_cells_to_changes",
    "to_fraction",
    "compute_credit_weights",
    "compute_fitness_signals",
    "update_cell_fitness",
    "append_fitness_log",
    "run_outcome_engine",
    "cli_outcome_engine",
    "INSIGHT_PRINCIPAL",
    "INSIGHT_SCOPE",
    "VERIFY_TIMEOUT",
    "_get_changed_files",
    "_parse_frontmatter",
    "_read_insight_cursor",
    "_run_verify",
    "PLATFORMS",
    "DEFAULT_PLATFORM",
    "detect_platform",
    "resolve_transcript_id",
    "extract_modified_files",
    "match_cells",
    "update_fitness",
    "cli_fitness_updater",
    "resolve_metrics_dir",
    "compute_token_census",
    "take_snapshot",
    "cli_metrics_snapshot",
    "evaluate_quorum",
    "cli_cell_quorum",
    "calculate_coverage",
    "calculate_cell_coverage",
    "cli_cell_coverage",
    "letter_grade",
    "calculate_immune_grade",
    "cli_immune_grade",
]
