"""TDD tests for branch_coverage.py — AUDITED ground truth.

Audit findings applied:
- test_returns_tool_evidence: strengthened with verdict + target + empty lines
- test_dead_branch_detected: asserts specific uncovered line ranges
- test_reports_uncovered_lines: asserts exact line 3, not just >= 2
- test_full_coverage_passes: asserts empty lines list
"""
import os
import sys
import textwrap

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from immune_system.verification import ToolEvidence


class TestBranchCoverageContract:
    """Behavioral contract for branch_coverage.check()."""

    def test_returns_tool_evidence(self, tmp_path):
        """check() must return passing ToolEvidence for fully covered code."""
        from immune_system.verification import branch_coverage

        src = tmp_path / "target.py"
        src.write_text(textwrap.dedent("""\
            def classify(x):
                if x > 0:
                    return "positive"
                else:
                    return "non-positive"
        """))

        test = tmp_path / "test_target.py"
        test.write_text(textwrap.dedent(f"""\
            import sys
            sys.path.insert(0, '{tmp_path}')
            from target import classify
            def test_positive():
                assert classify(5) == "positive"
            def test_negative():
                assert classify(-1) == "non-positive"
        """))

        result = branch_coverage.check(
            target_file=str(src),
            test_file=str(test),
        )
        assert isinstance(result, ToolEvidence)
        assert result.tool == "branch_coverage"
        assert "target.py" in result.target
        assert result.verdict is True
        assert result.lines == []

    def test_full_coverage_passes(self, tmp_path):
        """When all branches are covered, verdict=True and no uncovered lines."""
        from immune_system.verification import branch_coverage

        src = tmp_path / "target.py"
        src.write_text(textwrap.dedent("""\
            def classify(x):
                if x > 0:
                    return "positive"
                else:
                    return "non-positive"
        """))

        test = tmp_path / "test_target.py"
        test.write_text(textwrap.dedent(f"""\
            import sys
            sys.path.insert(0, '{tmp_path}')
            from target import classify
            def test_positive():
                assert classify(5) == "positive"
            def test_negative():
                assert classify(-1) == "non-positive"
        """))

        result = branch_coverage.check(
            target_file=str(src),
            test_file=str(test),
        )
        assert result.verdict is True
        assert result.lines == []

    def test_dead_branch_detected(self, tmp_path):
        """Uncovered branches must produce verdict=False with specific lines."""
        from immune_system.verification import branch_coverage

        src = tmp_path / "target.py"
        src.write_text(textwrap.dedent("""\
            def classify(x):
                if x > 0:
                    return "positive"
                elif x == 0:
                    return "zero"
                else:
                    return "negative"
        """))

        # Only tests positive — misses zero and negative branches
        test = tmp_path / "test_target.py"
        test.write_text(textwrap.dedent(f"""\
            import sys
            sys.path.insert(0, '{tmp_path}')
            from target import classify
            def test_positive():
                assert classify(5) == "positive"
        """))

        result = branch_coverage.check(
            target_file=str(src),
            test_file=str(test),
        )
        assert result.verdict is False
        # Lines 4-7 (elif/else branches) should be uncovered
        assert any(line in (4, 5, 6, 7) for line in result.lines), \
            f"Expected uncovered branch lines 4-7, got {result.lines}"
        # Line 3 (return "positive") was executed and must NOT be flagged
        assert 3 not in result.lines, \
            f"Covered line 3 was incorrectly flagged: {result.lines}"

    def test_reports_uncovered_lines(self, tmp_path):
        """Result must include the specific uncovered line number."""
        from immune_system.verification import branch_coverage

        src = tmp_path / "target.py"
        src.write_text(textwrap.dedent("""\
            def process(x):
                if x > 10:
                    return "big"
                return "small"
        """))

        # Only tests small path
        test = tmp_path / "test_target.py"
        test.write_text(textwrap.dedent(f"""\
            import sys
            sys.path.insert(0, '{tmp_path}')
            from target import process
            def test_small():
                assert process(5) == "small"
        """))

        result = branch_coverage.check(
            target_file=str(src),
            test_file=str(test),
        )
        assert result.verdict is False
        # Line 3 (return "big") should be uncovered
        assert 3 in result.lines, \
            f"Expected line 3 (return 'big') in uncovered lines, got {result.lines}"
        # Line 4 (return "small") was executed
        assert 4 not in result.lines, \
            f"Line 4 was executed and must not be in uncovered lines: {result.lines}"
