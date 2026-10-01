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


# ── 2A: Mutation Tester + Branch Coverage in Runner ─────────────────


class TestRunnerMutationTesterIntegration:
    """run_layer1() should wire mutation_tester with auto-discovery."""

    def test_mutation_targets_explicit(self, tmp_path):
        """When mutation_targets is provided, runner calls mutation_tester."""
        # Create a simple source + test pair
        src = tmp_path / "widget.py"
        src.write_text(textwrap.dedent("""\
            def add(a, b):
                return a + b
        """))
        test = tmp_path / "test_widget.py"
        test.write_text(textwrap.dedent("""\
            from widget import add
            def test_add():
                assert add(1, 2) == 3
        """))

        results = runner.run_layer1(
            changed_files=["widget.py"],
            repo_root=str(tmp_path),
            mutation_targets=[("widget.py", "add", "test_widget.py")],
        )
        mutation_results = [r for r in results if r.tool == "mutation_tester"]
        assert len(mutation_results) >= 1
        assert all(isinstance(r, ToolEvidence) for r in mutation_results)

    def test_mutation_respects_max_mutations(self, tmp_path):
        """Runner should pass max_mutations budget to mutation_tester."""
        src = tmp_path / "calc.py"
        src.write_text(textwrap.dedent("""\
            def multiply(a, b):
                return a * b
            def subtract(a, b):
                return a - b
        """))
        test = tmp_path / "test_calc.py"
        test.write_text(textwrap.dedent("""\
            from calc import multiply, subtract
            def test_multiply():
                assert multiply(3, 4) == 12
            def test_subtract():
                assert subtract(5, 2) == 3
        """))

        results = runner.run_layer1(
            changed_files=["calc.py"],
            repo_root=str(tmp_path),
            mutation_targets=[("calc.py", "multiply", "test_calc.py")],
            max_mutations=2,
        )
        mutation_results = [r for r in results if r.tool == "mutation_tester"]
        assert len(mutation_results) >= 1
        # The detail should reflect the bounded mutation count
        for r in mutation_results:
            assert isinstance(r.detail, str)

    def test_mutation_auto_discovery(self, tmp_path):
        """When mutation_targets is None but test files exist, auto-discover."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "foo.py").write_text("def bar(): return 1 + 2\n")

        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_foo.py").write_text(
            "from src.foo import bar\ndef test_bar():\n    assert bar() == 3\n"
        )

        results = runner.run_layer1(
            changed_files=["src/foo.py"],
            repo_root=str(tmp_path),
            # No explicit mutation_targets — should auto-discover
        )
        # Should attempt to find test_foo.py for foo.py
        tool_names = [r.tool for r in results]
        assert "mutation_tester" in tool_names


class TestRunnerBranchCoverageIntegration:
    """run_layer1() should wire branch_coverage with convention-based mapping."""

    def test_coverage_targets_explicit(self, tmp_path):
        """When coverage_targets is provided, runner calls branch_coverage."""
        src = tmp_path / "widget.py"
        src.write_text("def greet(name):\n    return f'hello {name}'\n")
        test = tmp_path / "test_widget.py"
        test.write_text(
            "from widget import greet\n"
            "def test_greet():\n    assert greet('x') == 'hello x'\n"
        )

        results = runner.run_layer1(
            changed_files=["widget.py"],
            repo_root=str(tmp_path),
            coverage_targets=[("widget.py", "test_widget.py")],
        )
        coverage_results = [r for r in results if r.tool == "branch_coverage"]
        assert len(coverage_results) >= 1
        assert all(isinstance(r, ToolEvidence) for r in coverage_results)

    def test_coverage_auto_pairs_by_convention(self, tmp_path):
        """When coverage_targets is None, auto-pair foo.py -> tests/test_foo.py."""
        (tmp_path / "helper.py").write_text("def x(): return 1\n")
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_helper.py").write_text(
            "from helper import x\ndef test_x():\n    assert x() == 1\n"
        )

        results = runner.run_layer1(
            changed_files=["helper.py"],
            repo_root=str(tmp_path),
        )
        tool_names = [r.tool for r in results]
        assert "branch_coverage" in tool_names

    def test_coverage_skipped_when_no_test_file(self, tmp_path):
        """When no test file found for a source file, skip branch_coverage."""
        (tmp_path / "orphan.py").write_text("def y(): return 2\n")

        results = runner.run_layer1(
            changed_files=["orphan.py"],
            repo_root=str(tmp_path),
        )
        coverage_results = [r for r in results if r.tool == "branch_coverage"]
        # Should not crash — either 0 results or a skip-evidence
        assert all(isinstance(r, ToolEvidence) for r in coverage_results)
