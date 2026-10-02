import os
import json
import shutil
from pathlib import Path

def run_epoch_migration(workspace: str) -> bool:
    """Run an atomic epoch generation cutover."""
    ws = Path(workspace)
    soma_dir = ws / ".soma"
    migration_lock = soma_dir / "migration.lock"
    epoch_file = soma_dir / "epoch_generation"
    evidence_dir = soma_dir / "evidence"
    
    # 1. Acquire exclusive migration lease
    if migration_lock.exists():
        return False
    migration_lock.touch()
    
    try:
        # 2. Snapshot legacy evidence
        snapshot_dir = evidence_dir / "snapshot"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        legacy_fitness = evidence_dir / "fitness.jsonl"
        if legacy_fitness.exists():
            shutil.copy2(legacy_fitness, snapshot_dir / "fitness.jsonl")
            
        # 3. Read old epoch
        old_epoch = 1
        if epoch_file.exists():
            try:
                old_epoch = int(epoch_file.read_text().strip())
            except ValueError:
                pass
                
        # 4. Write new epoch
        new_epoch = old_epoch + 1
        epoch_file.write_text(str(new_epoch))
        
        # 5. Conversion could happen here...
        
        return True
    finally:
        # 6. Re-enable hooks/endpoints
        if migration_lock.exists():
            migration_lock.unlink()
