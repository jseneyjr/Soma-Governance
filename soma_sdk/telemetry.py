"""Unified telemetry signal writer for the Soma evidence pipeline.

All fitness signal producers (CI reporter, outcome engine, MCP tools,
cell_signal.sh, fitness_updater) should call append_signal() to write
to the canonical evidence log at .soma/evidence/signals.jsonl.
"""
import fcntl
import json
import os
from datetime import datetime, timezone

VALID_SIGNAL_TYPES = frozenset({'tp', 'fp', 'fn', 'trigger'})
VALID_SOURCES = frozenset({'ci', 'session', 'mcp', 'manual'})
SIGNALS_FILENAME = 'signals.jsonl'


def append_signal(workspace, cell_name, signal_type, source, metadata=None):
    """Append a fitness signal to the canonical evidence log.

    Args:
        workspace: Root workspace directory containing .soma/
        cell_name: Cell identifier (e.g. 'trap-example')
        signal_type: One of 'tp', 'fp', 'fn', 'trigger'
        source: One of 'ci', 'session', 'mcp', 'manual'
        metadata: Optional dict with extra context (commit_sha, changed_files, etc.)

    Raises:
        ValueError: If signal_type or source is not in the allowed set.
    """
    if signal_type not in VALID_SIGNAL_TYPES:
        raise ValueError(
            f'signal_type must be one of {sorted(VALID_SIGNAL_TYPES)}, '
            f'got {signal_type!r}'
        )
    if source not in VALID_SOURCES:
        raise ValueError(
            f'source must be one of {sorted(VALID_SOURCES)}, '
            f'got {source!r}'
        )

    record = {
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'cell': cell_name,
        'signal': signal_type,
        'source': source,
    }
    if metadata:
        record['metadata'] = metadata

    evidence_dir = os.path.join(workspace, '.soma', 'evidence')
    os.makedirs(evidence_dir, exist_ok=True)

    log_path = os.path.join(evidence_dir, SIGNALS_FILENAME)
    line = json.dumps(record, ensure_ascii=False) + '\n'

    # File-locked append for concurrent safety
    with open(log_path, 'a', encoding='utf-8') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(line)
            f.flush()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
