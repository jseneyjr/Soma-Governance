import secrets
import json
import os
import time
import threading
import hashlib
import hmac
from pathlib import Path
from typing import Dict, Any, Iterable, List, Optional

from soma_core.cell_inventory import inventory_cells
from soma_core.workspace import confine_path

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
MAX_RECEIPTS = 1000
DEFAULT_TTL_SECONDS = 3600.0  # 1 hour


def _prune_expired_locked(now: float) -> None:
    """Evict expired receipts and enforce MAX_RECEIPTS cap (caller must hold _receipt_lock)."""
    expired = [
        rid for rid, data in _receipt_store.items()
        if data.get("expires_at") is not None and now > data["expires_at"]
    ]
    for rid in expired:
        _receipt_store.pop(rid, None)

    if len(_receipt_store) >= MAX_RECEIPTS:
        # Evict oldest entries by creation time
        sorted_by_age = sorted(
            _receipt_store.items(),
            key=lambda item: item[1].get("created_at", 0)
        )
        to_evict = len(_receipt_store) - MAX_RECEIPTS + 1
        for rid, _ in sorted_by_age[:to_evict]:
            _receipt_store.pop(rid, None)


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


def _safe_compare(a: Any, b: Any) -> bool:
    """Safely compare two strings or byte sequences in constant time without non-ASCII crash."""
    if not isinstance(a, (str, bytes)) or not isinstance(b, (str, bytes)):
        return False
    a_bytes = a.encode("utf-8") if isinstance(a, str) else a
    b_bytes = b.encode("utf-8") if isinstance(b, str) else b
    return hmac.compare_digest(a_bytes, b_bytes)


def _confined(workspace: str, rel_or_abs: str) -> str:
    """Resolve a path and require it to stay inside the workspace using single-authority confinement."""
    resolved, _ = confine_path(rel_or_abs, workspace)
    return resolved


def compute_file_digest(workspace: str, paths: Iterable[str]) -> str:
    """sha256 over (path, content) for every target path.

    Missing files are bound as missing, so creating one later also makes the
    receipt stale. Raises ValueError for paths outside the workspace.
    """
    ws_root = Path(workspace).resolve()
    seen = set()
    canonical_items = []
    for p in paths:
        resolved = _confined(workspace, p)
        canonical_rel = Path(resolved).resolve().relative_to(ws_root).as_posix()
        if canonical_rel not in seen:
            seen.add(canonical_rel)
            canonical_items.append((canonical_rel, resolved))
    canonical_items.sort(key=lambda x: x[0])

    h = hashlib.sha256(b"soma-file-digest-v1\0")
    for rel_posix, resolved in canonical_items:
        h.update(rel_posix.encode("utf-8") + b"\0")
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
        "created_at": now,
        "expires_at": (now + ttl_seconds) if ttl_seconds is not None else (now + DEFAULT_TTL_SECONDS),
    }
    with _receipt_lock:
        _prune_expired_locked(now)
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
    if (
        not isinstance(receipt_id, str)
        or not isinstance(session_id, str)
        or not isinstance(workspace, str)
        or not isinstance(operation, str)
        or not isinstance(file_digest, str)
        or not isinstance(cell_digest, str)
        or not isinstance(args, dict)
    ):
        return False

    with _receipt_lock:
        _prune_expired_locked(time.time())
        if receipt_id not in _receipt_store:
            return False
            
        stored = _receipt_store[receipt_id]
        
        # Check expiration
        if stored.get("expires_at") is not None and time.time() > stored["expires_at"]:
            _receipt_store.pop(receipt_id, None)
            return False
        
        is_valid = (
            _safe_compare(stored["session_id"], session_id) and
            _safe_compare(stored["workspace"], workspace) and
            _safe_compare(stored["operation"], operation) and
            _safe_compare(stored["args_hash"], _hash_args(args)) and
            _safe_compare(stored["file_digest"], file_digest) and
            _safe_compare(stored["cell_digest"], cell_digest)
        )
        
        # Single-use: burn receipt upon redemption attempt when consume=True (C-03)
        if consume:
            _receipt_store.pop(receipt_id, None)
            
        return is_valid

def clear_receipts():
    """Clear all receipts (simulates process restart invalidation)."""
    with _receipt_lock:
        _receipt_store.clear()


__all__ = [
    "DEFAULT_TTL_SECONDS",
    "MAX_RECEIPTS",
    "SERVER_OWNED_KEYS",
    "TARGET_PATH_KEYS",
    "clear_receipts",
    "compute_cell_digest",
    "compute_file_digest",
    "issue_receipt",
    "strip_server_owned",
    "target_paths",
    "verify_receipt",
]

