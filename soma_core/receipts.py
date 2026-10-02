import secrets
import json
import hashlib
from typing import Dict, Any, Optional

# In-memory storage for receipts: receipt_id -> receipt_data
_receipt_store: Dict[str, Dict[str, Any]] = {}

def _hash_args(args: Dict[str, Any]) -> str:
    """Consistently hash a dictionary of arguments."""
    serialized = json.dumps(args, sort_keys=True)
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

def issue_receipt(session_id: str, workspace: str, operation: str, args: Dict[str, Any], file_digest: str, cell_digest: str) -> str:
    """
    Issue an opaque, stateful, session-bound receipt.
    """
    receipt_id = secrets.token_hex(32)
    _receipt_store[receipt_id] = {
        "session_id": session_id,
        "workspace": workspace,
        "operation": operation,
        "args_hash": _hash_args(args),
        "file_digest": file_digest,
        "cell_digest": cell_digest
    }
    return receipt_id

def verify_receipt(receipt_id: str, session_id: str, workspace: str, operation: str, args: Dict[str, Any], file_digest: str, cell_digest: str) -> bool:
    """
    Verify that a receipt is valid for the given parameters.
    """
    if receipt_id not in _receipt_store:
        return False
        
    stored = _receipt_store[receipt_id]
    
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
        
    return True

def clear_receipts():
    """Clear all receipts (simulates process restart invalidation)."""
    _receipt_store.clear()
