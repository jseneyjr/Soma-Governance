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


def test_verify_receipt_with_invalid_types():
    assert verify_receipt(None, "s1", "w1", "o1", {}, "fd", "cd") is False
    assert verify_receipt(12345, "s1", "w1", "o1", {}, "fd", "cd") is False
    rid = issue_receipt("s1", "w1", "o1", {}, "fd", "cd")
    try:
        assert verify_receipt(rid, None, "w1", "o1", {}, "fd", "cd") is False
        assert verify_receipt(rid, 123, "w1", "o1", {}, "fd", "cd") is False
        assert verify_receipt(rid, "s1", None, "o1", {}, "fd", "cd") is False
        assert verify_receipt(rid, "s1", "w1", None, {}, "fd", "cd") is False
        assert verify_receipt(rid, "s1", "w1", "o1", None, "fd", "cd") is False
        assert verify_receipt(rid, "s1", "w1", "o1", {}, None, "cd") is False
        assert verify_receipt(rid, "s1", "w1", "o1", {}, "fd", None) is False
    finally:
        clear_receipts()


def test_verify_receipt_burn_on_success_only():
    """Verify that consume=True does not burn receipt if verification fails."""
    clear_receipts()
    try:
        rid = issue_receipt("sess_auth", "ws_1", "write_op", {"file": "a.txt"}, "fd_1", "cd_1")

        # Invalid call with consume=True: wrong session -> returns False, MUST NOT burn receipt
        assert verify_receipt(rid, "wrong_sess", "ws_1", "write_op", {"file": "a.txt"}, "fd_1", "cd_1", consume=True) is False

        # Invalid call with wrong args -> returns False, MUST NOT burn receipt
        assert verify_receipt(rid, "sess_auth", "ws_1", "write_op", {"file": "b.txt"}, "fd_1", "cd_1", consume=True) is False

        # Legitimate caller with consume=True -> returns True, burns receipt
        assert verify_receipt(rid, "sess_auth", "ws_1", "write_op", {"file": "a.txt"}, "fd_1", "cd_1", consume=True) is True

        # Subsequent redemption attempt must fail because receipt is burned
        assert verify_receipt(rid, "sess_auth", "ws_1", "write_op", {"file": "a.txt"}, "fd_1", "cd_1", consume=True) is False
    finally:
        clear_receipts()


def test_compute_file_digest_path_normalization(tmp_path):
    from soma_core.receipts import compute_file_digest

    sub = tmp_path / "sub"
    sub.mkdir()
    target = sub / "file.txt"
    target.write_text("content", encoding="utf-8")

    digest_clean = compute_file_digest(str(tmp_path), ["sub/file.txt"])
    digest_dot = compute_file_digest(str(tmp_path), ["sub/./file.txt"])
    digest_dups = compute_file_digest(str(tmp_path), ["sub/file.txt", "sub/./file.txt"])

    assert digest_clean == digest_dot
    assert digest_clean == digest_dups



