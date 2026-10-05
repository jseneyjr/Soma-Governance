import pytest
from soma_core.receipts import issue_receipt, verify_receipt, clear_receipts

def test_issue_and_verify_receipt():
    # Failing test to drive receipt implementation
    args = {"test": "data"}
    receipt_id = issue_receipt("session_1", "workspace_1", "op_1", args, "file_digest", "cell_digest")
    assert receipt_id is not None
    assert type(receipt_id) == str
    
    # Verify should succeed with identical parameters
    assert verify_receipt(receipt_id, "session_1", "workspace_1", "op_1", args, "file_digest", "cell_digest") == True
    
    # Verify should fail with wrong session
    assert verify_receipt(receipt_id, "session_2", "workspace_1", "op_1", args, "file_digest", "cell_digest") == False

def test_receipt_invalidation():
    # This should fail if state is not kept
    receipt_id = issue_receipt("s1", "w1", "o1", {}, "fd", "cd")
    clear_receipts()
    assert verify_receipt(receipt_id, "s1", "w1", "o1", {}, "fd", "cd") == False

def test_receipt_ttl_expiration():
    import time
    receipt_id = issue_receipt("s1", "w1", "o1", {}, "fd", "cd", ttl_seconds=0.01)
    time.sleep(0.02)
    assert verify_receipt(receipt_id, "s1", "w1", "o1", {}, "fd", "cd") == False

def test_receipt_capacity_cap(monkeypatch):
    import soma_core.receipts as r_mod
    clear_receipts()
    monkeypatch.setattr(r_mod, "MAX_RECEIPTS", 5)

    rids = []
    for i in range(10):
        rid = issue_receipt(f"s{i}", "w", "op", {}, "fd", "cd")
        rids.append(rid)

    # Store size must not exceed MAX_RECEIPTS
    assert len(r_mod._receipt_store) <= 5
    # The oldest receipts should have been evicted
    assert verify_receipt(rids[0], "s0", "w", "op", {}, "fd", "cd") == False
    # The newest receipt should still be valid
    assert verify_receipt(rids[-1], "s9", "w", "op", {}, "fd", "cd") == True
    clear_receipts()

