"""Tests for the evidence collector.

Behavioral contracts:
1. Given a transcript with tool calls, correctly detect rule compliance
2. Given compliance data + outcomes, produce valid evidence.json
3. Never read or store source code — only aggregate metrics
4. Handle edge cases: empty transcripts, missing rules, zero samples

Written BEFORE the evidence collector module exists — tests will
fail with ImportError initially, then with assertion errors once
stubs are created.
"""

import json
from pathlib import Path

import pytest


# ── Fixture: synthetic transcripts ──────────────────────────────────


def _write_transcript(tmp_path: Path, steps: list[dict]) -> Path:
    """Helper to write a list of step dicts as JSONL transcript."""
    path = tmp_path / "transcript.jsonl"
    path.write_text("\n".join(json.dumps(s) for s in steps) + "\n")
    return path


@pytest.fixture
def compliant_transcript(tmp_path):
    """Transcript where agent reads a file BEFORE writing to it."""
    steps = [
        {
            "step_index": 0, "source": "MODEL", "type": "PLANNER_RESPONSE",
            "created_at": "2026-01-01T00:00:00Z",
            "tool_calls": [
                {"name": "view_file",
                 "args": {"AbsolutePath": "/repo/src/main.py"}},
            ],
        },
        {
            "step_index": 1, "source": "MODEL", "type": "VIEW_FILE",
            "created_at": "2026-01-01T00:00:01Z",
            "content": "file contents...",
        },
        {
            "step_index": 2, "source": "MODEL", "type": "PLANNER_RESPONSE",
            "created_at": "2026-01-01T00:00:02Z",
            "tool_calls": [
                {"name": "replace_file_content",
                 "args": {"TargetFile": "/repo/src/main.py",
                          "TargetContent": "old", "ReplacementContent": "new"}},
            ],
        },
    ]
    return _write_transcript(tmp_path, steps)


@pytest.fixture
def non_compliant_transcript(tmp_path):
    """Transcript where agent writes WITHOUT reading the file first."""
    steps = [
        {
            "step_index": 0, "source": "MODEL", "type": "PLANNER_RESPONSE",
            "created_at": "2026-01-01T00:00:00Z",
            "tool_calls": [
                {"name": "replace_file_content",
                 "args": {"TargetFile": "/repo/src/main.py",
                          "TargetContent": "old", "ReplacementContent": "new"}},
            ],
        },
    ]
    return _write_transcript(tmp_path, steps)


@pytest.fixture
def mixed_transcript(tmp_path):
    """Transcript with both compliant and non-compliant writes."""
    steps = [
        # Read file A
        {
            "step_index": 0, "source": "MODEL", "type": "PLANNER_RESPONSE",
            "created_at": "2026-01-01T00:00:00Z",
            "tool_calls": [
                {"name": "grep_search",
                 "args": {"SearchPath": "/repo/src/a.py", "Query": "def"}},
            ],
        },
        # Write file A (compliant — read first)
        {
            "step_index": 1, "source": "MODEL", "type": "PLANNER_RESPONSE",
            "created_at": "2026-01-01T00:00:01Z",
            "tool_calls": [
                {"name": "replace_file_content",
                 "args": {"TargetFile": "/repo/src/a.py",
                          "TargetContent": "x", "ReplacementContent": "y"}},
            ],
        },
        # Write file B (non-compliant — no prior read)
        {
            "step_index": 2, "source": "MODEL", "type": "PLANNER_RESPONSE",
            "created_at": "2026-01-01T00:00:02Z",
            "tool_calls": [
                {"name": "replace_file_content",
                 "args": {"TargetFile": "/repo/src/b.py",
                          "TargetContent": "x", "ReplacementContent": "y"}},
            ],
        },
    ]
    return _write_transcript(tmp_path, steps)


@pytest.fixture
def empty_transcript(tmp_path):
    """Empty transcript file."""
    path = tmp_path / "transcript.jsonl"
    path.write_text("")
    return path


@pytest.fixture
def write_only_transcript(tmp_path):
    """Transcript using write_to_file (new file creation — no read expected)."""
    steps = [
        {
            "step_index": 0, "source": "MODEL", "type": "PLANNER_RESPONSE",
            "created_at": "2026-01-01T00:00:00Z",
            "tool_calls": [
                {"name": "write_to_file",
                 "args": {"TargetFile": "/repo/src/new_file.py",
                          "CodeContent": "print('hello')"}},
            ],
        },
    ]
    return _write_transcript(tmp_path, steps)


# ── Contract: Compliance Detection ──────────────────────────────────


