import os
import json
import pytest
from pathlib import Path
from soma_cli.migration import run_epoch_migration
from soma_sdk.telemetry import append_signal

def test_epoch_migration_lifecycle(tmp_path):
    ws = tmp_path / "workspace"
    evidence_dir = ws / ".soma" / "evidence"
    evidence_dir.mkdir(parents=True)
    
    # 1. Start with epoch 1
    (ws / ".soma" / "epoch_generation").write_text("1")
    
    # Write some legacy evidence
    legacy_file = evidence_dir / "fitness.jsonl"
    legacy_file.write_text('{"cell": "foo", "signal": "tp"}\n')
    
    # Run migration
    assert run_epoch_migration(str(ws)) == True
    
    # Check that generation is now 2
    assert (ws / ".soma" / "epoch_generation").read_text().strip() == "2"
    
    # Check that legacy file was snapshotted
    assert (evidence_dir / "snapshot" / "fitness.jsonl").exists()
    
    # New writes should require the correct epoch (this is internal to telemetry)
    # append_signal should work if no epoch generation is passed or if we pass the right one
    
def test_migration_blocks_telemetry(tmp_path):
    ws = tmp_path / "workspace"
    (ws / ".soma" / "evidence").mkdir(parents=True)
    (ws / ".soma" / "migration.lock").touch()
    
    # Telemetry should fail if migration lock is active
    with pytest.raises(RuntimeError, match="migration in progress"):
        append_signal(str(ws), "foo", "tp", "manual")
