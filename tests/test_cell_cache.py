"""Tests for soma_mcp.cell_cache — mtime-based in-memory cell cache.

v0.83 'Fast Path': eliminates redundant disk I/O in MCP hot path.
"""
import json
import os
import sys
import time

import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from soma_mcp.cell_cache import CellCache


def _make_cell(cells_dir, subdir, name, target_paths=None):
    """Create a minimal cell .md file."""
    path = os.path.join(cells_dir, subdir, f'{name}.md')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fm = {
        'id': name,
        'type': 'wall',
        'target_paths': target_paths or ['src/*.py'],
    }
    content = f'---\n{yaml.dump(fm, default_flow_style=False)}---\n\n# {name}\nBody text.\n'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return path


class TestCellCacheBasic:
    """Core cache behavior."""

    def test_returns_cells_from_disk(self, tmp_path):
        """First call reads cells from disk."""
        cells_dir = str(tmp_path / '.soma' / 'cells')
        _make_cell(cells_dir, 'walls', 'trap-test')
        cache = CellCache()
        cells = cache.get_cells(str(tmp_path))
        assert len(cells) == 1
        assert cells[0]['id'] == 'trap-test'

    def test_second_call_returns_cached(self, tmp_path):
        """Second call with same mtime returns cached list (no re-parse)."""
        cells_dir = str(tmp_path / '.soma' / 'cells')
        _make_cell(cells_dir, 'walls', 'trap-test')
        cache = CellCache()
        cells1 = cache.get_cells(str(tmp_path))
        cells2 = cache.get_cells(str(tmp_path))
        # Same list object means cache hit
        assert cells1 is cells2

    def test_invalidates_on_new_file(self, tmp_path):
        """Adding a cell file triggers re-parse."""
        cells_dir = str(tmp_path / '.soma' / 'cells')
        _make_cell(cells_dir, 'walls', 'trap-a')
        cache = CellCache()
        cells1 = cache.get_cells(str(tmp_path))
        assert len(cells1) == 1

        # Touch the directory to update mtime
        time.sleep(0.05)
        _make_cell(cells_dir, 'walls', 'trap-b')

        cells2 = cache.get_cells(str(tmp_path))
        assert len(cells2) == 2
        assert cells2 is not cells1

    def test_invalidates_on_modified_file(self, tmp_path):
        """Modifying a cell file triggers re-parse."""
        cells_dir = str(tmp_path / '.soma' / 'cells')
        cell_path = _make_cell(cells_dir, 'walls', 'trap-test')
        cache = CellCache()
        cells1 = cache.get_cells(str(tmp_path))
        assert cells1[0]['id'] == 'trap-test'

        # Modify the file — touch to update mtime
        time.sleep(0.05)
        with open(cell_path, 'a', encoding='utf-8') as f:
            f.write('\nAppended.\n')
        # Touch parent dir to update dir mtime
        os.utime(os.path.dirname(cell_path))

        cells2 = cache.get_cells(str(tmp_path))
        assert cells2 is not cells1

    def test_empty_dir_returns_empty(self, tmp_path):
        """No cells directory → empty list."""
        cache = CellCache()
        cells = cache.get_cells(str(tmp_path))
        assert cells == []

    def test_deleted_cell_removed(self, tmp_path):
        """Removing a cell file updates cache."""
        cells_dir = str(tmp_path / '.soma' / 'cells')
        cell_path = _make_cell(cells_dir, 'walls', 'trap-a')
        _make_cell(cells_dir, 'walls', 'trap-b')
        cache = CellCache()
        cells1 = cache.get_cells(str(tmp_path))
        assert len(cells1) == 2

        time.sleep(0.05)
        os.remove(cell_path)
        # Touch dir to update mtime
        os.utime(os.path.dirname(cell_path))

        cells2 = cache.get_cells(str(tmp_path))
        assert len(cells2) == 1

    def test_skips_readme(self, tmp_path):
        """README.md files are not treated as cells."""
        cells_dir = str(tmp_path / '.soma' / 'cells')
        _make_cell(cells_dir, 'walls', 'trap-test')
        readme = os.path.join(cells_dir, 'README.md')
        with open(readme, 'w') as f:
            f.write('# Cell Directory\n')
        cache = CellCache()
        cells = cache.get_cells(str(tmp_path))
        assert len(cells) == 1

    def test_skips_expired_cells(self, tmp_path):
        """Cells with expired_at are excluded."""
        cells_dir = str(tmp_path / '.soma' / 'cells')
        path = os.path.join(cells_dir, 'walls', 'trap-expired.md')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fm = {'id': 'trap-expired', 'type': 'wall', 'expired_at': '2026-01-01'}
        content = f'---\n{yaml.dump(fm)}---\n\nExpired.\n'
        with open(path, 'w') as f:
            f.write(content)
        cache = CellCache()
        cells = cache.get_cells(str(tmp_path))
        assert len(cells) == 0


class TestCellCacheIntegration:
    """Integration with existing load_all_cells output format."""

    def test_output_matches_load_all_cells_schema(self, tmp_path):
        """Cache output has same keys as load_all_cells."""
        cells_dir = str(tmp_path / '.soma' / 'cells')
        _make_cell(cells_dir, 'walls', 'trap-schema')
        cache = CellCache()
        cells = cache.get_cells(str(tmp_path))
        cell = cells[0]
        # Must have internal keys set by load_all_cells
        assert '_name' in cell
        assert '_path' in cell
        assert '_body' in cell
        assert '_full' in cell
        assert cell['_name'] == 'trap-schema'
