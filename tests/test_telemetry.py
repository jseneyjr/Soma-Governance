"""TDD tests for soma_sdk.telemetry — unified signal evidence writer.

Tests written BEFORE implementation (Red phase).
"""
import json
import os
import threading
import pytest


class TestAppendSignal:
    """append_signal() writes a single JSONL record to the evidence log."""

    def test_writes_jsonl_record(self, tmp_path):
        """A single append creates one valid JSON line."""
        from soma_sdk.telemetry import append_signal

        workspace = str(tmp_path)
        append_signal(
            workspace=workspace,
            cell_name='trap-example',
            signal_type='tp',
            source='ci',
            metadata={'commit_sha': 'abc123'},
        )

        log_path = tmp_path / '.soma' / 'evidence' / 'signals.jsonl'
        assert log_path.exists(), f'Expected {log_path} to exist'

        lines = log_path.read_text(encoding='utf-8').strip().splitlines()
        assert len(lines) == 1

        record = json.loads(lines[0])
        assert record['cell'] == 'trap-example'
        assert record['signal'] == 'tp'
        assert record['source'] == 'ci'
        assert record['metadata']['commit_sha'] == 'abc123'
        assert 'timestamp' in record

    def test_appends_multiple_records(self, tmp_path):
        """Multiple calls append to the same file, not overwrite."""
        from soma_sdk.telemetry import append_signal

        workspace = str(tmp_path)
        append_signal(workspace=workspace, cell_name='cell-a', signal_type='tp', source='ci')
        append_signal(workspace=workspace, cell_name='cell-b', signal_type='fp', source='session')

        log_path = tmp_path / '.soma' / 'evidence' / 'signals.jsonl'
        lines = log_path.read_text(encoding='utf-8').strip().splitlines()
        assert len(lines) == 2

        records = [json.loads(line) for line in lines]
        assert records[0]['cell'] == 'cell-a'
        assert records[1]['cell'] == 'cell-b'

    def test_creates_directories_if_missing(self, tmp_path):
        """Parent directories (.soma/evidence/) are created automatically."""
        from soma_sdk.telemetry import append_signal

        workspace = str(tmp_path)
        # No .soma/evidence/ exists yet
        append_signal(workspace=workspace, cell_name='cell-x', signal_type='trigger', source='ci')

        log_path = tmp_path / '.soma' / 'evidence' / 'signals.jsonl'
        assert log_path.exists()


class TestSignalSchema:
    """Every record must conform to the canonical schema."""

    def test_required_fields_present(self, tmp_path):
        """Every signal record has: timestamp, cell, signal, source."""
        from soma_sdk.telemetry import append_signal

        workspace = str(tmp_path)
        append_signal(workspace=workspace, cell_name='rule-1', signal_type='trigger', source='ci')

        log_path = tmp_path / '.soma' / 'evidence' / 'signals.jsonl'
        record = json.loads(log_path.read_text(encoding='utf-8').strip())

        required = {'timestamp', 'cell', 'signal', 'source'}
        assert required.issubset(record.keys()), f'Missing keys: {required - record.keys()}'

    def test_signal_type_validated(self, tmp_path):
        """Invalid signal types are rejected."""
        from soma_sdk.telemetry import append_signal

        workspace = str(tmp_path)
        with pytest.raises(ValueError, match='signal_type'):
            append_signal(workspace=workspace, cell_name='rule-1', signal_type='invalid', source='ci')

    def test_source_validated(self, tmp_path):
        """Invalid source values are rejected."""
        from soma_sdk.telemetry import append_signal

        workspace = str(tmp_path)
        with pytest.raises(ValueError, match='source'):
            append_signal(workspace=workspace, cell_name='rule-1', signal_type='tp', source='unknown_source')

    def test_metadata_is_optional(self, tmp_path):
        """Signals can be written without metadata."""
        from soma_sdk.telemetry import append_signal

        workspace = str(tmp_path)
        append_signal(workspace=workspace, cell_name='rule-1', signal_type='tp', source='session')

        log_path = tmp_path / '.soma' / 'evidence' / 'signals.jsonl'
        record = json.loads(log_path.read_text(encoding='utf-8').strip())
        # metadata should be empty dict or absent, not an error
        assert record.get('metadata') is None or isinstance(record.get('metadata'), dict)


class TestConcurrentAppend:
    """File writes must be safe under concurrent access."""

    def test_concurrent_writes_no_data_loss(self, tmp_path):
        """10 concurrent threads each writing 10 signals = 100 total records."""
        from soma_sdk.telemetry import append_signal

        workspace = str(tmp_path)
        n_threads = 10
        n_per_thread = 10

        def writer(thread_id):
            for i in range(n_per_thread):
                append_signal(
                    workspace=workspace,
                    cell_name=f'cell-t{thread_id}-{i}',
                    signal_type='trigger',
                    source='ci',
                )

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        log_path = tmp_path / '.soma' / 'evidence' / 'signals.jsonl'
        lines = log_path.read_text(encoding='utf-8').strip().splitlines()
        assert len(lines) == n_threads * n_per_thread, (
            f'Expected {n_threads * n_per_thread} records, got {len(lines)}'
        )

        # Every line must be valid JSON
        for i, line in enumerate(lines):
            try:
                json.loads(line)
            except json.JSONDecodeError:
                pytest.fail(f'Line {i} is not valid JSON: {line!r}')
