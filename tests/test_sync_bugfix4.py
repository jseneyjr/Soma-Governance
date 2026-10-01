"""Regression tests for Bug 4: sync.py score clobber.

Bug 4: sync.py clobbers scores when a cell has triggers but no outcomes.
It sets score = 0.0 instead of preserving the existing score.
"""
import json
import os
import sys

import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _make_cell_file(cells_dir, name, fitness=None):
    """Create a minimal cell .md file with optional fitness block."""
    cell_path = os.path.join(cells_dir, f'{name}.md')
    fm = {
        'id': name,
        'type': 'wall',
        'target_paths': ['tests/*'],
    }
    if fitness:
        fm['fitness'] = fitness
    content = f'---\n{yaml.dump(fm, default_flow_style=False)}---\n\n# {name}\n'
    os.makedirs(os.path.dirname(cell_path), exist_ok=True)
    with open(cell_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return cell_path


def _read_frontmatter(cell_path):
    """Read YAML frontmatter from a cell file."""
    with open(cell_path, 'r', encoding='utf-8') as f:
        content = f.read()
    end = content.find('---', 3)
    return yaml.safe_load(content[3:end].strip())


class TestBug4ScoreClobber:
    """sync.py must NOT clobber scores when no outcome data exists."""

    def test_score_preserved_when_no_outcomes(self, tmp_path):
        """Cell with triggers but zero tp/fp keeps existing score."""
        from soma_cli.sync import sync_frontmatter

        cells_dir = str(tmp_path / 'cells')
        cell_path = _make_cell_file(
            cells_dir, 'trap-example',
            fitness={'triggers': 5, 'true_positives': 3, 'false_positives': 1,
                     'score': 0.6, 'last_trigger_date': '2026-10-01T00:00:00Z'},
        )

        # Evidence has triggers but NO outcomes (tp=0, fp=0)
        counts = {
            'trap-example': {
                'triggers': 6, 'tp': 0, 'fp': 0, 'last_trigger': '2026-10-01T01:00:00Z',
            },
        }

        sync_frontmatter(cells_dir, counts)

        fm = _read_frontmatter(cell_path)
        fitness = fm['fitness']
        # Triggers should update
        assert fitness['triggers'] == 6
        # But score should NOT be clobbered to 0.0
        assert fitness['score'] != 0.0, (
            'Bug 4: score clobbered to 0.0 when no outcome data exists'
        )

    def test_score_updated_when_outcomes_exist(self, tmp_path):
        """Cell with both triggers and tp/fp gets correct score."""
        from soma_cli.sync import sync_frontmatter

        cells_dir = str(tmp_path / 'cells')
        cell_path = _make_cell_file(
            cells_dir, 'trap-example',
            fitness={'triggers': 0, 'true_positives': 0, 'false_positives': 0,
                     'score': None},
        )

        counts = {
            'trap-example': {
                'triggers': 10, 'tp': 7, 'fp': 2, 'last_trigger': '2026-10-01T01:00:00Z',
            },
        }

        sync_frontmatter(cells_dir, counts)

        fm = _read_frontmatter(cell_path)
        fitness = fm['fitness']
        assert fitness['triggers'] == 10
        assert fitness['true_positives'] == 7
        assert fitness['false_positives'] == 2
        assert fitness['score'] == 0.7  # 7/10

    def test_zero_triggers_score_is_none(self, tmp_path):
        """Cell with 0 triggers → score = None."""
        from soma_cli.sync import sync_frontmatter

        cells_dir = str(tmp_path / 'cells')
        cell_path = _make_cell_file(
            cells_dir, 'trap-example',
            fitness={'triggers': 0, 'true_positives': 0, 'false_positives': 0,
                     'score': None},
        )

        counts = {
            'trap-example': {
                'triggers': 0, 'tp': 0, 'fp': 0, 'last_trigger': None,
            },
        }

        # Should not change anything (already in sync)
        changes = sync_frontmatter(cells_dir, counts)
        assert len(changes) == 0
