"""Behavioral tests for cell dependency analysis (co-trigger detection).

TDD Phase: Tests written BEFORE implementation changes (Phase 2.0).
Tests verify co-trigger detection logic by creating test cells
with known target_paths and asserting correct edge detection.
"""
import json
import os
import sys
import subprocess
import tempfile
import shutil

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, 'enzymes'))

# Check if cell_deps.py supports --workspace (Phase 2.1 deliverable)
_check = subprocess.run(
    [sys.executable, os.path.join(REPO_ROOT, 'enzymes', 'cell_deps.py'), '--help'],
    capture_output=True, text=True
)
HAS_WORKSPACE_ARG = '--workspace' in _check.stdout

skip_until_workspace = pytest.mark.skipif(
    not HAS_WORKSPACE_ARG,
    reason="cell_deps.py --workspace not yet implemented (Phase 2.1)"
)


def _create_workspace_with_cells(cells):
    """Create a temp workspace with .soma/cells/ containing the given cells.
    
    Args:
        cells: list of dicts with 'name', 'type', 'target_paths' keys.
    
    Returns:
        workspace path.
    """
    workspace = tempfile.mkdtemp()
    cells_dir = os.path.join(workspace, '.soma', 'cells', 'vacuoles')
    os.makedirs(cells_dir)
    
    for cell in cells:
        cell_path = os.path.join(cells_dir, f"{cell['name']}.md")
        target_lines = '\n'.join(f'  - "{p}"' for p in cell.get('target_paths', []))
        with open(cell_path, 'w', encoding='utf-8') as f:
            f.write(f"---\n")
            f.write(f"name: {cell['name']}\n")
            f.write(f"type: {cell.get('type', 'vacuole')}\n")
            f.write(f"hypothesis: Test cell\n")
            f.write(f"target_paths:\n{target_lines}\n")
            f.write(f"---\n")
            f.write(f"# {cell['name']}\n")
    
    return workspace


@skip_until_workspace
class TestCellCoTriggerDetection:
    """Tests for co-trigger detection between cells."""

    def test_shared_target_paths_detected(self):
        """Two cells sharing target_paths produce a co-trigger edge."""
        workspace = _create_workspace_with_cells([
            {'name': 'cell-a', 'target_paths': ['src/*.py', 'lib/*.py']},
            {'name': 'cell-b', 'target_paths': ['src/*.py', 'tests/*.py']},
        ])
        try:
            result = subprocess.run(
                [sys.executable, os.path.join(REPO_ROOT, 'enzymes', 'cell_deps.py'),
                 '--json', '--workspace', workspace],
                capture_output=True, text=True, cwd=REPO_ROOT
            )
            assert result.returncode == 0, f"cell_deps.py failed: {result.stderr}"
            data = json.loads(result.stdout)
            edges = data.get('edges', [])
            assert len(edges) >= 1, "Should detect at least one co-trigger edge"
            
            # Find the edge between cell-a and cell-b
            edge = next(
                (e for e in edges if 
                 {e['from'], e['to']} == {'cell-a', 'cell-b'}),
                None
            )
            assert edge is not None, "Expected edge between cell-a and cell-b"
            assert 'src/*.py' in edge['shared_paths']
        finally:
            shutil.rmtree(workspace)

    def test_disjoint_target_paths_no_edge(self):
        """Two cells with disjoint target_paths produce NO edge."""
        workspace = _create_workspace_with_cells([
            {'name': 'cell-x', 'target_paths': ['src/*.py']},
            {'name': 'cell-y', 'target_paths': ['docs/*.md']},
        ])
        try:
            result = subprocess.run(
                [sys.executable, os.path.join(REPO_ROOT, 'enzymes', 'cell_deps.py'),
                 '--json', '--workspace', workspace],
                capture_output=True, text=True, cwd=REPO_ROOT
            )
            assert result.returncode == 0, f"cell_deps.py failed: {result.stderr}"
            data = json.loads(result.stdout)
            edges = data.get('edges', [])
            # Filter for edges between our test cells
            test_edges = [e for e in edges if 
                         {e['from'], e['to']} == {'cell-x', 'cell-y'}]
            assert len(test_edges) == 0, "Disjoint cells should have no edge"
        finally:
            shutil.rmtree(workspace)

    def test_multiple_shared_paths(self):
        """Cells sharing multiple paths report all shared paths."""
        workspace = _create_workspace_with_cells([
            {'name': 'cell-m', 'target_paths': ['src/*.py', 'lib/*.py', 'api/*.py']},
            {'name': 'cell-n', 'target_paths': ['src/*.py', 'api/*.py', 'tests/*.py']},
        ])
        try:
            result = subprocess.run(
                [sys.executable, os.path.join(REPO_ROOT, 'enzymes', 'cell_deps.py'),
                 '--json', '--workspace', workspace],
                capture_output=True, text=True, cwd=REPO_ROOT
            )
            assert result.returncode == 0
            data = json.loads(result.stdout)
            edges = data.get('edges', [])
            edge = next(
                (e for e in edges if 
                 {e['from'], e['to']} == {'cell-m', 'cell-n'}),
                None
            )
            assert edge is not None
            assert len(edge['shared_paths']) == 2, "Should share src/*.py and api/*.py"
            assert set(edge['shared_paths']) == {'src/*.py', 'api/*.py'}
        finally:
            shutil.rmtree(workspace)

    def test_three_cells_pairwise(self):
        """Three cells with partial overlap produce correct pairwise edges."""
        workspace = _create_workspace_with_cells([
            {'name': 'a', 'target_paths': ['src/*.py']},
            {'name': 'b', 'target_paths': ['src/*.py', 'lib/*.py']},
            {'name': 'c', 'target_paths': ['lib/*.py']},
        ])
        try:
            result = subprocess.run(
                [sys.executable, os.path.join(REPO_ROOT, 'enzymes', 'cell_deps.py'),
                 '--json', '--workspace', workspace],
                capture_output=True, text=True, cwd=REPO_ROOT
            )
            assert result.returncode == 0
            data = json.loads(result.stdout)
            edges = data.get('edges', [])
            
            # a-b share src/*.py
            ab = next((e for e in edges if {e['from'], e['to']} == {'a', 'b'}), None)
            assert ab is not None, "a and b should share src/*.py"
            
            # b-c share lib/*.py
            bc = next((e for e in edges if {e['from'], e['to']} == {'b', 'c'}), None)
            assert bc is not None, "b and c should share lib/*.py"
            
            # a-c should NOT share (src vs lib)
            ac = next((e for e in edges if {e['from'], e['to']} == {'a', 'c'}), None)
            assert ac is None, "a and c should not share any paths"
        finally:
            shutil.rmtree(workspace)

    def test_empty_workspace_no_crash(self):
        """Workspace with no cells should not crash."""
        workspace = tempfile.mkdtemp()
        cells_dir = os.path.join(workspace, '.soma', 'cells')
        os.makedirs(cells_dir)
        try:
            result = subprocess.run(
                [sys.executable, os.path.join(REPO_ROOT, 'enzymes', 'cell_deps.py'),
                 '--json', '--workspace', workspace],
                capture_output=True, text=True, cwd=REPO_ROOT
            )
            assert result.returncode == 0
            data = json.loads(result.stdout)
            assert data.get('cells', 0) == 0
            assert data.get('edges', []) == []
        finally:
            shutil.rmtree(workspace)
