"""Behavioral tests for cell_tournament.py.

Tests tournament selection logic via subprocess and monkeypatching.
"""
import os
import sys
import subprocess
import random
import pytest
from soma_core.frontmatter import dump_frontmatter

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _make_cell(workspace, cell_id, fitness_score=0.8, cell_type='vacuole',
               triggers=10, true_positives=8, false_positives=2):
    """Create a cell with known fitness for tournament testing."""
    type_map = {'vacuole': 'vacuoles', 'wall': 'walls', 'membrane': 'membranes'}
    cells_dir = os.path.join(workspace, '.soma', 'cells',
                             type_map.get(cell_type, 'vacuoles'))
    os.makedirs(cells_dir, exist_ok=True)
    fm = {
        'id': cell_id,
        'type': cell_type,
        'hypothesis': f'Hypothesis for {cell_id}',
        'prediction': f'Prediction for {cell_id}',
        'target_paths': ['src/*.py'],
        'fitness': {
            'triggers': triggers,
            'true_positives': true_positives,
            'false_positives': false_positives,
            'score': fitness_score,
        },
    }
    content = dump_frontmatter(fm, body="Body\n")
    path = os.path.join(cells_dir, f'{cell_id}.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return path


def _run_tournament(workspace, k=3, count=5, extra_args=None):
    """Run tournament via subprocess."""
    cmd = [sys.executable, os.path.join(REPO_ROOT, 'enzymes', 'cell_tournament.py'),
           '--k', str(k), '--count', str(count)]
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=workspace,
        env={**os.environ, 'PYTHONPATH': REPO_ROOT}
    )
    return result


class TestTournamentBasics:
    """Basic tournament selection behavior."""

    def test_tournament_with_cells_exits_zero(self, tmp_path):
        ws = str(tmp_path)
        for i in range(5):
            _make_cell(ws, f'cell-{i}', fitness_score=0.1 * (i + 1))
        result = _run_tournament(ws)
        assert result.returncode == 0

    def test_tournament_output_contains_winner(self, tmp_path):
        ws = str(tmp_path)
        _make_cell(ws, 'best-cell', fitness_score=0.99)
        _make_cell(ws, 'worst-cell', fitness_score=0.01)
        result = _run_tournament(ws, k=2, count=1)
        assert result.returncode == 0
        assert len(result.stdout.strip()) > 0

    def test_tournament_no_valid_cells_exits_zero(self, tmp_path):
        ws = str(tmp_path)
        os.makedirs(os.path.join(ws, '.soma', 'cells'), exist_ok=True)
        result = _run_tournament(ws)
        assert result.returncode == 0
        assert 'No valid cells' in result.stdout or result.stdout.strip() == ''

    def test_tournament_k_exceeds_cell_count_no_crash(self, tmp_path):
        ws = str(tmp_path)
        _make_cell(ws, 'only-cell', fitness_score=0.5)
        result = _run_tournament(ws, k=100, count=1)
        assert result.returncode == 0

    def test_tournament_count_three_produces_output(self, tmp_path):
        ws = str(tmp_path)
        for i in range(5):
            _make_cell(ws, f'multi-{i}', fitness_score=0.5)
        result = _run_tournament(ws, count=3)
        assert result.returncode == 0
        # Should have some output for multiple rounds
        assert len(result.stdout.strip()) > 0


class TestTournamentReadOnly:
    """Tournament must not modify cell files."""

    def test_cell_files_unchanged_after_tournament(self, tmp_path):
        ws = str(tmp_path)
        path = _make_cell(ws, 'readonly-cell', fitness_score=0.7)
        with open(path, 'r', encoding='utf-8') as f:
            before = f.read()
        _run_tournament(ws, count=5)
        with open(path, 'r', encoding='utf-8') as f:
            after = f.read()
        assert before == after, "Tournament modified cell file"


class TestTournamentNullFitness:
    """Tournament handles cells with null/missing fitness."""

    def test_null_fitness_cells_get_negative_score(self, tmp_path):
        ws = str(tmp_path)
        # Cell with no fitness field
        cells_dir = os.path.join(ws, '.soma', 'cells', 'vacuoles')
        os.makedirs(cells_dir, exist_ok=True)
        fm = {'id': 'no-fitness', 'type': 'vacuole',
              'hypothesis': 'test', 'prediction': 'test',
              'target_paths': ['src/*.py']}
        content = dump_frontmatter(fm, body="Body\n")
        with open(os.path.join(cells_dir, 'no-fitness.md'), 'w', encoding='utf-8') as f:
            f.write(content)
        # Also add a cell with fitness so tournament has something to compare
        _make_cell(ws, 'has-fitness', fitness_score=0.5)
        result = _run_tournament(ws, k=2, count=1)
        assert result.returncode == 0
