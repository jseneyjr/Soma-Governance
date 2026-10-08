"""Behavioral test suite verifying Call Graph reachability on language-agnostic NormalizedAST."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from soma_core.ast.schema import (
    CallSiteNode,
    DefinitionNode,
    ImportNode,
    NormalizedAST,
)
from soma_core.verification import call_graph


def test_call_graph_all_functions_called_internally():
    norm_ast = NormalizedAST(
        file_path="src/service.ts",
        language="typescript",
        definitions=(
            DefinitionNode(name="publicMethod", kind="function", line=10, is_exported=True),
            DefinitionNode(name="internalHelper", kind="function", line=20, is_exported=False),
        ),
        call_sites=(
            CallSiteNode(target="internalHelper", line=12, caller_scope="publicMethod"),
        ),
        imports=(),
    )

    evidence = call_graph.check_normalized(norm_ast, repo_root=".")
    assert evidence.verdict is True
    assert "All 2 functions have call sites" in evidence.detail or "verified" in evidence.detail.lower()


def test_call_graph_detects_orphan_function():
    norm_ast = NormalizedAST(
        file_path="src/calc.go",
        language="go",
        definitions=(
            DefinitionNode(name="ExportedApi", kind="function", line=5, is_exported=True),
            DefinitionNode(name="uncalledDeadwood", kind="function", line=15, is_exported=False),
            DefinitionNode(name="calledHelper", kind="function", line=25, is_exported=False),
        ),
        call_sites=(
            CallSiteNode(target="calledHelper", line=8, caller_scope="ExportedApi"),
        ),
        imports=(),
    )

    evidence = call_graph.check_normalized(norm_ast, repo_root=".")
    assert evidence.verdict is False
    assert "ORPHAN FUNCTIONS" in evidence.detail
    assert "uncalledDeadwood" in evidence.detail
    assert 15 in evidence.lines


def test_call_graph_exported_functions_not_flagged_as_orphans():
    norm_ast = NormalizedAST(
        file_path="lib/export_only.ts",
        language="typescript",
        definitions=(
            DefinitionNode(name="PublicApiA", kind="function", line=1, is_exported=True),
            DefinitionNode(name="PublicApiB", kind="function", line=10, is_exported=True),
        ),
        call_sites=(),
        imports=(),
    )

    evidence = call_graph.check_normalized(norm_ast, repo_root=".")
    assert evidence.verdict is True


def test_call_graph_external_file_matches_polyglot_orphan(tmp_path):
    # Target file has an uncalled function
    target_ts = tmp_path / "utils.ts"
    target_ts.write_text("// utils", encoding="utf-8")

    norm_ast = NormalizedAST(
        file_path=str(target_ts),
        language="typescript",
        definitions=(
            DefinitionNode(name="sharedHelper", kind="function", line=10, is_exported=False),
        ),
        call_sites=(),
        imports=(),
    )

    # Calling file in repo calls sharedHelper
    consumer_file = tmp_path / "caller.ts"
    consumer_file.write_text("import { sharedHelper } from './utils'; sharedHelper();", encoding="utf-8")

    evidence = call_graph.check_normalized(norm_ast, repo_root=str(tmp_path), fast_mode=False)
    assert evidence.verdict is True


def test_call_graph_comment_and_string_in_external_file_does_not_satisfy_call(tmp_path):
    target_go = tmp_path / "calc.go"
    target_go.write_text("// calc", encoding="utf-8")

    norm_ast = NormalizedAST(
        file_path=str(target_go),
        language="go",
        definitions=(
            DefinitionNode(name="uncalledCalc", kind="function", line=10, is_exported=False),
        ),
        call_sites=(),
        imports=(),
    )

    # Calling file only mentions uncalledCalc in a comment and string literal
    consumer_file = tmp_path / "main.go"
    consumer_file.write_text(
        '// Note: uncalledCalc() should be used\nconst msg = "call uncalledCalc()";\n',
        encoding="utf-8",
    )

    evidence = call_graph.check_normalized(norm_ast, repo_root=str(tmp_path), fast_mode=False)
    assert evidence.verdict is False
    assert "ORPHAN FUNCTIONS" in evidence.detail
    assert "uncalledCalc" in evidence.detail
