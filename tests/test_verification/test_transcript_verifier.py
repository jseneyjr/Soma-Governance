"""TDD tests for transcript_verifier.py — orchestrator-level claim verification.

Behavioral contract: the orchestrator reads subagent transcripts and
independently extracts metrics (pytest runs, pass/fail counts, file writes)
to verify subagent self-reported claims. Divergences between claimed and
verified results are flagged.
"""
import os
import sys
import json
import textwrap

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from immune_system.verification import ToolEvidence


class TestMetricExtraction:
    """Contract: extract_metrics parses transcript JSONL into objective counts."""

    def test_counts_pytest_runs(self, tmp_path):
        """Must count the number of distinct pytest invocations."""
        from immune_system.verification.transcript_verifier import extract_metrics

        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text('\n'.join([
            json.dumps({"step_index": 0, "source": "MODEL", "type": "WRITE_FILE", "status": "DONE", "content": "Created file mutation_tester.py"}),
            json.dumps({"step_index": 1, "source": "MODEL", "type": "RUN_COMMAND", "status": "DONE", "exit_code": 0, "content": "pytest tests/test_mutation.py\n6 passed in 2.0s"}),
        ]))

        metrics = extract_metrics(str(transcript))
        assert metrics.pytest_runs == 1

    def test_counts_multiple_pytest_runs(self, tmp_path):
        """Multiple pytest invocations should all be counted."""
        from immune_system.verification.transcript_verifier import extract_metrics

        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text('\n'.join([
            json.dumps({"step_index": 0, "source": "MODEL", "type": "WRITE_FILE", "status": "DONE", "content": "Created file"}),
            json.dumps({"step_index": 1, "source": "MODEL", "type": "RUN_COMMAND", "status": "DONE", "exit_code": 1, "content": "pytest\n2 failed, 2 passed"}),
            json.dumps({"step_index": 2, "source": "MODEL", "type": "WRITE_FILE", "status": "DONE", "content": "Fixed file"}),
            json.dumps({"step_index": 3, "source": "MODEL", "type": "RUN_COMMAND", "status": "DONE", "exit_code": 0, "content": "pytest\n4 passed"}),
        ]))

        metrics = extract_metrics(str(transcript))
        assert metrics.pytest_runs == 2

    def test_extracts_first_run_results(self, tmp_path):
        """Must capture pass/fail counts from the FIRST pytest run."""
        from immune_system.verification.transcript_verifier import extract_metrics

        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text('\n'.join([
            json.dumps({"step_index": 0, "source": "MODEL", "type": "RUN_COMMAND", "status": "DONE", "exit_code": 1, "content": "pytest\n2 failed, 4 passed"}),
            json.dumps({"step_index": 1, "source": "MODEL", "type": "RUN_COMMAND", "status": "DONE", "exit_code": 0, "content": "pytest\n6 passed"}),
        ]))

        metrics = extract_metrics(str(transcript))
        assert metrics.first_run_passed == 4
        assert metrics.first_run_failed == 2

    def test_extracts_final_run_results(self, tmp_path):
        """Must capture pass/fail counts from the LAST pytest run."""
        from immune_system.verification.transcript_verifier import extract_metrics

        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text('\n'.join([
            json.dumps({"step_index": 0, "source": "MODEL", "type": "RUN_COMMAND", "status": "DONE", "exit_code": 1, "content": "pytest\n2 failed, 4 passed"}),
            json.dumps({"step_index": 1, "source": "MODEL", "type": "RUN_COMMAND", "status": "DONE", "exit_code": 0, "content": "pytest\n6 passed"}),
        ]))

        metrics = extract_metrics(str(transcript))
        assert metrics.final_passed == 6
        assert metrics.final_failed == 0

    def test_counts_file_writes(self, tmp_path):
        """Must count write_to_file, replace_file_content, and multi_replace operations."""
        from immune_system.verification.transcript_verifier import extract_metrics

        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text('\n'.join([
            json.dumps({"step_index": 0, "source": "MODEL", "type": "WRITE_FILE", "status": "DONE", "content": "write_to_file created file"}),
            json.dumps({"step_index": 1, "source": "MODEL", "type": "RUN_COMMAND", "status": "DONE", "exit_code": 1, "content": "pytest\n2 failed"}),
            json.dumps({"step_index": 2, "source": "MODEL", "type": "EDIT_FILE", "status": "DONE", "content": "replace_file_content fixed bug"}),
            json.dumps({"step_index": 3, "source": "MODEL", "type": "EDIT_FILE", "status": "DONE", "content": "multi_replace fixed another bug"}),
            json.dumps({"step_index": 4, "source": "MODEL", "type": "RUN_COMMAND", "status": "DONE", "exit_code": 0, "content": "pytest\n4 passed"}),
        ]))

        metrics = extract_metrics(str(transcript))
        assert metrics.file_writes == 3

    def test_computes_fix_cycles(self, tmp_path):
        """fix_cycles = number of write operations AFTER the first failed test run."""
        from immune_system.verification.transcript_verifier import extract_metrics

        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text('\n'.join([
            json.dumps({"step_index": 0, "source": "MODEL", "type": "WRITE_FILE", "status": "DONE", "content": "Initial write"}),
            json.dumps({"step_index": 1, "source": "MODEL", "type": "RUN_COMMAND", "status": "DONE", "exit_code": 1, "content": "pytest\n2 failed, 2 passed"}),
            json.dumps({"step_index": 2, "source": "MODEL", "type": "EDIT_FILE", "status": "DONE", "content": "Fix 1"}),
            json.dumps({"step_index": 3, "source": "MODEL", "type": "EDIT_FILE", "status": "DONE", "content": "Fix 2"}),
            json.dumps({"step_index": 4, "source": "MODEL", "type": "RUN_COMMAND", "status": "DONE", "exit_code": 0, "content": "pytest\n4 passed"}),
        ]))

        metrics = extract_metrics(str(transcript))
        assert metrics.fix_cycles == 2

    def test_zero_fix_cycles_on_first_pass(self, tmp_path):
        """A lane that passes first try should have 0 fix cycles."""
        from immune_system.verification.transcript_verifier import extract_metrics

        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text('\n'.join([
            json.dumps({"step_index": 0, "source": "MODEL", "type": "WRITE_FILE", "status": "DONE", "content": "Created file"}),
            json.dumps({"step_index": 1, "source": "MODEL", "type": "RUN_COMMAND", "status": "DONE", "exit_code": 0, "content": "pytest\n6 passed"}),
        ]))

        metrics = extract_metrics(str(transcript))
        assert metrics.fix_cycles == 0
        assert metrics.first_run_passed == 6
        assert metrics.first_run_failed == 0


