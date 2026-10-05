import pytest
from soma_mcp.server import handle_request, _session_token, _canonical_workspace, _execution_enabled

# Mock global state for testing handle_request directly
import soma_mcp.server as server_module

@pytest.fixture(autouse=True)
def setup_server_globals(monkeypatch):
    import os
    os.environ["SOMA_EXECUTION_ENABLED"] = "1"
    monkeypatch.setattr(server_module, "_canonical_workspace", "/fake/workspace")
    monkeypatch.setattr(server_module, "_execution_enabled", True)
    # Initialize properly instead of mutating private module state directly
    handle_request({"jsonrpc": "2.0", "id": 0, "method": "initialize"})

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

def test_dispatch_flow_with_receipt(tmp_path, monkeypatch):
    (tmp_path / ".soma" / "cells").mkdir(parents=True)
    monkeypatch.setattr(server_module, "_canonical_workspace", str(tmp_path))
    # Issue receipt
    req1 = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "soma_request_receipt",
            "arguments": {
                "operation": "soma_create_cell",
                "arguments": {
                    "description": "Add security check"
                }
            }
        }
    }
    resp1 = handle_request(req1)
    import json
    receipt_data = json.loads(resp1["result"]["content"][0]["text"])
    receipt_id = receipt_data["receipt"]

    # Call tool with receipt for real (without mocking execute_tool)
    req2 = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "soma_create_cell",
            "arguments": {
                "description": "Add security check",
                "receipt": receipt_id
            }
        }
    }
    resp2 = handle_request(req2)
    assert "result" in resp2
    assert not resp2["result"].get("isError")
    tool_output = json.loads(resp2["result"]["content"][0]["text"])
    assert "prompt" in tool_output
    assert "instruction" in tool_output

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
