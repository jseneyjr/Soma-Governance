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
