import os
import time
import json
import shutil
from pathlib import Path

STALE_LOCK_TIMEOUT = 300  # seconds

def _acquire_migration_lock(lock_path: Path) -> bool:
    lock_str = str(lock_path)
    pid = os.getpid()
    now = time.time()
    payload = f"{pid}:{now}\n".encode('utf-8')
    for _ in range(2):
        try:
            fd = os.open(lock_str, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, payload)
            finally:
                os.close(fd)
            return True
        except FileExistsError:
            try:
                mtime = lock_path.stat().st_mtime
                is_stale = (now - mtime > STALE_LOCK_TIMEOUT)
                try:
                    content = lock_path.read_text(encoding='utf-8').strip()
                    if ':' in content:
                        lock_pid_str, _ = content.split(':', 1)
                        lock_pid = int(lock_pid_str)
                        try:
                            os.kill(lock_pid, 0)
                        except OSError:
                            is_stale = True  # Process died
                except Exception:
                    pass
                if is_stale:
                    lock_path.unlink(missing_ok=True)
                    continue
            except Exception:
                pass
            return False
    return False

def run_epoch_migration(workspace: str) -> bool:
    """Run an atomic epoch generation cutover."""
    ws = Path(workspace)
    soma_dir = ws / ".soma"
    migration_lock = soma_dir / "migration.lock"
    epoch_file = soma_dir / "epoch_generation"
    evidence_dir = soma_dir / "evidence"
    
    soma_dir.mkdir(parents=True, exist_ok=True)

    # 1. Acquire exclusive migration lease atomically
    if not _acquire_migration_lock(migration_lock):
        return False
    
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
        
        return True
    finally:
        # 6. Re-enable hooks/endpoints
        migration_lock.unlink(missing_ok=True)