class TestClaimVerification:
    """Contract: verify_claim compares metrics against subagent self-report."""

    def test_honest_first_pass_verified(self, tmp_path):
        """When subagent claims first-pass and transcript confirms, verdict=True."""
        from immune_system.verification.transcript_verifier import extract_metrics, verify_claim

        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text('\n'.join([
            json.dumps({"step_index": 0, "source": "MODEL", "type": "WRITE_FILE", "status": "DONE", "content": "Created file"}),
            json.dumps({"step_index": 1, "source": "MODEL", "type": "RUN_COMMAND", "status": "DONE", "exit_code": 0, "content": "pytest\n6 passed"}),
        ]))

        metrics = extract_metrics(str(transcript))
        result = verify_claim(
            metrics=metrics,
            claimed_first_pass=True,
            claimed_tests_passed=6,
            agent_role="test_agent",
        )
        assert result.verdict is True
        assert "verified" in result.detail.lower() or "confirmed" in result.detail.lower()

    def test_false_first_pass_caught(self, tmp_path):
        """When subagent claims first-pass but had failures, verdict=False."""
        from immune_system.verification.transcript_verifier import extract_metrics, verify_claim

        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text('\n'.join([
            json.dumps({"step_index": 0, "source": "MODEL", "type": "WRITE_FILE", "status": "DONE", "content": "Created file"}),
            json.dumps({"step_index": 1, "source": "MODEL", "type": "RUN_COMMAND", "status": "DONE", "exit_code": 1, "content": "pytest\n2 failed, 4 passed"}),
            json.dumps({"step_index": 2, "source": "MODEL", "type": "EDIT_FILE", "status": "DONE", "content": "Fixed"}),
            json.dumps({"step_index": 3, "source": "MODEL", "type": "RUN_COMMAND", "status": "DONE", "exit_code": 0, "content": "pytest\n6 passed"}),
        ]))

        metrics = extract_metrics(str(transcript))
        result = verify_claim(
            metrics=metrics,
            claimed_first_pass=True,
            claimed_tests_passed=6,
            agent_role="test_agent",
        )
        assert result.verdict is False
        assert "2" in result.detail  # Should mention the actual failure count
        assert result.tool == "transcript_verifier"

    def test_inflated_test_count_caught(self, tmp_path):
        """When subagent claims more tests passed than actually did, verdict=False."""
        from immune_system.verification.transcript_verifier import extract_metrics, verify_claim

        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text('\n'.join([
            json.dumps({"step_index": 0, "source": "MODEL", "type": "WRITE_FILE", "status": "DONE", "content": "Created file"}),
            json.dumps({"step_index": 1, "source": "MODEL", "type": "RUN_COMMAND", "status": "DONE", "exit_code": 0, "content": "pytest\n4 passed"}),
        ]))

        metrics = extract_metrics(str(transcript))
        result = verify_claim(
            metrics=metrics,
            claimed_first_pass=True,
            claimed_tests_passed=6,  # Claims 6 but only 4 passed
            agent_role="test_agent",
        )
        assert result.verdict is False
        assert "4" in result.detail  # Should mention actual count


