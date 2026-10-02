import pytest
from soma_mcp.server import handle_request, _session_token, _canonical_workspace, _execution_enabled

# Mock global state for testing handle_request directly
import soma_mcp.server as server_module

@pytest.fixture(autouse=True)
def setup_server_globals(monkeypatch):
    monkeypatch.setattr(server_module, "_session_token", "test-session-123")
    monkeypatch.setattr(server_module, "_canonical_workspace", "/fake/workspace")
    monkeypatch.setattr(server_module, "_execution_enabled", True)

def test_execute_tool_requires_receipt():
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "soma_propose_change",
            "arguments": {
                "file_path": "test.txt",
                "proposed_content": "new"
            }
        }
    }
    resp = handle_request(req)
    assert resp["error"]["code"] == -32600
    assert "valid 'receipt'" in resp["error"]["message"]

def test_write_tool_requires_receipt():
    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "soma_report_outcome",
            "arguments": {
                "outcome": "success"
            }
        }
    }
    resp = handle_request(req)
    assert resp["error"]["code"] == -32600
    assert "valid 'receipt'" in resp["error"]["message"]

def test_soma_request_receipt_issues_receipt():
    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "soma_request_receipt",
            "arguments": {
                "operation": "soma_report_outcome",
                "arguments": {
                    "outcome": "success"
                }
            }
        }
    }
    resp = handle_request(req)
    assert "result" in resp
    import json
    content = resp["result"]["content"][0]["text"]
    assert "receipt" in content

def test_dispatch_flow_with_receipt(monkeypatch):
    # Issue receipt
    req1 = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "soma_request_receipt",
            "arguments": {
                "operation": "soma_report_outcome",
                "arguments": {
                    "outcome": "success"
                }
            }
        }
    }
    resp1 = handle_request(req1)
    import json
    receipt_data = json.loads(resp1["result"]["content"][0]["text"])
    receipt_id = receipt_data["receipt"]

    # Mock execute_tool to avoid actually running
    monkeypatch.setattr(server_module, "execute_tool", lambda name, args: {"mock": "ok"})

    # Call tool with receipt
    req2 = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "soma_report_outcome",
            "arguments": {
                "outcome": "success",
                "receipt": receipt_id
            }
        }
    }
    resp2 = handle_request(req2)
    assert "result" in resp2
    assert not resp2["result"]["isError"]

def test_invalid_receipt_is_rejected():
    req = {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "name": "soma_report_outcome",
            "arguments": {
                "outcome": "success",
                "receipt": "bad-receipt"
            }
        }
    }
    resp = handle_request(req)
    assert resp["error"]["code"] == -32600
    assert "Invalid, expired, or mismatched receipt" in resp["error"]["message"]
