"""Integration tests for the Layer 1 runner + persistence checker.

Validates against the actual Soma codebase (post-fix) and against
synthetic pre-fix scenarios.
"""
import os
import sys
import textwrap
import tempfile

import pytest

# tests/test_verification/ → tests/ → REPO_ROOT
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from immune_system.verification import ToolEvidence
from immune_system.verification import persistence_checker
from immune_system.verification import call_graph
from immune_system.verification import runner


class TestPersistenceChecker:
    """Test the persistence completeness checker against real and synthetic code."""

    def test_post_fix_cell_promote_passes(self):
        """After v0.30 fixes, cell_promote.py should have no persistence gaps."""
        filepath = os.path.join(REPO_ROOT, "enzymes", "cell_promote.py")
        result = persistence_checker.check(filepath, "fitness")
        assert result.verdict is True, f"Expected PASS, got: {result.detail}"
        assert result.tool == "persistence_checker"

    def test_synthetic_gap_detected(self, tmp_path):
        """A file that mutates a key but doesn't serialize it should FAIL."""
        code = textwrap.dedent("""\
            def save(data):
                fitness = data.get('fitness', {})
                fitness['score'] = 0.5
                fitness['secret_key'] = 42  # not serialized!

                for line in lines:
                    if line.startswith('score:'):
                        line = f"score: {fitness['score']}"
                # secret_key never handled in serialization
        """)
        filepath = tmp_path / "test_file.py"
        filepath.write_text(code)

        result = persistence_checker.check(str(filepath), "fitness")
        assert result.verdict is False
        assert "secret_key" in result.detail

    def test_excluded_keys_not_flagged(self, tmp_path):
        """Keys in the exclude list should not be flagged as gaps."""
        code = textwrap.dedent("""\
            def process(data):
                fitness = data.get('fitness', {})
                fitness['cached_value'] = compute()  # intentionally in-memory only

                for line in lines:
                    pass  # no serialization at all
        """)
        filepath = tmp_path / "test_file.py"
        filepath.write_text(code)

        result = persistence_checker.check(str(filepath), "fitness", exclude={"cached_value"})
        assert result.verdict is True

    def test_no_mutations_passes(self, tmp_path):
        """A file with no dict mutations should pass trivially."""
        code = "x = 1\ny = 2\n"
        filepath = tmp_path / "empty.py"
        filepath.write_text(code)

        result = persistence_checker.check(str(filepath), "fitness")
        assert result.verdict is True


class TestCallGraph:
    """Test the call graph completeness checker."""

    def test_bayesian_score_has_callers(self):
        """bayesian_score.py's function should have callers in the repo."""
        filepath = os.path.join(REPO_ROOT, "enzymes", "bayesian_score.py")
        result = call_graph.check(filepath, REPO_ROOT)
        assert result.verdict is True, f"Expected PASS: {result.detail}"

    def test_synthetic_orphan_detected(self, tmp_path):
        """A function with no call sites should be flagged."""
        code = textwrap.dedent("""\
            def orphan_function():
                pass

            def another_orphan():
                pass
        """)
        filepath = tmp_path / "orphan.py"
        filepath.write_text(code)

        result = call_graph.check(str(filepath), str(tmp_path))
        assert result.verdict is False
        assert "orphan_function" in result.detail or "another_orphan" in result.detail


class TestLayer1Runner:
    """Test the Layer 1 orchestrator."""

    def test_runner_returns_results(self):
        """Runner should return ToolEvidence list for changed files."""
        results = runner.run_layer1(
            changed_files=["enzymes/cell_promote.py"],
            repo_root=REPO_ROOT,
            persistence_targets=[("enzymes/cell_promote.py", "fitness")],
        )
        assert len(results) >= 2  # persistence + call_graph
        assert all(isinstance(r, ToolEvidence) for r in results)

    def test_gate_verdict_all_pass(self):
        """Gate should pass when all tools pass."""
        results = [
            ToolEvidence("t1", "f1", True, "ok"),
            ToolEvidence("t2", "f2", True, "ok"),
        ]
        assert runner.gate_verdict(results) is True

    def test_gate_verdict_any_fail(self):
        """Gate should fail when any tool fails."""
        results = [
            ToolEvidence("t1", "f1", True, "ok"),
            ToolEvidence("t2", "f2", False, "gap found"),
        ]
        assert runner.gate_verdict(results) is False

    def test_format_summary_pass(self):
        results = [ToolEvidence("t1", "f1", True, "ok")]
        summary = runner.format_summary(results)
        assert "1/1 PASSED" in summary

    def test_format_summary_fail(self):
        results = [
            ToolEvidence("t1", "f1", True, "ok"),
            ToolEvidence("t2", "f2", False, "gap"),
        ]
        summary = runner.format_summary(results)
        assert "1/2 FAILED" in summary
