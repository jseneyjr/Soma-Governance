"""Regression tests for telemetry bug fixes (v0.81).

Bug 1: outcome_engine read from wrong path (.soma/outcomes.jsonl)
Bug 2: outcome_engine expected wrong schema key (cells_used vs cell_id)
Bug 3: sync.py ignored agent outcomes (success/failure not mapped to tp/fp)
"""
import json
import os
import sys
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_enzymes = os.path.join(REPO_ROOT, 'enzymes')
if _enzymes not in sys.path:
    sys.path.insert(0, _enzymes)


class TestBug1OutcomeEnginePath:
    """Bug 1: capture_mcp_outcomes must read from .soma/evidence/outcomes.jsonl."""

    def test_reads_from_evidence_dir(self, tmp_path):
        """outcome_engine reads from .soma/evidence/outcomes.jsonl, not .soma/outcomes.jsonl."""
        from outcome_engine import capture_mcp_outcomes

        # Write to the CORRECT path
        evidence_dir = tmp_path / '.soma' / 'evidence'
        evidence_dir.mkdir(parents=True)
        signals_file = evidence_dir / 'signals.jsonl'
        record = {'cell_id': 'trap-example', 'outcome': 'success',
                  'timestamp': '2026-10-01T00:00:00Z'}
        signals_file.write_text(json.dumps(record) + '\n', encoding='utf-8')

        results = capture_mcp_outcomes(str(tmp_path))
        assert len(results) == 1
        assert results[0]['cell_id'] == 'trap-example'

    def test_ignores_old_path(self, tmp_path):
        """outcome_engine does NOT read from the old .soma/outcomes.jsonl path."""
        from outcome_engine import capture_mcp_outcomes

        # Write to the OLD (wrong) path
        old_dir = tmp_path / '.soma'
        old_dir.mkdir(parents=True)
        old_file = old_dir / 'outcomes.jsonl'
        old_file.write_text(json.dumps({'cell_id': 'stale'}) + '\n', encoding='utf-8')

        # Correct path doesn't exist
        results = capture_mcp_outcomes(str(tmp_path))
        assert len(results) == 0, 'Should not read from old .soma/outcomes.jsonl path'


class TestBug2OutcomeEngineSchema:
    """Bug 2: compute_fitness_signals must handle both cells_used and cell_id schemas."""

    def test_cell_id_schema_matches(self, tmp_path):
        """MCP records with cell_id (string) are matched to cells."""
        from outcome_engine import compute_fitness_signals

        triggered_cells = [{
            '_name': 'trap-example',
            '_path': str(tmp_path / 'cell.md'),
            'target_paths': ['enzymes/*'],
        }]
        outcomes = {
            'tests': {'verified': True, 'passed': True, 'framework': 'pytest'},
            'build': {'verified': False, 'passed': None},
            'git': {'reverts': 0, 'rework_count': 0},
            'mcp': [{'cell_id': 'trap-example', 'outcome': 'success'}],
        }

        signals = compute_fitness_signals(triggered_cells, outcomes)
        assert len(signals) == 1
        # success + tests passed = positive signal (agent reported success correctly)
        assert signals[0]['signal'] > 0
        assert any('agent reported success' in r for r in signals[0]['reasons'])

    def test_cells_used_schema_still_works(self, tmp_path):
        """Legacy records with cells_used (list) still match."""
        from outcome_engine import compute_fitness_signals

        triggered_cells = [{
            '_name': 'trap-example',
            '_path': str(tmp_path / 'cell.md'),
            'target_paths': ['enzymes/*'],
        }]
        outcomes = {
            'tests': {'verified': True, 'passed': True, 'framework': 'pytest'},
            'build': {'verified': False, 'passed': None},
            'git': {'reverts': 0, 'rework_count': 0},
            'mcp': [{'cells_used': ['trap-example'], 'outcome': 'success'}],
        }

        signals = compute_fitness_signals(triggered_cells, outcomes)
        assert len(signals) == 1
        assert any('agent reported success' in r for r in signals[0]['reasons'])


class TestBug3SyncOutcomeMapping:
    """Bug 3: sync.py aggregate_evidence must map success→tp, failure→fp."""

    def test_success_mapped_to_tp(self, tmp_path):
        """outcome='success' is counted as tp."""
        from soma_cli.sync import aggregate_evidence

        evidence_dir = str(tmp_path)
        signals_file = tmp_path / 'signals.jsonl'
        record = {'cell_id': 'trap-example', 'outcome': 'success',
                  'timestamp': '2026-10-01T00:00:00Z'}
        signals_file.write_text(json.dumps(record) + '\n', encoding='utf-8')

        counts = aggregate_evidence(evidence_dir)
        assert counts['trap-example']['tp'] == 1

    def test_failure_mapped_to_fp(self, tmp_path):
        """outcome='failure' is counted as fp."""
        from soma_cli.sync import aggregate_evidence

        evidence_dir = str(tmp_path)
        signals_file = tmp_path / 'signals.jsonl'
        record = {'cell_id': 'trap-example', 'outcome': 'failure',
                  'timestamp': '2026-10-01T00:00:00Z'}
        signals_file.write_text(json.dumps(record) + '\n', encoding='utf-8')

        counts = aggregate_evidence(evidence_dir)
        assert counts['trap-example']['fp'] == 1

    def test_literal_tp_fp_still_work(self, tmp_path):
        """outcome='tp' and 'fp' still count correctly (backward compat)."""
        from soma_cli.sync import aggregate_evidence

        evidence_dir = str(tmp_path)
        signals_file = tmp_path / 'signals.jsonl'
        lines = [
            json.dumps({'cell_id': 'cell-a', 'outcome': 'tp'}),
            json.dumps({'cell_id': 'cell-a', 'outcome': 'fp'}),
        ]
        signals_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')

        counts = aggregate_evidence(evidence_dir)
        assert counts['cell-a']['tp'] == 1
        assert counts['cell-a']['fp'] == 1

    def test_partial_outcome_ignored(self, tmp_path):
        """outcome='partial' is neither tp nor fp."""
        from soma_cli.sync import aggregate_evidence

        evidence_dir = str(tmp_path)
        signals_file = tmp_path / 'signals.jsonl'
        record = {'cell_id': 'trap-example', 'outcome': 'partial',
                  'timestamp': '2026-10-01T00:00:00Z'}
        signals_file.write_text(json.dumps(record) + '\n', encoding='utf-8')

        counts = aggregate_evidence(evidence_dir)
        assert counts['trap-example']['tp'] == 0
        assert counts['trap-example']['fp'] == 0
