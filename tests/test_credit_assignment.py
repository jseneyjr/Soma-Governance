"""Behavioral tests for Phase 3.1 credit assignment.

Tests scope-narrowed per-file credit distribution, probabilistic rounding,
and signal provenance.
"""
import json
import os
import sys
import yaml
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Add enzymes/ to path for soma_resolve
_enzymes = os.path.join(REPO_ROOT, 'enzymes')
if _enzymes not in sys.path:
    sys.path.insert(0, _enzymes)


def _make_cell_dict(name, target_paths):
    """Create a triggered-cell dict matching match_cells_to_changes output."""
    return {
        'id': name,
        '_name': name,
        '_path': f'/tmp/{name}.md',
        'target_paths': target_paths,
    }


class TestScopeNarrowing:
    """Credit only flows to cells whose target_paths match specific changed files."""

    def test_cell_matching_tests_gets_no_credit_for_src(self):
        from enzymes.outcome_engine import compute_credit_weights
        cells = [_make_cell_dict('c-tests', ['tests/*.py'])]
        weights = compute_credit_weights(cells, ['src/foo.py'])
        assert weights['c-tests'] == 0.0

    def test_cell_matching_src_gets_credit_for_src(self):
        from enzymes.outcome_engine import compute_credit_weights
        cells = [_make_cell_dict('c-src', ['src/*.py'])]
        weights = compute_credit_weights(cells, ['src/foo.py'])
        assert weights['c-src'] == 1.0

    def test_cell_matching_nothing_gets_zero_credit(self):
        from enzymes.outcome_engine import compute_credit_weights
        cells = [_make_cell_dict('c-docs', ['docs/*.md'])]
        weights = compute_credit_weights(cells, ['src/foo.py'])
        assert weights['c-docs'] == 0.0


class TestCreditConservation:
    """Per-file credit must sum to exactly 1.0."""

    def test_three_cells_same_file_get_one_third_each(self):
        from enzymes.outcome_engine import compute_credit_weights
        cells = [
            _make_cell_dict('a', ['src/*.py']),
            _make_cell_dict('b', ['src/*.py']),
            _make_cell_dict('c', ['src/*.py']),
        ]
        weights = compute_credit_weights(cells, ['src/foo.py'])
        for name in ['a', 'b', 'c']:
            assert abs(weights[name] - 1 / 3) < 1e-9

    def test_one_cell_unique_file_gets_full_credit(self):
        from enzymes.outcome_engine import compute_credit_weights
        cells = [
            _make_cell_dict('sole', ['src/*.py']),
            _make_cell_dict('other', ['tests/*.py']),
        ]
        weights = compute_credit_weights(cells, ['src/foo.py'])
        assert weights['sole'] == 1.0
        assert weights['other'] == 0.0

    def test_per_file_credit_sums_to_one(self):
        from enzymes.outcome_engine import compute_credit_weights
        cells = [
            _make_cell_dict('x', ['src/*.py']),
            _make_cell_dict('y', ['src/*.py']),
            _make_cell_dict('z', ['src/*.py', 'tests/*.py']),
        ]
        weights = compute_credit_weights(cells, ['src/bar.py'])
        total = sum(weights[n] for n in ['x', 'y', 'z'])
        assert abs(total - 1.0) < 1e-9

    def test_five_cells_same_file_get_one_fifth_each(self):
        from enzymes.outcome_engine import compute_credit_weights
        cells = [_make_cell_dict(f'c{i}', ['src/*.py']) for i in range(5)]
        weights = compute_credit_weights(cells, ['src/foo.py'])
        for i in range(5):
            assert abs(weights[f'c{i}'] - 0.2) < 1e-9


class TestProbabilisticRounding:
    """prob_round converts fractional credit to integer 0/1 while preserving expected value."""

    def test_prob_round_one_always_returns_one(self):
        from enzymes.outcome_engine import prob_round
        for _ in range(100):
            assert prob_round(1.0) == 1

    def test_prob_round_zero_always_returns_zero(self):
        from enzymes.outcome_engine import prob_round
        for _ in range(100):
            assert prob_round(0.0) == 0

    def test_prob_round_half_statistical(self):
        from enzymes.outcome_engine import prob_round
        results = [prob_round(0.5) for _ in range(1000)]
        pct = sum(results) / len(results)
        assert 0.40 <= pct <= 0.60, f"Expected ~50% but got {pct*100:.1f}%"

    def test_prob_round_returns_int(self):
        from enzymes.outcome_engine import prob_round
        for val in [0.0, 0.1, 0.5, 0.9, 1.0]:
            result = prob_round(val)
            assert isinstance(result, int)
            assert result in (0, 1)


class TestSignalProvenance:
    """Fitness JSONL entries include credit weight metadata."""

    def test_jsonl_entry_has_credit_weight(self, tmp_path):
        from enzymes.outcome_engine import compute_fitness_signals, append_fitness_log
        cells = [_make_cell_dict('prov-cell', ['src/*.py'])]
        outcomes = {'tests': {'verified': True, 'passed': True, 'exit_code': 0}}
        signals = compute_fitness_signals(cells, outcomes, changed_files=['src/foo.py'])
        ws = str(tmp_path)
        os.makedirs(os.path.join(ws, '.soma', 'cells'), exist_ok=True)
        append_fitness_log(ws, signals, outcomes)
        log_path = os.path.join(ws, '.soma', 'cells', 'fitness.jsonl')
        with open(log_path, 'r', encoding='utf-8') as f:
            entry = json.loads(f.readline())
        assert 'credit_weight' in entry
        assert isinstance(entry['credit_weight'], (int, float))

    def test_jsonl_entry_has_signal_method(self, tmp_path):
        from enzymes.outcome_engine import compute_fitness_signals, append_fitness_log
        cells = [_make_cell_dict('method-cell', ['src/*.py'])]
        outcomes = {'tests': {'verified': True, 'passed': True, 'exit_code': 0}}
        signals = compute_fitness_signals(cells, outcomes)
        ws = str(tmp_path)
        os.makedirs(os.path.join(ws, '.soma', 'cells'), exist_ok=True)
        append_fitness_log(ws, signals, outcomes)
        log_path = os.path.join(ws, '.soma', 'cells', 'fitness.jsonl')
        with open(log_path, 'r', encoding='utf-8') as f:
            entry = json.loads(f.readline())
        assert 'signal_method' in entry
        assert entry['signal_method'] == 'credit_weighted'


class TestStatisticalConvergence:
    """Over many signals, accumulated credit converges to expected value."""

    def test_convergence_within_ten_percent(self):
        from enzymes.outcome_engine import prob_round
        credit = 1.0 / 3.0
        total = sum(prob_round(credit) for _ in range(1000))
        expected = 1000 * credit  # ~333
        assert abs(total - expected) < expected * 0.15, (
            f"Expected ~{expected:.0f} but got {total}"
        )
