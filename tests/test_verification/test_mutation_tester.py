"""TDD tests for mutation_tester.py — AUDITED ground truth.

Audit findings applied:
- test_returns_tool_evidence: strengthened with verdict + target assertions
- test_reports_survival_count: regex for numeric survived/total
- test_respects_max_mutations: was TAUTOLOGICAL, now asserts budget cap
"""
import os
import re
import sys
import textwrap

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from immune_system.verification import ToolEvidence


class TestMutationTesterContract:
    """Behavioral contract for mutation_tester.check()."""

    def test_returns_tool_evidence(self, tmp_path):
        """check() must return a passing ToolEvidence for a well-tested function."""
        from immune_system.verification import mutation_tester

        src = tmp_path / "target.py"
        src.write_text(textwrap.dedent("""\
            def add(a, b):
                return a + b
        """))

        test = tmp_path / "test_target.py"
        test.write_text(textwrap.dedent(f"""\
            import sys
            sys.path.insert(0, {str(tmp_path)!r})
            from target import add
            def test_add():
                assert add(2, 3) == 5
        """))

        result = mutation_tester.check(
            target_file=str(src),
            target_function="add",
            test_file=str(test),
        )
        assert isinstance(result, ToolEvidence)
        assert result.tool == "mutation_tester"
        assert "add" in result.target
        assert result.verdict is True
        assert result.lines == []  # No surviving mutations

    def test_catches_tautological_test(self, tmp_path):
        """A test that passes regardless of implementation should FAIL."""
        from immune_system.verification import mutation_tester

        src = tmp_path / "target.py"
        src.write_text(textwrap.dedent("""\
            def compute(x):
                return x * 2
        """))

        # Tautological: doesn't check the return value
        test = tmp_path / "test_target.py"
        test.write_text(textwrap.dedent(f"""\
            import sys
            sys.path.insert(0, {str(tmp_path)!r})
            from target import compute
            def test_compute():
                result = compute(5)
                assert isinstance(result, int)  # passes for ANY int return
        """))

        result = mutation_tester.check(
            target_file=str(src),
            target_function="compute",
            test_file=str(test),
        )
        assert result.verdict is False, \
            "Tautological test should be detected (mutations survive)"
        assert 2 in result.lines, \
            f"Surviving mutation should be on line 2 (return x * 2), got {result.lines}"

    def test_real_test_passes(self, tmp_path):
        """A test that validates behavior should PASS (no survivors)."""
        from immune_system.verification import mutation_tester

        src = tmp_path / "target.py"
        src.write_text(textwrap.dedent("""\
            def multiply(a, b):
                return a * b
        """))

        test = tmp_path / "test_target.py"
        test.write_text(textwrap.dedent(f"""\
            import sys
            sys.path.insert(0, {str(tmp_path)!r})
            from target import multiply
            def test_multiply_basic():
                assert multiply(3, 4) == 12
            def test_multiply_zero():
                assert multiply(0, 5) == 0
            def test_multiply_negative():
                assert multiply(-2, 3) == -6
        """))

        result = mutation_tester.check(
            target_file=str(src),
            target_function="multiply",
            test_file=str(test),
        )
        assert result.verdict is True, \
            f"Real tests should catch mutations, but got: {result.detail}"
        assert result.lines == [], \
            f"No mutations should survive, but got survivors at: {result.lines}"

    def test_reports_survival_count(self, tmp_path):
        """Result detail must include numeric survived vs total counts."""
        from immune_system.verification import mutation_tester

        src = tmp_path / "target.py"
        src.write_text(textwrap.dedent("""\
            def negate(x):
                return -x
        """))

        test = tmp_path / "test_target.py"
        test.write_text(textwrap.dedent(f"""\
            import sys
            sys.path.insert(0, {str(tmp_path)!r})
            from target import negate
            def test_negate():
                assert negate(5) == -5
        """))

        result = mutation_tester.check(
            target_file=str(src),
            target_function="negate",
            test_file=str(test),
        )
        # Detail must contain numeric counts like "0/3 survived" or "0 of 3"
        assert re.search(r"\d+\s*(?:/|\s+of\s+)\s*\d+", result.detail), \
            f"Detail must include survived/total counts, got: {result.detail}"

    def test_empty_function_passes(self, tmp_path):
        """A function with no mutable operations should pass trivially."""
        from immune_system.verification import mutation_tester

        src = tmp_path / "target.py"
        src.write_text(textwrap.dedent("""\
            def noop():
                pass
        """))

        test = tmp_path / "test_target.py"
        test.write_text(textwrap.dedent(f"""\
            import sys
            sys.path.insert(0, {str(tmp_path)!r})
            from target import noop
            def test_noop():
                assert noop() is None
        """))

        result = mutation_tester.check(
            target_file=str(src),
            target_function="noop",
            test_file=str(test),
        )
        assert result.verdict is True


class TestMutationTesterBudget:
    """Verify mutation budget controls."""

    def test_respects_max_mutations(self, tmp_path):
        """Must not generate more mutations than the budget allows."""
        from immune_system.verification import mutation_tester

        src = tmp_path / "target.py"
        src.write_text(textwrap.dedent("""\
            def big_function(a, b, c, d):
                x = a + b
                y = c - d
                z = x * y
                w = z / max(a, 1)
                return x + y + z + w
        """))

        test = tmp_path / "test_target.py"
        test.write_text(textwrap.dedent(f"""\
            import sys
            sys.path.insert(0, {str(tmp_path)!r})
            from target import big_function
            def test_basic():
                result = big_function(2, 3, 4, 1)
                assert isinstance(result, (int, float))
        """))

        result = mutation_tester.check(
            target_file=str(src),
            target_function="big_function",
            test_file=str(test),
            max_mutations=3,
        )
        assert isinstance(result, ToolEvidence)
        # Parse total mutations attempted from detail
        match = re.search(r"(\d+)\s*(?:/|\s+of\s+)\s*(\d+)", result.detail) or \
                re.search(r"(\d+)\s+mutation", result.detail)
        assert match, f"Could not parse mutation count from: {result.detail}"
        total = int(match.group(2)) if match.lastindex >= 2 else int(match.group(1))
        assert total <= 3, f"Expected <= 3 mutations attempted, got {total}"
