import secrets
import json
import time
import threading
import hashlib
from typing import Dict, Any, Optional

# In-memory storage for receipts: receipt_id -> receipt_data
_receipt_store: Dict[str, Dict[str, Any]] = {}
_receipt_lock = threading.RLock()

def _hash_args(args: Dict[str, Any]) -> str:
    """Consistently hash a dictionary of arguments."""
    try:
        serialized = json.dumps(args, sort_keys=True, default=str)
    except Exception:
        serialized = str(sorted(args.items()))
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

def issue_receipt(
    session_id: str,
    workspace: str,
    operation: str,
    args: Dict[str, Any],
    file_digest: str,
    cell_digest: str,
    ttl_seconds: Optional[float] = None
) -> str:
    """
    Issue an opaque, stateful, session-bound receipt.
    """
    receipt_id = secrets.token_hex(32)
    now = time.time()
    data = {
        "session_id": session_id,
        "workspace": workspace,
        "operation": operation,
        "args_hash": _hash_args(args),
        "file_digest": file_digest,
        "cell_digest": cell_digest,
        "expires_at": (now + ttl_seconds) if ttl_seconds is not None else None,
    }
    with _receipt_lock:
        _receipt_store[receipt_id] = data
    return receipt_id

def verify_receipt(
    receipt_id: str,
    session_id: str,
    workspace: str,
    operation: str,
    args: Dict[str, Any],
    file_digest: str,
    cell_digest: str,
    consume: bool = False
) -> bool:
    """
    Verify that a receipt is valid for the given parameters.
    """
    with _receipt_lock:
        if receipt_id not in _receipt_store:
            return False
            
        stored = _receipt_store[receipt_id]
        
        # Check expiration
        if stored.get("expires_at") is not None and time.time() > stored["expires_at"]:
            _receipt_store.pop(receipt_id, None)
            return False
        
        # Server recomputes hashes to compare
        if stored["session_id"] != session_id:
            return False
        if stored["workspace"] != workspace:
            return False
        if stored["operation"] != operation:
            return False
        if stored["args_hash"] != _hash_args(args):
            return False
        if stored["file_digest"] != file_digest:
            return False
        if stored["cell_digest"] != cell_digest:
            return False
            
        # Only consume upon successful verification
        if consume:
            _receipt_store.pop(receipt_id, None)
            
        return True

def clear_receipts():
    """Clear all receipts (simulates process restart invalidation)."""
    with _receipt_lock:
        _receipt_store.clear()
