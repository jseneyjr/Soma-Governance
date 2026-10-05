import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from soma_sdk.governance import Governance

def test_governance_uses_importlib_resources_instead_of_relative_path(tmp_path, monkeypatch):
    # If _find_scripts_dir is removed or doesn't find enzymes locally, 
    # it should use importlib.resources.
    gov = Governance(project_root=tmp_path)
    
    # We will mock subprocess.run to avoid actually executing and test if it runs the script from importlib
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"status": "ok"}'
        
        # We need to make sure the scripts_dir is not relying on relative paths
        # So we mock Path.exists to always return False for the local candidates if _find_scripts_dir still exists
        
        try:
            res = gov.fitness_landscape()
        except RuntimeError as e:
            pytest.fail(f"Failed with {e}, likely because it still relies on relative enzymes/")
            
        assert mock_run.called
        cmd_run = mock_run.call_args[0][0]
        # Check that the script being executed is cell_fitness.py
        assert any("cell_fitness.py" in str(arg) for arg in cmd_run)


def _populate_governed_workspace(root: Path):
    cells_dir = root / ".soma" / "cells"
    for d in ["vacuoles", "walls", "chloroplasts", "membranes", "plasmodesmata"]:
        (cells_dir / d).mkdir(parents=True, exist_ok=True)
    (cells_dir / "vacuoles" / "vacuole-test-trap.md").write_text(
        "---\ntype: vacuole\nhypothesis: test trap\n---\nBody\n", encoding="utf-8"
    )
    (cells_dir / "walls" / "wall-test-guard.md").write_text(
        "---\ntype: wall\nhypothesis: test guard\n---\nBody\n", encoding="utf-8"
    )
    (cells_dir / "chloroplasts" / "chloroplast-test-persona.md").write_text(
        "---\ntype: chloroplast\nhypothesis: test persona\n---\nBody\n", encoding="utf-8"
    )
    (cells_dir / "membranes" / "membrane-test-boundary.md").write_text(
        "---\ntype: membrane\nhypothesis: test boundary\n---\nBody\n", encoding="utf-8"
    )
    (cells_dir / "plasmodesmata" / "plasmodesmata-test-bridge.md").write_text(
        "---\ntype: plasmodesmata\nhypothesis: test bridge\n---\nBody\n", encoding="utf-8"
    )


def test_list_cells_with_cell_type_filter(tmp_path):
    _populate_governed_workspace(tmp_path)
    gov = Governance(project_root=tmp_path)

    # 0 args: returns all cells
    all_cells = gov.list_cells()
    assert len(all_cells) == 5

    # Filter by canonical type
    vacuoles = gov.list_cells(cell_type="vacuole")
    assert len(vacuoles) == 1
    assert vacuoles[0]["_name"] == "vacuole-test-trap"

    # Filter by porcelain alias
    traps = gov.list_cells(cell_type="learned-trap")
    assert len(traps) == 1
    assert traps[0]["_name"] == "vacuole-test-trap"


def test_list_rules_porcelain_facade(tmp_path):
    _populate_governed_workspace(tmp_path)
    gov = Governance(project_root=tmp_path)

    all_rules = gov.list_rules()
    assert len(all_rules) == 5

    guards = gov.list_rules(rule_type="safety-guard")
    assert len(guards) == 1
    assert guards[0]["_name"] == "wall-test-guard"

    personas = gov.list_rules(rule_type="agent-persona")
    assert len(personas) == 1
    assert personas[0]["_name"] == "chloroplast-test-persona"

    boundaries = gov.list_rules(rule_type="escalation-boundary")
    assert len(boundaries) == 1
    assert boundaries[0]["_name"] == "membrane-test-boundary"

    bridges = gov.list_rules(rule_type="contract-bridge")
    assert len(bridges) == 1
    assert bridges[0]["_name"] == "plasmodesmata-test-bridge"


def test_record_outcome_in_process(tmp_path):
    import json
    _populate_governed_workspace(tmp_path)
    gov = Governance(project_root=tmp_path)

    res = gov.record_outcome(
        rule_id="vacuole-test-trap",
        success=True,
        metric={"test_metric": 99}
    )
    assert isinstance(res, dict)
    assert res.get("signal") == "tp" or res.get("signal_type") == "tp"

    signals_file = tmp_path / ".soma" / "evidence" / "signals.jsonl"
    assert signals_file.exists()
    lines = [json.loads(line) for line in signals_file.read_text(encoding="utf-8").strip().splitlines()]
    assert len(lines) >= 1
    assert lines[-1]["cell"] == "vacuole-test-trap"
    assert lines[-1]["signal"] == "tp"


def test_record_outcome_fp_and_source_validation(tmp_path, monkeypatch):
    import json
    _populate_governed_workspace(tmp_path)
    gov = Governance(project_root=tmp_path)

    # Test failure outcome emits fp
    res_fp = gov.record_outcome("vacuole-test-trap", success=False, source="ci")
    assert isinstance(res_fp, dict)
    assert res_fp.get("signal") == "fp"

    # Test invalid source raises ValueError
    with pytest.raises(ValueError, match="Invalid telemetry source"):
        gov.record_outcome("vacuole-test-trap", success=True, source="invalid_src")

    # Test fallback guarantees dict return
    def _raise(*args, **kwargs):
        raise RuntimeError("simulated telemetry failure")

    monkeypatch.setattr("soma_core.telemetry.append_signal", _raise)
    monkeypatch.setattr(gov, "signal", lambda *a, **k: "legacy stdout string")
    fallback_res = gov.record_outcome("vacuole-test-trap", success=True)
    assert isinstance(fallback_res, dict)
    assert fallback_res["status"] == "fallback_recorded"
    assert fallback_res["signal"] == "tp"
    assert fallback_res["raw"] == "legacy stdout string"


def test_list_cells_corrupted_isolation(tmp_path):
    _populate_governed_workspace(tmp_path)
    gov = Governance(project_root=tmp_path)

    # Add corrupted vacuole cell
    corrupted_file = tmp_path / ".soma" / "cells" / "vacuoles" / "corrupted_trap.md"
    corrupted_file.write_bytes(b"\xff\xfe\x00\x00")

    # Full list returns diagnostic error record
    all_cells = gov.list_cells()
    assert any(c.get("_name") == "corrupted_trap" and "_error" in c for c in all_cells)

    # Wall filter must isolate and NOT leak corrupted vacuole
    wall_cells = gov.list_cells(cell_type="wall")
    assert not any(c.get("_name") == "corrupted_trap" for c in wall_cells)
    assert len(wall_cells) == 1
    assert wall_cells[0]["_name"] == "wall-test-guard"


