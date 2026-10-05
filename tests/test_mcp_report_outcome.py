import json
import os
import pytest

def _workspace_with_cell(tmp_path, cell="trap-x"):
    cells = tmp_path / ".soma" / "cells" / "vacuoles"
    cells.mkdir(parents=True)
    (cells / f"{cell}.md").write_text(
        f"---\nid: {cell}\ntype: vacuole\nhypothesis: h\nprediction: p\n---\n# x\n",
        encoding="utf-8")
    return tmp_path

def _jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def test_report_outcome_writes_only_canonical_signal(tmp_path, monkeypatch):
    from soma_mcp.tools import execute_tool
    ws = _workspace_with_cell(tmp_path)
    monkeypatch.setenv("SOMA_WORKSPACE", str(ws))
    result = execute_tool(
        "soma_report_outcome",
        {"outcome": "success", "cells_used": ["trap-x"],
         "workspace": str(ws), "idempotency_key": "report-1"},
    )
    assert result["status"] == "recorded"
    ev = ws / ".soma" / "evidence"
    signal, = _jsonl(ev / "signals.jsonl")
    assert signal["cell"] == "trap-x"
    assert signal["signal"] == "tp"
    assert signal["event_id"], "MCP outcome signal is not idempotent"
    assert not (ev / "outcomes.jsonl").exists()

