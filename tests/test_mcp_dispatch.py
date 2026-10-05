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


def test_porcelain_create_rule_requires_receipt():
    req = {
        "jsonrpc": "2.0",
        "id": 7,
        "method": "tools/call",
        "params": {
            "name": "soma_create_rule",
            "arguments": {
                "description": "Rule without receipt"
            }
        }
    }
    resp = handle_request(req)
    assert resp["error"]["code"] == -32600
    assert "requires a valid 'receipt'" in resp["error"]["message"]


def test_porcelain_create_rule_dispatch_flow_with_receipt(tmp_path, monkeypatch):
    (tmp_path / ".soma" / "cells").mkdir(parents=True)
    monkeypatch.setattr(server_module, "_canonical_workspace", str(tmp_path))
    # Request receipt for porcelain tool
    req1 = {
        "jsonrpc": "2.0",
        "id": 8,
        "method": "tools/call",
        "params": {
            "name": "soma_request_receipt",
            "arguments": {
                "operation": "soma_create_rule",
                "arguments": {
                    "description": "Add security check",
                    "rule_type": "safety-guard"
                }
            }
        }
    }
    resp1 = handle_request(req1)
    import json
    receipt_data = json.loads(resp1["result"]["content"][0]["text"])
    receipt_id = receipt_data["receipt"]

    # Redeem receipt using soma_create_rule
    req2 = {
        "jsonrpc": "2.0",
        "id": 9,
        "method": "tools/call",
        "params": {
            "name": "soma_create_rule",
            "arguments": {
                "description": "Add security check",
                "rule_type": "safety-guard",
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


def test_porcelain_list_rules_dispatch(tmp_path, monkeypatch):
    (tmp_path / ".soma" / "cells" / "walls").mkdir(parents=True)
    (tmp_path / ".soma" / "cells" / "walls" / "wall-test.md").write_text(
        "---\ntype: wall\nhypothesis: test\n---\nbody\n", encoding="utf-8"
    )
    monkeypatch.setattr(server_module, "_canonical_workspace", str(tmp_path))
    req = {
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/call",
        "params": {
            "name": "soma_list_rules",
            "arguments": {}
        }
    }
    resp = handle_request(req)
    assert "result" in resp
    import json
    cells = json.loads(resp["result"]["content"][0]["text"])
    assert len(cells) == 1
    assert cells[0]["_name"] == "wall-test"


def test_porcelain_rule_fitness_dispatch(tmp_path, monkeypatch):
    (tmp_path / ".soma" / "cells").mkdir(parents=True)
    monkeypatch.setattr(server_module, "_canonical_workspace", str(tmp_path))
    from soma_sdk.governance import Governance
    monkeypatch.setattr(Governance, "fitness_landscape", lambda self, bayesian=False: [{"rule": "test", "score": 1.0}])
    req = {
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {
            "name": "soma_rule_fitness",
            "arguments": {}
        }
    }
    resp = handle_request(req)
    assert "result" in resp
    assert not resp["result"].get("isError")
    import json
    data = json.loads(resp["result"]["content"][0]["text"])
    assert data == [{"rule": "test", "score": 1.0}]


def test_invalid_receipt_does_not_consume_rate_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(server_module, "_canonical_workspace", str(tmp_path))
    # soma_checkpoint quota is 3 calls / 60s
    req = {
        "jsonrpc": "2.0",
        "id": 12,
        "method": "tools/call",
        "params": {
            "name": "soma_checkpoint",
            "arguments": {
                "receipt": "bogus-unauthenticated-receipt"
            }
        }
    }
    # Issue 10 calls with bogus receipts (exceeding max 3)
    for _ in range(10):
        resp = handle_request(req)
        assert resp["error"]["code"] == -32600
        assert "Invalid, expired, or mismatched receipt" in resp["error"]["message"]

    # Verify quota was rolled back and is not exhausted
    assert server_module._tool_call_times["soma_checkpoint"] == []


def test_canonical_create_cell_with_porcelain_args_redemption(tmp_path, monkeypatch):
    (tmp_path / ".soma" / "cells").mkdir(parents=True)
    monkeypatch.setattr(server_module, "_canonical_workspace", str(tmp_path))
    # Request receipt for canonical tool soma_create_cell with porcelain argument rule_type
    req1 = {
        "jsonrpc": "2.0",
        "id": 13,
        "method": "tools/call",
        "params": {
            "name": "soma_request_receipt",
            "arguments": {
                "operation": "soma_create_cell",
                "arguments": {
                    "description": "Add boundary check",
                    "rule_type": "safety-guard"
                }
            }
        }
    }
    resp1 = handle_request(req1)
    import json
    receipt_data = json.loads(resp1["result"]["content"][0]["text"])
    receipt_id = receipt_data["receipt"]

    # Redeem receipt using soma_create_cell with same arguments
    req2 = {
        "jsonrpc": "2.0",
        "id": 14,
        "method": "tools/call",
        "params": {
            "name": "soma_create_cell",
            "arguments": {
                "description": "Add boundary check",
                "rule_type": "safety-guard",
                "receipt": receipt_id
            }
        }
    }
    resp2 = handle_request(req2)
    assert "result" in resp2
    assert not resp2["result"].get("isError")


def test_report_outcome_with_rules_alias(tmp_path, monkeypatch):
    (tmp_path / ".soma" / "cells" / "walls").mkdir(parents=True)
    (tmp_path / ".soma" / "cells" / "walls" / "wall-test.md").write_text(
        "---\ntype: wall\nhypothesis: test\n---\nbody\n", encoding="utf-8"
    )
    monkeypatch.setattr(server_module, "_canonical_workspace", str(tmp_path))

    # Request receipt with 'rules' alias
    req1 = {
        "jsonrpc": "2.0",
        "id": 15,
        "method": "tools/call",
        "params": {
            "name": "soma_request_receipt",
            "arguments": {
                "operation": "soma_report_outcome",
                "arguments": {
                    "idempotency_key": "test-key-1",
                    "rules": ["wall-test"],
                    "outcome": "tp"
                }
            }
        }
    }
    resp1 = handle_request(req1)
    import json
    receipt_data = json.loads(resp1["result"]["content"][0]["text"])
    receipt_id = receipt_data["receipt"]

    # Redeem receipt with 'rules'
    req2 = {
        "jsonrpc": "2.0",
        "id": 16,
        "method": "tools/call",
        "params": {
            "name": "soma_report_outcome",
            "arguments": {
                "idempotency_key": "test-key-1",
                "rules": ["wall-test"],
                "outcome": "tp",
                "receipt": receipt_id
            }
        }
    }
    resp2 = handle_request(req2)
    assert "result" in resp2
    assert not resp2["result"].get("isError")
    result_data = json.loads(resp2["result"]["content"][0]["text"])
    assert result_data.get("status") == "recorded"


def test_request_receipt_invalid_rolls_back_rate_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(server_module, "_canonical_workspace", str(tmp_path))
    server_module._tool_call_times["soma_request_receipt"] = []
    # Invalid operation request
    req = {
        "jsonrpc": "2.0",
        "id": 17,
        "method": "tools/call",
        "params": {
            "name": "soma_request_receipt",
            "arguments": {
                "operation": "nonexistent_tool"
            }
        }
    }
    for _ in range(5):
        resp = handle_request(req)
        assert resp["error"]["code"] == -32602
    # Verify rate limit was rolled back
    assert server_module._tool_call_times["soma_request_receipt"] == []


def test_state_digests_error_rolls_back_rate_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(server_module, "_canonical_workspace", str(tmp_path))
    server_module._tool_call_times["soma_checkpoint"] = []
    def _fail_digests(args):
        raise RuntimeError("simulated filesystem error")
    monkeypatch.setattr(server_module, "_state_digests", _fail_digests)

    req = {
        "jsonrpc": "2.0",
        "id": 18,
        "method": "tools/call",
        "params": {
            "name": "soma_checkpoint",
            "arguments": {
                "receipt": "some-receipt"
            }
        }
    }
    resp = handle_request(req)
    assert resp["error"]["code"] == -32602
    assert "simulated filesystem error" in resp["error"]["message"]
    assert server_module._tool_call_times["soma_checkpoint"] == []



