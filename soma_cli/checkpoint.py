"""soma checkpoint — deterministic quality checks (no LLM required).

Checks:
- Test file coverage for implementation files
- Hardcoded absolute paths (/home, /Users, /tmp)
- Assertion density in test files
- Cell fitness scores from .soma/evidence ledger

Supports --pre-commit (warn mode), --strict, --json, --workspace flags.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


# Patterns considered hardcoded absolute paths
_HARDCODED_PATH_RE = re.compile(
    r'''(?:"|')(/home/|/Users/|/tmp/)'''
)

# Directories to skip when scanning for implementation files
_SKIP_DIRS = {
    "__pycache__", ".git", ".soma", "node_modules", ".venv", "venv",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build", "egg-info",
}


# ── Individual Checks ─────────────────────────────────────────────────


def _find_python_files(root: Path, subdir: str) -> list[Path]:
    """Find all .py files under root/subdir, skipping hidden/build dirs."""
    target = root / subdir
    if not target.is_dir():
        return []
    result = []
    for dirpath, dirnames, filenames in os.walk(target):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for f in filenames:
            if f.endswith(".py") and not f.startswith("__"):
                result.append(Path(dirpath) / f)
    return result


def _check_test_coverage(root: Path) -> list[dict]:
    """Check that every src/*.py has a corresponding tests/test_*.py."""
    issues = []
    src_files = _find_python_files(root, "src")
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


def _check_hardcoded_paths(root: Path) -> list[dict]:
    """Scan all .py files for hardcoded absolute paths."""
    issues = []
    for subdir in ("src", "tests"):
        for py_file in _find_python_files(root, subdir):
            try:
                content = py_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line_no, line in enumerate(content.splitlines(), 1):
                if _HARDCODED_PATH_RE.search(line):
                    issues.append({
                        "check": "hardcoded_paths",
                        "file": str(py_file.relative_to(root)),
                        "line": line_no,
                        "message": f"Hardcoded absolute path found in {py_file.name}:{line_no}",
                    })
    return issues


def _check_assertion_density(root: Path) -> list[dict]:
    """Flag test files that contain zero assert statements."""
    issues = []
    test_files = _find_python_files(root, "tests")

    for tf in test_files:
        # Only check actual test files, not conftest.py or helper modules
        if not tf.name.startswith("test_"):
            continue

        # Prefer AST-based checker from quality_gate (handles self.assert*,
        # pytest.raises, and ignores comments/strings)
        try:
            from immune_system.verification.quality_gate import check_assertion_density
            evidence = check_assertion_density(str(tf))
            if not evidence.verdict:
                issues.append({
                    "check": "assertion_density",
                    "file": str(tf.relative_to(root)),
                    "message": f"Low assertion density in {tf.name}: {evidence.detail}",
                })
            continue
        except Exception:
            pass

        # Fallback: line-based substring matching (skip comment lines)
        try:
            content = tf.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        has_assertion = False
        for line in content.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if (
                "assert " in stripped
                or "assert(" in stripped
                or "pytest.raises" in stripped
                or ".assertEqual" in stripped
                or ".assertTrue" in stripped
                or ".assertFalse" in stripped
                or ".assertRaises" in stripped
                or ".assertIn" in stripped
            ):
                has_assertion = True
                break
        if not has_assertion:
            issues.append({
                "check": "assertion_density",
                "file": str(tf.relative_to(root)),
                "message": f"Low assertion density in {tf.name}: no assert statements found",
            })
    return issues


def _check_cell_fitness(root: Path) -> list[dict]:
    """Check .soma/evidence for cells with high false-positive rates."""
    issues = []
    evidence_dir = root / ".soma" / "evidence"
    outcomes_file = evidence_dir / "outcomes.jsonl"

    if not outcomes_file.exists():
        return issues

    # Tally outcomes per cell_id
    cell_outcomes: dict[str, dict[str, int]] = {}
    try:
        for line in outcomes_file.read_text(encoding="utf-8").strip().splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            cid = record.get("cell_id", "unknown")
            outcome = record.get("outcome", "")
            if cid not in cell_outcomes:
                cell_outcomes[cid] = {"tp": 0, "fp": 0, "total": 0}
            cell_outcomes[cid]["total"] += 1
            if outcome == "fp":
                cell_outcomes[cid]["fp"] += 1
            elif outcome == "tp":
                cell_outcomes[cid]["tp"] += 1
    except (OSError, json.JSONDecodeError):
        return issues

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


def _check_cell_conventions(root: Path) -> list[dict]:
    """Check that cell files follow project conventions.

    Catches dogfooding failures:
    - Walls must have enforcement: gate
    - Frontmatter 'type' must match the directory (vacuoles/ → vacuole)
    - Required fields: id, domain, type, enforcement
    - Frontmatter 'id' must match filename stem
    """
    issues = []
    cells_dir = root / ".soma" / "cells"
    if not cells_dir.is_dir():
        return issues

    try:
        import yaml
    except ImportError:
        return issues

    dir_to_type = {"vacuoles": "vacuole", "walls": "wall"}

    for type_dir_name, expected_type in dir_to_type.items():
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
            try:
                meta = yaml.safe_load(content[3:end])
            except Exception:
                continue
            if not isinstance(meta, dict):
                continue

            rel = f".soma/cells/{type_dir_name}/{cell_file.name}"

            # Check required fields
            for field in ("id", "domain", "type", "enforcement"):
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


def _check_arbitration_evidence(root: Path) -> list[dict]:
    """Check that review arbitration evidence exists and verdict is SHIP.

    Un-bypassable gate: if any arbitration_cycle_*.json exists with a
    non-SHIP verdict, checkpoint fails. If no arbitration evidence exists
    at all, this check passes silently (review may not have been triggered).
    """
    issues = []
    evidence_dir = root / ".soma" / "evidence"
    if not evidence_dir.is_dir():
        return issues

    import glob
    arb_files = sorted(glob.glob(
        str(evidence_dir / "arbitration_cycle_*.json")
    ))
    if not arb_files:
        return issues  # No review cycles recorded — not a gate failure

    # Check the latest cycle
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

    verdict = record.get("verdict", "unknown")
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

    return issues


# ── Main Entry Point ──────────────────────────────────────────────────


def run_checkpoint(args: argparse.Namespace) -> int:
    """Run deterministic quality checkpoint on a workspace.

    Args:
        args: Parsed CLI arguments with workspace, pre_commit, strict, json.

    Returns:
        Exit code: 0 for pass, 1 for failures.
    """
    workspace = getattr(args, "workspace", None) or os.getcwd()
    root = Path(workspace)

    pre_commit = getattr(args, "pre_commit", False)
    strict = getattr(args, "strict", False)
    use_json = getattr(args, "json", False)

    # Validate workspace exists
    if not root.is_dir():
        msg = f"Error: workspace does not exist: {workspace}"
        if use_json:
            print(json.dumps({
                "status": "error",
                "passed": False,
                "checks": [],
                "issues": [{"check": "workspace", "message": msg}],
            }))
        else:
            print(msg, file=sys.stderr)
        return 1

    # Run all checks
    all_issues: list[dict] = []
    all_issues.extend(_check_test_coverage(root))
    all_issues.extend(_check_hardcoded_paths(root))
    all_issues.extend(_check_assertion_density(root))
    all_issues.extend(_check_cell_fitness(root))
    all_issues.extend(_check_cell_conventions(root))
    all_issues.extend(_check_arbitration_evidence(root))

    has_issues = len(all_issues) > 0

    # Determine exit code
    if has_issues:
        if pre_commit and not strict:
            # Warn mode: report issues but exit 0
            exit_code = 0
        else:
            exit_code = 1
    else:
        exit_code = 0

    # Output
    if use_json:
        checks_run = ["test_coverage", "hardcoded_paths", "assertion_density", "cell_fitness", "cell_conventions"]
        output = {
            "status": "failed" if has_issues else "passed",
            "passed": not has_issues,
            "checks": checks_run,
            "issues": all_issues,
        }
        print(json.dumps(output, indent=2))
    else:
        if has_issues:
            warn_label = "[WARN]" if (pre_commit and not strict) else "[FAIL]"
            for issue in all_issues:
                print(f"{warn_label} {issue['message']}")
        else:
            print("checkpoint: all checks passed")

    return exit_code