class TestRealTranscripts:
    """Validate against the ACTUAL subagent transcripts from this session."""

    LANE_A = "/home/nseney/.gemini/antigravity/brain/9739cd63-0ab0-4f36-9551-9abc11d4a7cd/.system_generated/logs/transcript.jsonl"
    LANE_B = "/home/nseney/.gemini/antigravity/brain/abbe31f4-341b-4b5d-a7b2-a0a06f004558/.system_generated/logs/transcript.jsonl"
    LANE_C = "/home/nseney/.gemini/antigravity/brain/ffef2cc0-a0f0-46e0-9da5-678126093a73/.system_generated/logs/transcript.jsonl"

    @pytest.mark.skipif(
        not os.path.exists("/home/nseney/.gemini/antigravity/brain/9739cd63-0ab0-4f36-9551-9abc11d4a7cd/.system_generated/logs/transcript.jsonl"),
        reason="Lane A transcript not available"
    )
    def test_lane_a_was_genuine_first_pass(self):
        """Lane A (mutation_tester) claimed first-pass — verify from transcript."""
        from immune_system.verification.transcript_verifier import extract_metrics

        metrics = extract_metrics(self.LANE_A)
        assert metrics.pytest_runs == 1, f"Expected 1 pytest run, got {metrics.pytest_runs}"
        assert metrics.first_run_failed == 0, f"Expected 0 failures, got {metrics.first_run_failed}"
        assert metrics.fix_cycles == 0

    @pytest.mark.skipif(
        not os.path.exists("/home/nseney/.gemini/antigravity/brain/abbe31f4-341b-4b5d-a7b2-a0a06f004558/.system_generated/logs/transcript.jsonl"),
        reason="Lane B transcript not available"
    )
    def test_lane_b_was_not_first_pass(self):
        """Lane B (branch_coverage) should show iteration — verify from transcript."""
        from immune_system.verification.transcript_verifier import extract_metrics

        metrics = extract_metrics(self.LANE_B)
        assert metrics.pytest_runs >= 2, f"Expected >=2 pytest runs, got {metrics.pytest_runs}"
        assert metrics.first_run_failed > 0, f"Expected failures on first run"
        assert metrics.fix_cycles > 0, f"Expected fix cycles > 0"

    @pytest.mark.skipif(
        not os.path.exists("/home/nseney/.gemini/antigravity/brain/ffef2cc0-a0f0-46e0-9da5-678126093a73/.system_generated/logs/transcript.jsonl"),
        reason="Lane C transcript not available"
    )
    def test_lane_c_was_genuine_first_pass(self):
        """Lane C (immune_verify) claimed first-pass — verify from transcript."""
        from immune_system.verification.transcript_verifier import extract_metrics

        metrics = extract_metrics(self.LANE_C)
        assert metrics.pytest_runs == 1, f"Expected 1 pytest run, got {metrics.pytest_runs}"
        assert metrics.first_run_failed == 0, f"Expected 0 failures, got {metrics.first_run_failed}"
        assert metrics.fix_cycles == 0
