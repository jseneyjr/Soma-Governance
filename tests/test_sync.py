"""Unit tests for soma_core.sync."""
import json
import pytest
from soma_core.sync import (
    check_liveness,
    classify_file,
    is_test_file,
    prompt_llm_translation,
)


def test_sync_liveness_check():
    payload = json.dumps({
        "agents": [
            {
                "name": "worker",
                "dispatched": "2026-10-05T12:00:00Z",
                "timeout_seconds": 3600,
            }
        ]
    })
    rc = check_liveness(payload)
    assert rc == 0


def test_sync_classification():
    assert classify_file("enzymes/bump_version.sh") == "HIGH"
    assert classify_file("genome/testing.md") == "MEDIUM"
    assert classify_file("docs/README.md") == "LOW"
    assert is_test_file("tests/test_sync.py")
    assert not is_test_file("soma_core/sync.py")


def test_sync_hgt_mock_translation():
    res = prompt_llm_translation("draft all combat-capable pawns", mock=True)
    assert "Resource Consolidation" in res
