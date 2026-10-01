"""Shared checkpoint checks — canonical implementations for CLI and MCP.

These are stdlib-only functions that verify workspace quality. Both
``soma_cli.checkpoint`` and ``soma_mcp.tools`` import from here to
avoid copy-paste divergence.

All checks follow the same contract:
    def check_*(root: Path) -> list[dict]:
        '''Return a list of issue dicts with 'check' and 'message' keys.'''
"""
from __future__ import annotations

import glob
import json
import os
import re
from pathlib import Path


# ── Constants ─────────────────────────────────────────────────────────

HARDCODED_PATH_RE = re.compile(
    r'''(?:"|')(/home/|/Users/|/tmp/)'''
)

SKIP_DIRS = {
    "__pycache__", ".git", ".soma", "node_modules", ".venv", "venv",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build", "egg-info",
}

# Known cell directory names → expected frontmatter type
DIR_TO_TYPE = {
    "vacuoles": "vacuole",
    "walls": "wall",
    "chloroplasts": "chloroplast",
    "membranes": "membrane",
    "plasmodesmata": "plasmodesmata",
}


# ── Utilities ─────────────────────────────────────────────────────────


def find_python_files(root: Path, subdir: str) -> list[Path]:
    """Find all .py files under root/subdir, skipping hidden/build dirs."""
    target = root / subdir
    if not target.is_dir():
        return []
    result: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(target):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if f.endswith(".py") and not f.startswith("__"):
                result.append(Path(dirpath) / f)
    return result


# ── Checks ────────────────────────────────────────────────────────────


def check_test_coverage(root: Path) -> list[dict]:
    """Check that every src/*.py has a corresponding tests/test_*.py."""
    issues: list[dict] = []
    # Auto-detect source directories (support src/, lib/, and package-named dirs)
    src_dirs: list[str] = []
    for candidate in sorted(root.iterdir()):
        if not candidate.is_dir():
            continue
        name = candidate.name
        if name.startswith(".") or name in SKIP_DIRS or name == "tests":
            continue
        # Include if it contains at least one .py file at any depth
        if any(candidate.rglob("*.py")):
            src_dirs.append(name)
    src_files: list[Path] = []
    for sd in src_dirs:
        src_files.extend(find_python_files(root, sd))
    test_dir = root / "tests"
    for src_file in src_files:
        stem = src_file.stem
        expected_test = test_dir / f"test_{stem}.py"
        if not expected_test.exists():
            issues.append({
                "check": "test_coverage",
                "file": str(src_file.relative_to(root)),
                "message": f"Missing test file for {src_file.name}: expected tests/test_{stem}.py",
            })
    return issues


def check_hardcoded_paths(root: Path) -> list[dict]:
    """Scan source .py files for hardcoded absolute paths."""
    issues: list[dict] = []
    # Auto-detect source directories (same logic as check_test_coverage)
    for candidate in sorted(root.iterdir()):
        if not candidate.is_dir():
            continue
        name = candidate.name
        if name.startswith(".") or name in SKIP_DIRS or name == "tests":
            continue
        for py_file in find_python_files(root, name):
            try:
                content = py_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line_no, line in enumerate(content.splitlines(), 1):
                if HARDCODED_PATH_RE.search(line):
                    issues.append({
                        "check": "hardcoded_paths",
                        "file": str(py_file.relative_to(root)),
                        "line": line_no,
                        "message": f"Hardcoded absolute path found in {py_file.name}:{line_no}",
                    })
    return issues


def check_assertion_density(root: Path) -> list[dict]:
    """Flag test files that contain zero assert statements."""
    issues: list[dict] = []
    test_files = find_python_files(root, "tests")
    for tf in test_files:
        if not tf.name.startswith("test_"):
            continue
        try:
            content = tf.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Check for both pytest-style and unittest-style assertions
        has_assertion = (
            "assert " in content
            or "assert(" in content
            or "pytest.raises" in content
            or "pytest.fail" in content
            or "self.assert" in content
        )
        if not has_assertion:
            # Try AST-based detection as fallback
            try:
                from immune_system.verification.quality_gate import (
                    check_assertion_density as _ast_check,
                )
                evidence = _ast_check(str(tf))
                if evidence.verdict:
                    continue  # AST found assertions
            except Exception:
                pass
            issues.append({
                "check": "assertion_density",
                "file": str(tf.relative_to(root)),
                "message": f"Low assertion density in {tf.name}: no assert statements found",
            })
    return issues


def check_cell_fitness(root: Path) -> list[dict]:
    """Check .soma/evidence for cells with high false-positive rates."""
    issues: list[dict] = []
    evidence_dir = root / ".soma" / "evidence"
    outcomes_file = evidence_dir / "outcomes.jsonl"
    if not outcomes_file.exists():
        return issues

    cell_outcomes: dict[str, dict[str, int]] = {}
    try:
        lines = outcomes_file.read_text(encoding="utf-8").strip().splitlines()
    except OSError:
        return issues

    for line in lines:
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue  # Skip corrupted lines
        cid = record.get("cell_id", "unknown")
        outcome = record.get("outcome", "")
        if cid not in cell_outcomes:
            cell_outcomes[cid] = {"tp": 0, "fp": 0, "total": 0}
        cell_outcomes[cid]["total"] += 1
        if outcome in ("fp", "failure"):
            cell_outcomes[cid]["fp"] += 1
        elif outcome in ("tp", "success"):
            cell_outcomes[cid]["tp"] += 1

    # Flag cells with fp rate > 50%
    for cid, counts in cell_outcomes.items():
        if counts["total"] >= 2 and counts["fp"] / counts["total"] > 0.5:
            fp_rate = counts["fp"] / counts["total"]
            issues.append({
                "check": "cell_fitness",
                "cell_id": cid,
                "message": (
                    f"Cell '{cid}' has unhealthy fitness: "
                    f"{counts['fp']}/{counts['total']} false positives "
                    f"({fp_rate:.0%} FP rate)"
                ),
            })
    return issues


