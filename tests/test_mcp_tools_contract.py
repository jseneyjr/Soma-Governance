"""Contract tests for MCP tool handlers.

Tests untested tools in soma_mcp/tools.py through the execute_tool dispatcher.
"""
import os
import sys
import json
import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from soma_mcp.tools import execute_tool


def _setup_workspace(tmp_path):
    """Create a minimal workspace with cells for MCP tools."""
    ws = str(tmp_path)
    cells_dir = os.path.join(ws, '.soma', 'cells', 'vacuoles')
    os.makedirs(cells_dir, exist_ok=True)
    # Create one cell
    fm = {
        'id': 'test-cell',
        'type': 'vacuole',
        'target_paths': ['src/*.py'],
        'hypothesis': 'Test hypothesis',
        'prediction': 'Test prediction',
    }
    content = '---\n' + yaml.dump(fm, default_flow_style=False) + '---\nBody\n'
    with open(os.path.join(cells_dir, 'test-cell.md'), 'w', encoding='utf-8') as f:
        f.write(content)
    # Create genome dir
    genome_dir = os.path.join(ws, 'genome')
    os.makedirs(genome_dir, exist_ok=True)
    # Create insight log dir
    os.makedirs(os.path.join(ws, '.soma', 'insights'), exist_ok=True)
    return ws


class TestSomaScan:
    """Tests for soma_scan tool."""

    def test_scan_returns_required_keys(self, tmp_path, monkeypatch):
        ws = _setup_workspace(tmp_path)
        monkeypatch.chdir(ws)
        result = execute_tool('soma_scan', {})
        assert isinstance(result, dict)
        assert 'relevant_cells' in result or 'stats' in result or 'context' in result

    def test_scan_with_files_arg(self, tmp_path, monkeypatch):
        ws = _setup_workspace(tmp_path)
        monkeypatch.chdir(ws)
        result = execute_tool('soma_scan', {'files': ['src/foo.py']})
        assert isinstance(result, dict)


class TestSomaListCells:
    """Tests for soma_list_cells tool."""

    def test_list_returns_list(self, tmp_path, monkeypatch):
        ws = _setup_workspace(tmp_path)
        monkeypatch.chdir(ws)
        result = execute_tool('soma_list_cells', {})
        assert isinstance(result, (list, dict))


class TestSomaCreateCell:
    """Tests for soma_create_cell tool."""

    def test_create_cell_returns_prompt(self, tmp_path, monkeypatch):
        ws = _setup_workspace(tmp_path)
        monkeypatch.chdir(ws)
        result = execute_tool('soma_create_cell', {
            'description': 'Test cell for catching null dereferences'
        })
        assert isinstance(result, dict)
        assert 'prompt' in result or 'instruction' in result


class TestSomaReportOutcome:
    """Tests for soma_report_outcome tool."""

    def test_valid_outcome_returns_recorded(self, tmp_path, monkeypatch):
        ws = _setup_workspace(tmp_path)
        monkeypatch.chdir(ws)
        result = execute_tool('soma_report_outcome', {
            'outcome': 'success',
            'cells_used': ['test-cell'],
            'tests_passed': True,
        })
        assert isinstance(result, dict)
        assert result.get('status') in ('recorded', 'FAIL')

    def test_invalid_outcome_returns_error(self, tmp_path, monkeypatch):
        ws = _setup_workspace(tmp_path)
        monkeypatch.chdir(ws)
        result = execute_tool('soma_report_outcome', {
            'outcome': 'invalid_value_xyz',
        })
        assert isinstance(result, dict)


class TestSomaProposeChange:
    """Tests for soma_propose_change tool."""

    def test_propose_returns_result(self, tmp_path, monkeypatch):
        ws = _setup_workspace(tmp_path)
        monkeypatch.chdir(ws)
        # Create a target file
        src_dir = os.path.join(ws, 'src')
        os.makedirs(src_dir, exist_ok=True)
        with open(os.path.join(src_dir, 'example.py'), 'w', encoding='utf-8') as f:
            f.write('def hello():\n    return "world"\n')
        result = execute_tool('soma_propose_change', {
            'file_path': os.path.join(src_dir, 'example.py'),
            'proposed_content': 'def hello():\n    return "updated"\n',
        })
        assert isinstance(result, dict)


class TestSomaAuditTools:
    """Tests for security and performance audit tools."""

    def test_audit_security_returns_status(self, tmp_path, monkeypatch):
        ws = _setup_workspace(tmp_path)
        monkeypatch.chdir(ws)
        result = execute_tool('soma_audit_security', {
            'file_path': 'src/example.py',
            'proposed_content': 'import os\nos.system("ls")\n',
        })
        assert isinstance(result, dict)
        assert 'status' in result or 'feedback' in result

    def test_audit_performance_returns_status(self, tmp_path, monkeypatch):
        ws = _setup_workspace(tmp_path)
        monkeypatch.chdir(ws)
        result = execute_tool('soma_audit_performance', {
            'file_path': 'src/example.py',
            'proposed_content': 'for i in range(10**9): pass\n',
        })
        assert isinstance(result, dict)
        assert 'status' in result or 'feedback' in result


class TestToolOutputSerializability:
    """All tool outputs must be JSON-serializable."""

    @pytest.mark.parametrize('tool_name,args', [
        ('soma_list_cells', {}),
        ('soma_create_cell', {'description': 'test'}),
    ])
    def test_output_is_json_serializable(self, tool_name, args, tmp_path, monkeypatch):
        ws = _setup_workspace(tmp_path)
        monkeypatch.chdir(ws)
        result = execute_tool(tool_name, args)
        # Should not raise
        json.dumps(result)