class TestComplianceDetection:
    """The collector must correctly classify tool-call patterns as
    compliant or non-compliant for each rule."""

    def test_detects_read_before_write_compliance(self, compliant_transcript):
        from enzymes.evidence_collector import check_compliance

        results = check_compliance(
            compliant_transcript, rule_id="read-before-write"
        )
        assert results["compliant_count"] >= 1
        assert results["non_compliant_count"] == 0

    def test_detects_read_before_write_violation(self, non_compliant_transcript):
        from enzymes.evidence_collector import check_compliance

        results = check_compliance(
            non_compliant_transcript, rule_id="read-before-write"
        )
        assert results["non_compliant_count"] >= 1
        assert results["compliant_count"] == 0

    def test_detects_mixed_compliance(self, mixed_transcript):
        from enzymes.evidence_collector import check_compliance

        results = check_compliance(
            mixed_transcript, rule_id="read-before-write"
        )
        assert results["compliant_count"] >= 1, "Should detect compliant write to a.py"
        assert results["non_compliant_count"] >= 1, "Should detect non-compliant write to b.py"

    def test_empty_transcript_returns_zero(self, empty_transcript):
        from enzymes.evidence_collector import check_compliance

        results = check_compliance(
            empty_transcript, rule_id="read-before-write"
        )
        assert results["compliant_count"] == 0
        assert results["non_compliant_count"] == 0

    def test_unknown_rule_returns_zero(self, compliant_transcript):
        from enzymes.evidence_collector import check_compliance

        results = check_compliance(
            compliant_transcript, rule_id="nonexistent-rule-xyz"
        )
        assert results["compliant_count"] == 0
        assert results["non_compliant_count"] == 0

    def test_write_to_file_not_flagged_as_violation(self, write_only_transcript):
        """Creating new files (write_to_file) should NOT count as a
        read-before-write violation — the rule applies to modifications
        of existing files (replace_file_content / multi_replace_file_content)."""
        from enzymes.evidence_collector import check_compliance

        results = check_compliance(
            write_only_transcript, rule_id="read-before-write"
        )
        # No modifications occurred, so no compliance events at all
        assert results["compliant_count"] == 0
        assert results["non_compliant_count"] == 0

    def test_grep_search_counts_as_read(self, mixed_transcript):
        """grep_search on a file's path should satisfy the 'read' requirement."""
        from enzymes.evidence_collector import check_compliance

        results = check_compliance(
            mixed_transcript, rule_id="read-before-write"
        )
        # a.py was grep_searched then written — should be compliant
        assert results["compliant_count"] >= 1


# ── Contract: Evidence Aggregation ──────────────────────────────────