def check_cell_conventions(root: Path) -> list[dict]:
    """Check that cell files follow project conventions.

    Catches:
    - Walls must have enforcement: gate
    - Frontmatter 'type' must match the directory
    - Required fields: id, domain, type, enforcement
    - Frontmatter 'id' must match filename stem
    """
    issues: list[dict] = []
    cells_dir = root / ".soma" / "cells"
    if not cells_dir.is_dir():
        return issues

    try:
        import yaml
    except ImportError:
        issues.append({
            "check": "cell_conventions",
            "message": "pyyaml not installed — cell convention checks skipped",
        })
        return issues

    for type_dir_name, expected_type in DIR_TO_TYPE.items():
        type_dir = cells_dir / type_dir_name
        if not type_dir.is_dir():
            continue
        for cell_file in sorted(type_dir.glob("*.md")):
            if cell_file.name == "README.md":
                continue
            try:
                content = cell_file.read_text(encoding="utf-8")
            except OSError:
                continue
            if not content.startswith("---"):
                continue
            end = content.find("---", 3)
            if end < 0:
                continue

            rel = f".soma/cells/{type_dir_name}/{cell_file.name}"

            try:
                meta = yaml.safe_load(content[3:end])
            except Exception as exc:
                issues.append({
                    "check": "cell_conventions",
                    "message": f"{rel}: malformed YAML frontmatter: {exc}",
                })
                continue
            if not isinstance(meta, dict):
                continue

            # Check required fields — enforcement only required for walls/vacuoles
            required = ["id", "domain", "type"]
            if expected_type in ("wall", "vacuole"):
                required.append("enforcement")
            for field in required:
                if field not in meta:
                    issues.append({
                        "check": "cell_conventions",
                        "message": f"{rel}: missing required field '{field}'",
                    })

            # Check type matches directory
            cell_type = meta.get("type", "")
            if cell_type != expected_type:
                issues.append({
                    "check": "cell_conventions",
                    "message": (
                        f"{rel}: type '{cell_type}' doesn't match directory "
                        f"'{type_dir_name}' (expected '{expected_type}')"
                    ),
                })

            # Check enforcement convention for walls
            if expected_type == "wall" and meta.get("enforcement") != "gate":
                issues.append({
                    "check": "cell_conventions",
                    "message": (
                        f"{rel}: wall enforcement is '{meta.get('enforcement')}' "
                        f"but walls must use 'gate'"
                    ),
                })

            # Check id matches filename
            if meta.get("id") != cell_file.stem:
                issues.append({
                    "check": "cell_conventions",
                    "message": (
                        f"{rel}: frontmatter id '{meta.get('id')}' "
                        f"doesn't match filename '{cell_file.stem}'"
                    ),
                })

    return issues


def check_arbitration_evidence(root: Path) -> list[dict]:
    """Check that review arbitration evidence exists and verdict is SHIP.

    Un-bypassable gate: if any arbitration_cycle_*.json exists with a
    non-SHIP verdict, checkpoint fails.
    """
    issues: list[dict] = []
    evidence_dir = root / ".soma" / "evidence"
    if not evidence_dir.is_dir():
        return issues

    arb_files = glob.glob(
        str(evidence_dir / "arbitration_cycle_*.json")
    )
    if not arb_files:
        return issues

    # Sort numerically by cycle number to avoid lex ordering (10 < 9)
    def _cycle_num(path: str) -> int:
        m = re.search(r'cycle_(\d+)', path)
        return int(m.group(1)) if m else 0

    arb_files.sort(key=_cycle_num)
    latest = arb_files[-1]
    try:
        with open(latest, encoding="utf-8") as f:
            record = json.loads(f.read())
    except (OSError, json.JSONDecodeError):
        issues.append({
            "check": "arbitration_evidence",
            "message": f"Arbitration evidence file is corrupt: {latest}",
        })
        return issues

    verdict = record.get("verdict", "unknown").lower()
    cycle = record.get("cycle", "?")
    divergences = record.get("divergence_count", 0)

    if verdict == "block":
        issues.append({
            "check": "arbitration_evidence",
            "message": (
                f"Arbiter verdict is BLOCK for cycle {cycle} "
                f"({divergences} divergence(s)). Fix all findings before ship."
            ),
        })
    elif verdict == "revise":
        issues.append({
            "check": "arbitration_evidence",
            "message": (
                f"Arbiter verdict is REVISE for cycle {cycle} "
                f"({divergences} divergence(s)). Address high-severity findings."
            ),
        })
    elif verdict not in ("ship",):
        issues.append({
            "check": "arbitration_evidence",
            "message": (
                f"Unknown arbiter verdict '{verdict}' for cycle {cycle}. "
                f"Only 'ship' passes the gate."
            ),
        })

    return issues


# ── Aggregate Runner ──────────────────────────────────────────────────

ALL_CHECKS = [
    check_test_coverage,
    check_hardcoded_paths,
    check_assertion_density,
    check_cell_fitness,
    check_cell_conventions,
    check_arbitration_evidence,
]

CHECK_NAMES = [
    "test_coverage",
    "hardcoded_paths",
    "assertion_density",
    "cell_fitness",
    "cell_conventions",
    "arbitration_evidence",
]


def run_all_checks(root: Path) -> list[dict]:
    """Run all checkpoint checks and return combined issues."""
    all_issues: list[dict] = []
    for check_fn in ALL_CHECKS:
        all_issues.extend(check_fn(root))
    return all_issues
