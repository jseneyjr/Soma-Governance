"""MCP tool annotations: every advertised tool must declare the four boolean
hints (readOnlyHint, destructiveHint, idempotentHint, openWorldHint) and a
title. Expected values are derived from reading each handler in
soma_mcp/tools.py; see docs/project/CHANGELOG.md for rationale.
"""
import pytest

import soma_mcp.server as server_module
from soma_mcp.server import handle_request

_HINTS = ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint")

# (readOnly, destructive, idempotent) — openWorld is False for every tool:
# the server only touches the confined local workspace and makes no network calls.
_EXPECTED = {
    "soma_scan": (True, False, True),
    "soma_list_cells": (True, False, True),
    "soma_grade": (True, False, True),
    "soma_coverage": (True, False, True),
    "soma_fitness": (True, False, True),
    "soma_create_cell": (True, False, True),  # returns a prompt; writes nothing
    "soma_propose_change": (True, False, True),
    "soma_audit_security": (True, False, True),
    "soma_audit_performance": (True, False, True),
    "soma_checkpoint": (True, False, True),
    "soma_verify_changes": (False, False, True),  # runs verifiers as subprocesses
    "soma_request_receipt": (False, False, False),  # mints a new receipt each call
    "soma_report_outcome": (False, False, False),  # appends telemetry
    "soma_capture_insight": (False, False, False),  # appends an insight record
    "soma_generate_manifest": (False, True, True),  # overwrites manifest; may create key
}


@pytest.fixture
def tools(monkeypatch):
    monkeypatch.setattr(server_module, "_session_token", "test-session")
    monkeypatch.setattr(server_module, "_execution_enabled", True)
    resp = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    return {t["name"]: t for t in resp["result"]["tools"]}


def test_expected_table_covers_every_advertised_tool(tools):
    assert set(tools) == set(_EXPECTED)


def test_every_tool_declares_four_boolean_hints_and_title(tools):
    for name, tool in tools.items():
        ann = tool.get("annotations")
        assert isinstance(ann, dict), f"{name}: missing annotations"
        for hint in _HINTS:
            assert isinstance(ann.get(hint), bool), f"{name}: {hint} not a bool"
        assert isinstance(ann.get("title"), str) and ann["title"], f"{name}: no title"


@pytest.mark.parametrize("name", sorted(_EXPECTED))
def test_hint_values_match_handler_behavior(tools, name):
    ro, destructive, idem = _EXPECTED[name]
    ann = tools[name]["annotations"]
    assert ann["readOnlyHint"] is ro
    assert ann["destructiveHint"] is destructive
    assert ann["idempotentHint"] is idem
    assert ann["openWorldHint"] is False


def test_read_only_tools_are_never_destructive(tools):
    for name, tool in tools.items():
        ann = tool["annotations"]
        if ann["readOnlyHint"]:
            assert ann["destructiveHint"] is False, name


def test_hints_agree_with_server_privilege_classes(tools):
    # Anything the server gates behind a receipt as a write tool must not
    # advertise itself as read-only.
    for name in server_module._WRITE_TOOLS - {"soma_create_cell"}:
        assert tools[name]["annotations"]["readOnlyHint"] is False, name
