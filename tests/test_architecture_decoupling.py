"""Behavioral tests for BUG-079: Architectural Layer Decoupling (Layer 0 Core -> Layer 2 Inversion).

Layer 0 Core (soma_core/) is the foundational, zero-dependency engine.
It must NEVER import from Layer 2 (soma_mcp/ or soma_cli/) or Layer 1 (soma_sdk/).
Specifically, checkpoint_checks.py must not import parse_frontmatter from soma_mcp.
"""
import ast
import os
from pathlib import Path
import pytest


def test_soma_core_has_zero_upward_imports():
    """All files in soma_core/ must have zero imports of soma_mcp, soma_cli, or soma_sdk."""
    repo_root = Path(__file__).resolve().parent.parent
    core_dir = repo_root / "soma_core"

    violations = []
    forbidden_modules = ("soma_mcp", "soma_cli", "soma_sdk")

    for py_file in core_dir.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except Exception as exc:
            violations.append(f"Failed to parse {py_file}: {exc}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(alias.name == f or alias.name.startswith(f + ".") for f in forbidden_modules):
                        violations.append(f"{py_file.relative_to(repo_root)}:{node.lineno} imports '{alias.name}'")
            elif isinstance(node, ast.ImportFrom):
                if node.module and any(node.module == f or node.module.startswith(f + ".") for f in forbidden_modules):
                    violations.append(f"{py_file.relative_to(repo_root)}:{node.lineno} imports from '{node.module}'")

    assert not violations, "Architectural Layer Inversion violations found in soma_core:\n" + "\n".join(violations)


def test_parse_frontmatter_in_soma_core():
    """parse_frontmatter must be available directly in soma_core."""
    from soma_core.cell_inventory import parse_frontmatter
    content = "---\ntype: learned-trap\nname: test-trap\n---\nBody here"
    fm = parse_frontmatter(content)
    assert isinstance(fm, dict)
    assert fm.get("type") == "learned-trap"
