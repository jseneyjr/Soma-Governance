"""Tests for rule metadata schema compliance.

Validates that every governance rule (genome + cells) has YAML frontmatter
with the fields required by the evidence enrichment pipeline:
  - 'id': unique identifier matching filename (stem)
  - 'domain': one of {efficiency, correctness, security, style, governance}

Written BEFORE adding the new fields — tests will fail on every rule
that lacks them, proving they detect the gap.
"""

import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
GENOME_DIR = REPO_ROOT / "genome"
ORACLES_DIR = GENOME_DIR / ".oracles"
CELLS_DIR = REPO_ROOT / ".soma" / "cells"

# Fields required for the evidence enrichment pipeline
REQUIRED_FIELDS = {"id", "domain"}
VALID_DOMAINS = {"efficiency", "correctness", "security", "style", "governance"}

# Regex to extract YAML frontmatter block
FRONTMATTER_RE = re.compile(r"^---\n(.+?)\n---\n", re.DOTALL)

# Files to skip (non-rule files)
SKIP_FILES = {"META.md", "README.md"}


def parse_frontmatter(text: str) -> dict | None:
    """Minimal YAML frontmatter parser — no pyyaml dependency.

    Handles simple key: value pairs. Does not support nested structures.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    result = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def get_genome_rules() -> list[Path]:
    """All .md rule files in genome/ (top-level, non-hidden)."""
    if not GENOME_DIR.exists():
        return []
    return sorted(
        p for p in GENOME_DIR.glob("*.md")
        if p.name not in SKIP_FILES
    )


def get_oracle_rules() -> list[Path]:
    """All .md rule files in genome/.oracles/."""
    if not ORACLES_DIR.exists():
        return []
    return sorted(
        p for p in ORACLES_DIR.glob("*.md")
        if p.name not in SKIP_FILES
    )


def get_cell_rules() -> list[Path]:
    """All .md cell files in .soma/cells/**/ (excluding README)."""
    if not CELLS_DIR.exists():
        return []
    return sorted(
        p for p in CELLS_DIR.rglob("*.md")
        if p.name not in SKIP_FILES
    )


def get_all_rules() -> list[Path]:
    """All rule files across genome + cells."""
    return get_genome_rules() + get_oracle_rules() + get_cell_rules()


# ── Genome rules must have frontmatter ──


@pytest.mark.parametrize("rule_file", get_genome_rules(),
                         ids=lambda p: f"genome/{p.name}")
def test_genome_rule_has_frontmatter(rule_file):
    """Every genome rule MUST have YAML frontmatter."""
    meta = parse_frontmatter(rule_file.read_text())
    assert meta is not None, f"{rule_file.name} lacks YAML frontmatter"


@pytest.mark.parametrize("rule_file", get_genome_rules(),
                         ids=lambda p: f"genome/{p.name}")
def test_genome_rule_has_id(rule_file):
    """Every genome rule MUST have an 'id' field in frontmatter."""
    meta = parse_frontmatter(rule_file.read_text())
    assert meta is not None, f"{rule_file.name} lacks YAML frontmatter"
    assert "id" in meta, f"{rule_file.name} missing 'id' field"


@pytest.mark.parametrize("rule_file", get_genome_rules(),
                         ids=lambda p: f"genome/{p.name}")
def test_genome_rule_has_domain(rule_file):
    """Every genome rule MUST have a 'domain' field in frontmatter."""
    meta = parse_frontmatter(rule_file.read_text())
    assert meta is not None, f"{rule_file.name} lacks YAML frontmatter"
    assert "domain" in meta, f"{rule_file.name} missing 'domain' field"


# ── Oracle rules must have frontmatter ──


@pytest.mark.parametrize("rule_file", get_oracle_rules(),
                         ids=lambda p: f"oracles/{p.name}")
def test_oracle_rule_has_frontmatter(rule_file):
    """Every oracle rule MUST have YAML frontmatter."""
    meta = parse_frontmatter(rule_file.read_text())
    assert meta is not None, f"{rule_file.name} lacks YAML frontmatter"


@pytest.mark.parametrize("rule_file", get_oracle_rules(),
                         ids=lambda p: f"oracles/{p.name}")
def test_oracle_rule_has_id(rule_file):
    """Every oracle rule MUST have an 'id' field in frontmatter."""
    meta = parse_frontmatter(rule_file.read_text())
    assert meta is not None, f"{rule_file.name} lacks YAML frontmatter"
    assert "id" in meta, f"{rule_file.name} missing 'id' field"


@pytest.mark.parametrize("rule_file", get_oracle_rules(),
                         ids=lambda p: f"oracles/{p.name}")
def test_oracle_rule_has_domain(rule_file):
    """Every oracle rule MUST have a 'domain' field in frontmatter."""
    meta = parse_frontmatter(rule_file.read_text())
    assert meta is not None, f"{rule_file.name} lacks YAML frontmatter"
    assert "domain" in meta, f"{rule_file.name} missing 'domain' field"


# ── Cell rules must have frontmatter and domain ──


@pytest.mark.parametrize("rule_file", get_cell_rules(),
                         ids=lambda p: f"cells/{p.parent.name}/{p.name}")
def test_cell_rule_has_frontmatter(rule_file):
    """Every cell rule MUST have YAML frontmatter."""
    meta = parse_frontmatter(rule_file.read_text())
    assert meta is not None, f"{rule_file.name} lacks YAML frontmatter"


@pytest.mark.parametrize("rule_file", get_cell_rules(),
                         ids=lambda p: f"cells/{p.parent.name}/{p.name}")
def test_cell_rule_has_domain(rule_file):
    """Every cell rule MUST have a 'domain' field in frontmatter."""
    meta = parse_frontmatter(rule_file.read_text())
    assert meta is not None, f"{rule_file.name} lacks YAML frontmatter"
    assert "domain" in meta, f"{rule_file.name} missing 'domain' field"


# ── Cross-cutting validation ──


@pytest.mark.parametrize("rule_file", get_all_rules(),
                         ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_domain_is_valid(rule_file):
    """Domain must be one of the known values."""
    meta = parse_frontmatter(rule_file.read_text())
    assert meta is not None, f"{rule_file.name} lacks YAML frontmatter"
    assert "domain" in meta, f"{rule_file.name} missing domain"
    assert meta["domain"] in VALID_DOMAINS, (
        f"{rule_file.name}: domain '{meta['domain']}' not in {VALID_DOMAINS}"
    )


@pytest.mark.parametrize("rule_file", get_all_rules(),
                         ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_id_matches_filename(rule_file):
    """Rule ID should match the filename (without extension)."""
    meta = parse_frontmatter(rule_file.read_text())
    assert meta is not None, f"{rule_file.name} lacks YAML frontmatter"
    assert "id" in meta, f"{rule_file.name} missing id"
    expected = rule_file.stem
    assert meta["id"] == expected, (
        f"ID mismatch: frontmatter says '{meta['id']}', file is '{expected}'"
    )


@pytest.mark.parametrize("rule_file", get_cell_rules(),
                         ids=lambda p: f"cells/{p.parent.name}/{p.name}")
def test_cell_rule_has_id(rule_file):
    """Every cell rule MUST have an 'id' field in frontmatter."""
    meta = parse_frontmatter(rule_file.read_text())
    assert meta is not None, f"{rule_file.name} lacks YAML frontmatter"
    assert "id" in meta, f"{rule_file.name} missing 'id' field"


def test_no_duplicate_rule_ids():
    """All rule IDs across genome + oracles + cells must be unique."""
    ids_seen: dict[str, str] = {}
    for rule_file in get_all_rules():
        meta = parse_frontmatter(rule_file.read_text())
        if meta and "id" in meta:
            rid = meta["id"]
            assert rid not in ids_seen, (
                f"Duplicate id '{rid}': {ids_seen[rid]} and {rule_file.name}"
            )
            ids_seen[rid] = rule_file.name

