"""Tests for governance rule CONTENT correctness.

Validates that factual claims made in governance rules match the actual
state of the codebase. This prevents rule drift — where a rule's prose
contradicts reality, causing agents to follow incorrect guidance.

Grounded in evidence: the optional-import-guard oracle listed pyyaml as
"optional" despite pyproject.toml declaring it as a required dependency.
This single incorrect table row caused 28 files of buggy guard code.
"""

import os
import re
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # Python 3.10 fallback

REPO_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PYPROJECT = REPO_ROOT / "pyproject.toml"


def _parse_pyproject_deps():
    """Extract required dependency package names from pyproject.toml."""
    with open(PYPROJECT, "rb") as f:
        data = tomllib.load(f)
    deps = data.get("project", {}).get("dependencies", [])
    # Parse "pyyaml>=6.0" → "pyyaml"
    return {re.split(r"[><=!~\[]", d)[0].strip().lower() for d in deps}


def _parse_oracle_table(section_header, filepath):
    """Extract package names from a markdown table under a section header."""
    content = filepath.read_text(encoding="utf-8")
    packages = []
    in_section = False
    in_table = False
    for line in content.splitlines():
        if line.startswith("## ") and section_header.lower() in line.lower():
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break  # Next section
        if in_section and line.startswith("|") and "---" not in line:
            cols = [c.strip() for c in line.split("|")]
            if len(cols) >= 3 and cols[1].lower() != "package":
                # Extract package name: "`yaml` (pyyaml)" → "pyyaml"
                raw = cols[1]
                # Check for parenthetical real name: "yaml (pyyaml)" → pyyaml
                paren_match = re.search(r"\((\w+)\)", raw)
                if paren_match:
                    packages.append(paren_match.group(1).lower())
                else:
                    # Strip backticks and use raw name
                    packages.append(raw.strip("`").split(".")[0].lower())
    return set(packages)


# ── Required deps must be in pyproject.toml ──


def test_required_deps_in_pyproject():
    """Every package listed as 'Required' in optional-import-guard must be
    a declared dependency in pyproject.toml."""
    oracle = REPO_ROOT / "genome" / ".oracles" / "optional-import-guard.md"
    if not oracle.exists():
        pytest.skip("optional-import-guard oracle not found")
    required = _parse_oracle_table("Required Dependencies", oracle)
    pyproject_deps = _parse_pyproject_deps()
    for pkg in required:
        assert pkg in pyproject_deps, (
            f"Oracle lists '{pkg}' as required, but it's not in "
            f"pyproject.toml [project.dependencies]: {pyproject_deps}"
        )


def test_optional_deps_not_in_required():
    """Every package listed as 'Optional' in optional-import-guard must NOT
    be a declared required dependency in pyproject.toml."""
    oracle = REPO_ROOT / "genome" / ".oracles" / "optional-import-guard.md"
    if not oracle.exists():
        pytest.skip("optional-import-guard oracle not found")
    optional = _parse_oracle_table("Known Optional Dependencies", oracle)
    pyproject_deps = _parse_pyproject_deps()
    for pkg in optional:
        assert pkg not in pyproject_deps, (
            f"Oracle lists '{pkg}' as optional, but it IS in "
            f"pyproject.toml [project.dependencies]. Move it to the "
            f"'Required Dependencies' table."
        )


# ── Rule-referenced paths should exist ──


def _collect_target_paths_from_rules():
    """Collect target_paths values from all cell frontmatter."""
    import yaml
    results = []
    cells_dir = REPO_ROOT / ".soma" / "cells"
    if not cells_dir.exists():
        return results
    for md_file in cells_dir.rglob("*.md"):
        if md_file.name == "README.md":
            continue
        content = md_file.read_text(encoding="utf-8")
        if not content.startswith("---"):
            continue
        end = content.find("---", 3)
        if end == -1:
            continue
        try:
            fm = yaml.safe_load(content[3:end])
        except Exception:
            continue
        if fm and isinstance(fm, dict):
            tp = fm.get("target_paths", [])
            if isinstance(tp, list):
                for p in tp:
                    if isinstance(p, str) and not any(c in p for c in "*?["):
                        # Only check literal paths, not globs
                        results.append((md_file.name, p))
    return results


_literal_paths = _collect_target_paths_from_rules()


@pytest.mark.parametrize(
    "rule_name,target_path", _literal_paths,
    ids=[f"{r}:{p}" for r, p in _literal_paths]
) if _literal_paths else lambda f: f
def test_literal_target_paths_exist(rule_name, target_path):
    """Literal (non-glob) target_paths referenced by cells should exist."""
    full = REPO_ROOT / target_path
    assert full.exists(), (
        f"Cell '{rule_name}' references target_path '{target_path}' "
        f"which does not exist in the repo"
    )


# ── Rule IDs unique across all layers ──


def test_no_duplicate_ids_across_layers():
    """All rule IDs across genome + oracles + cells must be globally unique."""
    import yaml
    ids_seen: dict[str, str] = {}
    rule_dirs = [
        (REPO_ROOT / "genome", "*.md"),          # non-recursive (oracles separate)
        (REPO_ROOT / "genome" / ".oracles", "*.md"),
        (REPO_ROOT / ".soma" / "cells", "**/*.md"),  # recursive
    ]
    for rule_dir, pattern in rule_dirs:
        if not rule_dir.exists():
            continue
        for md_file in rule_dir.glob(pattern):
            if md_file.name == "README.md":
                continue
            content = md_file.read_text(encoding="utf-8")
            if not content.startswith("---"):
                continue
            end = content.find("---", 3)
            if end == -1:
                continue
            try:
                fm = yaml.safe_load(content[3:end])
            except Exception:
                continue
            if fm and isinstance(fm, dict) and "id" in fm:
                rid = fm["id"]
                rel = str(md_file.relative_to(REPO_ROOT))
                assert rid not in ids_seen, (
                    f"Duplicate id '{rid}': {ids_seen[rid]} and {rel}"
                )
                ids_seen[rid] = rel