class TestEvidenceAggregation:
    """Given per-session compliance data, produce valid aggregate statistics."""

    def test_evidence_has_required_fields(self):
        from enzymes.evidence_collector import aggregate_evidence

        observations = [
            {"rule_id": "read-before-write", "compliant": True,
             "session_steps": 36, "session_fpsr": 0.94},
            {"rule_id": "read-before-write", "compliant": True,
             "session_steps": 42, "session_fpsr": 0.88},
            {"rule_id": "read-before-write", "compliant": False,
             "session_steps": 547, "session_fpsr": 0.31},
        ]
        evidence = aggregate_evidence(observations)
        rbw = evidence["read-before-write"]
        assert "samples" in rbw
        assert "compliant_fpsr" in rbw
        assert "non_compliant_fpsr" in rbw
        assert "compliant_avg_steps" in rbw
        assert "non_compliant_avg_steps" in rbw
        assert "rework_multiplier" in rbw

    def test_correct_sample_count(self):
        from enzymes.evidence_collector import aggregate_evidence

        observations = [
            {"rule_id": "r1", "compliant": True,
             "session_steps": 10, "session_fpsr": 1.0},
            {"rule_id": "r1", "compliant": False,
             "session_steps": 50, "session_fpsr": 0.5},
            {"rule_id": "r1", "compliant": True,
             "session_steps": 15, "session_fpsr": 0.9},
        ]
        evidence = aggregate_evidence(observations)
        assert evidence["r1"]["samples"] == 3

    def test_correct_averages(self):
        from enzymes.evidence_collector import aggregate_evidence

        observations = [
            {"rule_id": "r1", "compliant": True,
             "session_steps": 30, "session_fpsr": 0.90},
            {"rule_id": "r1", "compliant": True,
             "session_steps": 40, "session_fpsr": 0.80},
            {"rule_id": "r1", "compliant": False,
             "session_steps": 100, "session_fpsr": 0.20},
        ]
        evidence = aggregate_evidence(observations)
        r = evidence["r1"]
        assert r["compliant_avg_steps"] == pytest.approx(35.0)
        assert r["compliant_fpsr"] == pytest.approx(0.85)
        assert r["non_compliant_avg_steps"] == pytest.approx(100.0)
        assert r["non_compliant_fpsr"] == pytest.approx(0.20)

    def test_rework_multiplier_calculation(self):
        from enzymes.evidence_collector import aggregate_evidence

        observations = [
            {"rule_id": "r1", "compliant": True,
             "session_steps": 30, "session_fpsr": 1.0},
            {"rule_id": "r1", "compliant": False,
             "session_steps": 90, "session_fpsr": 0.5},
        ]
        evidence = aggregate_evidence(observations)
        # rework_multiplier = non_compliant_avg / compliant_avg = 90/30 = 3.0
        assert evidence["r1"]["rework_multiplier"] == pytest.approx(3.0)

    def test_confidence_low_with_few_samples(self):
        from enzymes.evidence_collector import aggregate_evidence

        observations = [
            {"rule_id": "r1", "compliant": True,
             "session_steps": 10, "session_fpsr": 1.0},
        ]
        evidence = aggregate_evidence(observations)
        assert evidence["r1"]["confidence"] == "low"

    def test_confidence_high_with_many_samples(self):
        from enzymes.evidence_collector import aggregate_evidence

        observations = [
            {"rule_id": "r1", "compliant": (i % 3 != 0),
             "session_steps": 30 + i, "session_fpsr": 0.8}
            for i in range(15)
        ]
        evidence = aggregate_evidence(observations)
        assert evidence["r1"]["confidence"] == "high"

    def test_multiple_rules_segregated(self):
        from enzymes.evidence_collector import aggregate_evidence

        observations = [
            {"rule_id": "r1", "compliant": True,
             "session_steps": 10, "session_fpsr": 1.0},
            {"rule_id": "r2", "compliant": False,
             "session_steps": 100, "session_fpsr": 0.1},
        ]
        evidence = aggregate_evidence(observations)
        assert "r1" in evidence
        assert "r2" in evidence
        assert evidence["r1"]["samples"] == 1
        assert evidence["r2"]["samples"] == 1

    def test_empty_observations(self):
        from enzymes.evidence_collector import aggregate_evidence

        evidence = aggregate_evidence([])
        assert evidence == {}

    def test_all_compliant_no_division_error(self):
        """When all observations are compliant, non_compliant fields
        should have safe defaults (not raise ZeroDivisionError)."""
        from enzymes.evidence_collector import aggregate_evidence

        observations = [
            {"rule_id": "r1", "compliant": True,
             "session_steps": 30, "session_fpsr": 0.9},
            {"rule_id": "r1", "compliant": True,
             "session_steps": 40, "session_fpsr": 0.8},
        ]
        evidence = aggregate_evidence(observations)
        r = evidence["r1"]
        # Should not crash; non-compliant fields should be None or 0
        assert r["non_compliant_avg_steps"] is None or r["non_compliant_avg_steps"] == 0
        assert r["non_compliant_fpsr"] is None or r["non_compliant_fpsr"] == 0


# ── Contract: Security Invariant ────────────────────────────────────


class TestSecurityInvariant:
    """The evidence collector must NEVER store source code, file paths,
    or diff content in its output."""

    def test_evidence_contains_no_file_paths(self):
        from enzymes.evidence_collector import aggregate_evidence

        observations = [
            {"rule_id": "read-before-write", "compliant": True,
             "session_steps": 36, "session_fpsr": 0.94},
        ]
        evidence = aggregate_evidence(observations)
        serialized = json.dumps(evidence)
        assert "/home/" not in serialized
        assert "/repo/" not in serialized
        assert "/src/" not in serialized

    def test_evidence_contains_no_code(self):
        from enzymes.evidence_collector import aggregate_evidence

        observations = [
            {"rule_id": "r1", "compliant": True,
             "session_steps": 10, "session_fpsr": 1.0},
        ]
        evidence = aggregate_evidence(observations)
        serialized = json.dumps(evidence)
        assert "def " not in serialized
        assert "import " not in serialized
        assert "class " not in serialized

    def test_check_compliance_returns_only_counts(self, compliant_transcript):
        """check_compliance must return only aggregate counts, not
        file paths or code content from the transcript."""
        from enzymes.evidence_collector import check_compliance

        results = check_compliance(
            compliant_transcript, rule_id="read-before-write"
        )
        serialized = json.dumps(results)
        assert "/repo/" not in serialized
        assert "main.py" not in serialized
        assert "file contents" not in serialized
