import pytest
from soma_mcp.server import handle_request
import soma_mcp.server as server_module
from unittest.mock import MagicMock

@pytest.fixture(autouse=True)
def setup_server_globals(monkeypatch):
    monkeypatch.setattr(server_module, "_session_token", "test-session-123")
    monkeypatch.setattr(server_module, "_canonical_workspace", "/fake/workspace")
    monkeypatch.setattr(server_module, "_execution_enabled", True)

@pytest.fixture
def mock_gov(monkeypatch):
    # Mock the get_governance call inside execute_tool
    mock = MagicMock()
    mock.grade.return_value = {"grade": "A"}
    mock.coverage_report.return_value = {"coverage": 100}
    mock.fitness_landscape.return_value = {"landscape": "flat"}
    
    # We patch `soma_mcp.tools.get_governance` to return our mock
    import soma_mcp.tools as tools_module
    monkeypatch.setattr(tools_module, "get_governance", lambda args: mock)
    return mock

def _call(name, args=None):
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": name,
            "arguments": args or {}
        }
    }
    return handle_request(req)

def test_soma_grade_calls_gov_grade(mock_gov):
    resp = _call("soma_grade")
    assert resp.get("result")["content"][0]["text"] == '{"grade": "A"}'
    mock_gov.grade.assert_called_once()

def test_soma_coverage_calls_gov_coverage_report(mock_gov):
    resp = _call("soma_coverage")
    assert resp.get("result")["content"][0]["text"] == '{"coverage": 100}'
    mock_gov.coverage_report.assert_called_once()

def test_soma_fitness_calls_gov_fitness_landscape(mock_gov):
    resp = _call("soma_fitness", {"bayesian": True})
    assert resp.get("result")["content"][0]["text"] == '{"landscape": "flat"}'
    mock_gov.fitness_landscape.assert_called_once_with(bayesian=True)

def test_soma_generate_manifest_requires_receipt():
    resp = _call("soma_generate_manifest")
    assert "error" in resp
    assert resp["error"]["code"] == -32600
    assert "receipt" in resp["error"]["message"].lower()

