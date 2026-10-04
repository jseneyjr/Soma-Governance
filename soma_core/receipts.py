import secrets
import json
import os
import time
import threading
import hashlib
from typing import Dict, Any, Iterable, List, Optional

from soma_core.cell_inventory import inventory_cells

# Argument keys that name workspace files a tool will read or act on. A receipt
# binds the content of each of these, so editing a target between issuance and
# redemption makes the receipt stale.
TARGET_PATH_KEYS = ("file_path", "files", "context_files")

# Client-supplied keys the server owns. They are stripped before hashing and
# dispatch; "workspace" is re-injected from the operator-configured value.
SERVER_OWNED_KEYS = ("workspace", "receipt", "_sessionToken")

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

def strip_server_owned(args: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return a copy of client arguments without server-owned keys."""
    if not isinstance(args, dict):
        return {}
    return {k: v for k, v in args.items() if k not in SERVER_OWNED_KEYS}


def target_paths(args: Dict[str, Any]) -> List[str]:
    """Collect the workspace file paths named by a tool's arguments."""
    found = []
    for key in TARGET_PATH_KEYS:
        value = args.get(key)
        if isinstance(value, str):
            found.append(value)
        elif isinstance(value, (list, tuple)):
            found.extend(v for v in value if isinstance(v, str))
    return sorted(set(p for p in found if p))


def _confined(workspace: str, rel_or_abs: str) -> str:
    """Resolve a path and require it to stay inside the workspace."""
    root = os.path.realpath(workspace)
    candidate = os.path.realpath(os.path.join(root, rel_or_abs))
    try:
        inside = os.path.commonpath([root, candidate]) == root
    except ValueError:
        inside = False
    if not inside or candidate == root:
        raise ValueError(f"path escapes the workspace: {rel_or_abs!r}")
    return candidate


def compute_file_digest(workspace: str, paths: Iterable[str]) -> str:
    """sha256 over (path, content) for every target path.

    Missing files are bound as missing, so creating one later also makes the
    receipt stale. Raises ValueError for paths outside the workspace.
    """
    h = hashlib.sha256(b"soma-file-digest-v1\0")
    for rel in sorted(set(paths)):
        resolved = _confined(workspace, rel)
        h.update(rel.encode("utf-8") + b"\0")
        if os.path.isfile(resolved):
            with open(resolved, "rb") as f:
                h.update(hashlib.sha256(f.read()).digest())
        else:
            h.update(b"<missing>")
        h.update(b"\0")
    return h.hexdigest()


def compute_cell_digest(workspace: str) -> str:
    """Return the canonical aggregate fingerprint of governance cell bytes."""
    return inventory_cells(workspace).fingerprint


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
        
        import hmac
        is_valid = (
            hmac.compare_digest(stored["session_id"], session_id) and
            hmac.compare_digest(stored["workspace"], workspace) and
            hmac.compare_digest(stored["operation"], operation) and
            hmac.compare_digest(stored["args_hash"], _hash_args(args)) and
            hmac.compare_digest(stored["file_digest"], file_digest) and
            hmac.compare_digest(stored["cell_digest"], cell_digest)
        )
        
        # Purge receipt only when verification succeeds and consume=True
        if is_valid and consume:
            _receipt_store.pop(receipt_id, None)
            
        return is_valid

def clear_receipts():
    """Clear all receipts (simulates process restart invalidation)."""
    with _receipt_lock:
        _receipt_store.clear()
