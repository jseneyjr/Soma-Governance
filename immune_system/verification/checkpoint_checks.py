"""Shared, deterministic, read-only checkpoint checks for CLI and MCP."""
from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from soma_core.evidence import aggregate_signals


HARDCODED_PATH_RE = re.compile(r'''(?:"|')(/home/|/Users/|/tmp/)''')
SKIP_DIRS = {
    "__pycache__", ".git", ".soma", "node_modules", ".venv", "venv",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build", "egg-info",
}
DIR_TO_TYPE = {
    "vacuoles": "vacuole",
    "walls": "wall",
    "chloroplasts": "chloroplast",
    "membranes": "membrane",
    "plasmodesmata": "plasmodesmata",
}

SOURCE_TO_TEST_MAP = {
    "enzymes/bayesian_score.py": "tests/test_bayesian_correctness.py",
    "enzymes/bump_version.py": "tests/test_phase4_enzymes.py",
    "enzymes/cell_adapt.py": "tests/test_governance.py",
    "enzymes/cell_adversarial.py": "tests/test_enzyme_console_encoding.py",
    "enzymes/cell_coverage.py": "tests/test_enzyme_console_encoding.py",
    "enzymes/cell_create_nl.py": "tests/test_cell_create_insight.py",
    "enzymes/cell_crossover.py": "tests/test_crossover_structured.py",
    "enzymes/cell_demote.py": "tests/test_cli_demote.py",
    "enzymes/cell_deps.py": "tests/test_cell_deps_behavioral.py",
    "enzymes/cell_enforce.py": "tests/test_enforce_hooks.py",
    "enzymes/cell_escaped_defects.py": "tests/test_escaped_defects_behavioral.py",
    "enzymes/cell_fitness.py": "tests/test_bayesian_fitness.py",
    "enzymes/cell_genesis_stochastic.py": "tests/test_genesis.py",
    "enzymes/cell_metamorphose.py": "tests/test_lifecycle.py",
    "enzymes/cell_promote.py": "tests/test_local_promotion_decay.py",
    "enzymes/cell_quorum.py": "tests/test_quorum.py",
    "enzymes/cell_scan.py": "tests/test_cell_signal.py",
    "enzymes/cell_selection.py": "tests/test_phase4_enzymes.py",
    "enzymes/cell_tournament.py": "tests/test_tournament_integration.py",
    "enzymes/escalation_sentinel.py": "tests/test_documentation_accuracy.py",
    "enzymes/export_logs.py": "tests/test_phase4_enzymes.py",
    "enzymes/fitness_landscape.py": "tests/test_governance.py",
    "enzymes/hgt_ribosome.py": "tests/test_governance.py",
    "enzymes/immune_entropy.py": "tests/test_enzyme_console_encoding.py",
    "enzymes/immune_grade.py": "tests/test_enzyme_console_encoding.py",
    "enzymes/immune_replay.py": "tests/test_enzyme_console_encoding.py",
    "enzymes/immune_trends.py": "tests/test_governance.py",
    "enzymes/inference_provider.py": "tests/test_keyring_integration.py",
    "enzymes/liveness_sentinel.py": "tests/test_phase4_enzymes.py",
    "enzymes/log_finding.py": "tests/test_phase4_enzymes.py",
    "enzymes/metrics_snapshot.py": "tests/test_python_resolution.py",
    "enzymes/post_session_hook.py": "tests/test_phase4_enzymes.py",
    "enzymes/resilience_engine.py": "tests/test_enzyme_console_encoding.py",
    "enzymes/soma_coherence.py": "tests/test_enzyme_console_encoding.py",
    "enzymes/soma_interoception.py": "tests/test_enzyme_console_encoding.py",
    "enzymes/soma_resolve.py": "tests/test_python_resolution.py",
    "enzymes/soma_sleep.py": "tests/test_enzyme_console_encoding.py",
    "enzymes/sweep_session.py": "tests/test_governance.py",
    "enzymes/team_sync.py": "tests/test_phase4_enzymes.py",
    "enzymes/token_census.py": "tests/test_python_resolution.py",
    "enzymes/ttc_oracle.py": "tests/test_security.py",
    "enzymes/ttc_verifier.py": "tests/test_mcp_tools_contract.py",
    "enzymes/verify_bug_registry.py": "tests/test_bug_registry.py",
    "enzymes/verify_readme_claims.py": "tests/test_documentation_accuracy.py",
    "immune_system/verification/call_graph.py": "tests/test_verification/test_layer1.py",
    "immune_system/verification/checkpoint_checks.py": "tests/test_checkpoint_fail_closed.py",
    "immune_system/verification/persistence_checker.py": "tests/test_verification/test_layer1.py",
    "immune_system/verification/runner.py": "tests/test_verification/test_layer1.py",
    "soma_cli/checkpoint.py": "tests/test_checkpoint_fail_closed.py",
    "soma_cli/demote.py": "tests/test_cli_demote.py",
    "soma_cli/genesis_generator.py": "tests/test_genesis.py",
    "soma_cli/genesis_scanner.py": "tests/test_genesis.py",
    "soma_cli/hooks.py": "tests/test_hooks_lifecycle.py",
    "soma_cli/oracle.py": "tests/test_static_invariants.py",
    "soma_cli/promote.py": "tests/test_cli_promote.py",
    "soma_cli/sync.py": "tests/test_cli_sync.py",
    "soma_cli/verify.py": "tests/test_cli_verify.py",
    "soma_core/errors.py": "tests/test_domain_errors.py",
    "soma_core/evidence.py": "tests/test_canonical_evidence_readers.py",
    "soma_core/frontmatter.py": "tests/test_core_lifecycle.py",
    "soma_core/inference_provider.py": "tests/test_keyring_integration.py",
    "soma_core/lifecycle.py": "tests/test_core_lifecycle.py",
    "soma_core/locking.py": "tests/test_locking.py",
    "soma_core/quarantine.py": "tests/test_quarantine_resilience.py",
    "soma_core/sweep_session.py": "tests/test_governance.py",
    "soma_core/verification_jobs.py": "tests/test_mcp_async_verify.py",
    "soma_mcp/integrity.py": "tests/test_evidence_integrity.py",
    "soma_mcp/jit_engine.py": "tests/test_jit_engine_behavioral.py",
    "soma_mcp/server.py": "tests/test_mcp_dispatch.py",
    "soma_mcp/tools.py": "tests/test_mcp_tools_contract.py",
    "soma_sdk/analysis.py": "tests/test_cell_deps_behavioral.py",
    "soma_sdk/cells.py": "tests/test_rule_content.py",
    "soma_sdk/errors.py": "tests/test_sdk_behavioral.py",
    "soma_sdk/invariants.py": "tests/test_enforcement_ladder.py",
    "soma_sdk/scoring.py": "tests/test_bayesian_fitness.py",
}


def _relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except (ValueError, OSError):
        return str(path)


def _failure(
    check: str,
    root: Path,
    path: Path,
    operation: str,
    exc: BaseException,
) -> dict:
    rel = _relative(root, path)
    return {
        "check": check,
        "file": rel,
        "message": f"{rel}: {operation} failed: {exc}",
    }


def _is_regular_file(
    check: str,
    root: Path,
    path: Path,
    issues: list[dict],
) -> bool:
    """Validate a checked input without following a symlink."""
    try:
        info = os.stat(path, follow_symlinks=False)
    except FileNotFoundError as exc:
        issues.append(_failure(check, root, path, "stat", exc))
        return False
    except (OSError, UnicodeError) as exc:
        issues.append(_failure(check, root, path, "stat", exc))
        return False
    if stat.S_ISLNK(info.st_mode):
        issues.append({
            "check": check,
            "file": _relative(root, path),
            "message": f"{_relative(root, path)}: symlinked file is not allowed",
        })
        return False
    if not stat.S_ISREG(info.st_mode):
        issues.append({
            "check": check,
            "file": _relative(root, path),
            "message": f"{_relative(root, path)}: expected a regular file",
        })
        return False
    return True


def find_python_files(root: Path, subdir: str) -> list[Path]:
    """Find source files without following symlinked directories."""
    target = root / subdir
    result = []  # type: List[Path]
    try:
        target_info = os.stat(target, follow_symlinks=False)
    except FileNotFoundError:
        return result
    if not stat.S_ISDIR(target_info.st_mode):
        return result

    def walk_error(exc: OSError) -> None:
        raise exc

    for dirpath, dirnames, filenames in os.walk(
        target, topdown=True, followlinks=False, onerror=walk_error
    ):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for filename in sorted(filenames):
            if filename.endswith(".py") and not filename.startswith("__"):
                result.append(Path(dirpath) / filename)
    return result


def _source_dirs(root: Path, check: str, issues: list[dict]) -> list[str]:
    try:
        with os.scandir(root) as it:
            candidates = sorted(it, key=lambda e: e.name)
    except (OSError, UnicodeError) as exc:
        issues.append(_failure(check, root, root, "list", exc))
        return []

    names = []
    for entry in candidates:
        name = entry.name
        if name.startswith(".") or name in SKIP_DIRS or name == "tests":
            continue
        try:
            info = entry.stat(follow_symlinks=False)
        except FileNotFoundError as exc:
            issues.append(_failure(check, root, Path(entry.path), "stat", exc))
            continue
        except (OSError, UnicodeError) as exc:
            issues.append(_failure(check, root, Path(entry.path), "stat", exc))
            continue
        candidate = Path(entry.path)
        if stat.S_ISLNK(info.st_mode):
            issues.append({
                "check": check,
                "file": _relative(root, candidate),
                "message": (
                    f"{_relative(root, candidate)}: "
                    "symlinked source directory is not allowed"
                ),
            })
            continue
        if not stat.S_ISDIR(info.st_mode):
            continue
        try:
            if find_python_files(root, name):
                names.append(name)
        except (OSError, UnicodeError) as exc:
            issues.append(_failure(check, root, candidate, "list", exc))
    return names


def check_test_coverage(root: Path) -> list[dict]:
    issues = []  # type: List[dict]
    source_files = []  # type: List[Path]
    for source_dir in _source_dirs(root, "test_coverage", issues):
        try:
            source_files.extend(find_python_files(root, source_dir))
        except (OSError, UnicodeError) as exc:
            issues.append(_failure(
                "test_coverage", root, root / source_dir, "list", exc
            ))

    test_dir = root / "tests"
    for source_file in source_files:
        if not _is_regular_file(
            "test_coverage", root, source_file, issues
        ):
            continue

        rel_posix = _relative(root, source_file)
        candidates: list[Path] = []

        if rel_posix in SOURCE_TO_TEST_MAP:
            candidates.append(root / SOURCE_TO_TEST_MAP[rel_posix])

        parent_name = source_file.parent.name
        if parent_name == "soma_cli":
            candidates.append(test_dir / f"test_cli_{source_file.stem}.py")
        elif parent_name == "soma_core":
            candidates.append(test_dir / f"test_core_{source_file.stem}.py")
        elif parent_name == "soma_mcp":
            candidates.append(test_dir / f"test_mcp_{source_file.stem}.py")
        elif parent_name == "soma_sdk":
            candidates.append(test_dir / f"test_sdk_{source_file.stem}.py")
        candidates.append(test_dir / f"test_{parent_name}_{source_file.stem}.py")

        candidates.append(test_dir / f"test_{source_file.stem}.py")
        candidates.append(test_dir / "test_verification" / f"test_{source_file.stem}.py")

        matched = False
        for expected in candidates:
            try:
                expected_info = os.stat(expected, follow_symlinks=False)
            except FileNotFoundError:
                continue
            except (OSError, UnicodeError) as exc:
                issues.append(_failure("test_coverage", root, expected, "stat", exc))
                matched = True
                break
            else:
                if stat.S_ISLNK(expected_info.st_mode) or not stat.S_ISREG(expected_info.st_mode):
                    kind = "symlinked" if stat.S_ISLNK(expected_info.st_mode) else "non-regular"
                    issues.append({
                        "check": "test_coverage",
                        "file": _relative(root, expected),
                        "message": (
                            f"{_relative(root, expected)}: {kind} test file "
                            "does not satisfy coverage"
                        ),
                    })
                matched = True
                break

        if not matched:
            issues.append({
                "check": "test_coverage",
                "file": rel_posix,
                "message": (
                    f"Missing test file for {source_file.name}: "
                    f"expected tests/test_{source_file.stem}.py"
                ),
            })
    return issues


def check_hardcoded_paths(root: Path) -> list[dict]:
    issues = []  # type: List[dict]
    for source_dir in _source_dirs(root, "hardcoded_paths", issues):
        try:
            files = find_python_files(root, source_dir)
        except (OSError, UnicodeError) as exc:
            issues.append(_failure(
                "hardcoded_paths", root, root / source_dir, "list", exc
            ))
            continue
        for py_file in files:
            if not _is_regular_file(
                "hardcoded_paths", root, py_file, issues
            ):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                issues.append(_failure(
                    "hardcoded_paths", root, py_file, "read", exc
                ))
                continue
            for line_no, line in enumerate(content.splitlines(), 1):
                if HARDCODED_PATH_RE.search(line):
                    issues.append({
                        "check": "hardcoded_paths",
                        "file": _relative(root, py_file),
                        "line": line_no,
                        "message": (
                            f"Hardcoded absolute path found in "
                            f"{py_file.name}:{line_no}"
                        ),
                    })
    return issues


def check_assertion_density(root: Path) -> list[dict]:
    issues = []  # type: List[dict]
    try:
        test_files = find_python_files(root, "tests")
    except (OSError, UnicodeError) as exc:
        return [_failure("assertion_density", root, root / "tests", "list", exc)]

    for test_file in test_files:
        if not test_file.name.startswith("test_"):
            continue
        if not _is_regular_file(
            "assertion_density", root, test_file, issues
        ):
            continue
        try:
            content = test_file.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            issues.append(_failure(
                "assertion_density", root, test_file, "read", exc
            ))
            continue
        has_assertion = (
            "assert " in content
            or "assert(" in content
            or "pytest.raises" in content
            or "pytest.fail" in content
            or "self.assert" in content
        )
        if not has_assertion:
            try:
                from immune_system.verification.quality_gate import (
                    check_assertion_density as ast_check,
                )
                evidence = ast_check(str(test_file))
                if evidence.verdict:
                    continue
            except (OSError, UnicodeError, ValueError, SyntaxError) as exc:
                issues.append(_failure(
                    "assertion_density", root, test_file, "parse", exc
                ))
                continue
            except ImportError:
                pass
            issues.append({
                "check": "assertion_density",
                "file": _relative(root, test_file),
                "message": (
                    f"Low assertion density in {test_file.name}: "
                    "no assert statements found"
                ),
            })
    return issues


def check_cell_fitness(root: Path) -> list[dict]:
    issues = []  # type: List[dict]
    evidence_dir = root / ".soma" / "evidence"
    aggregation = aggregate_signals(evidence_dir)

    for error in aggregation.errors:
        error_path = Path(error.get("file") or evidence_dir / "signals.jsonl")
        rel = _relative(root, error_path)
        line = error.get("line")
        location = f" line {line}" if line is not None else ""
        issues.append({
            "check": "cell_fitness",
            "file": rel,
            "message": f"{rel}:{location} {error.get('error', 'signal aggregation failed')}",
        })

    for cell_id, counts in aggregation.counts.items():
        tp = counts["tp"]
        fp = counts["fp"]
        total = tp + fp
        if total >= 2 and fp / total > 0.5:
            rate = fp / total
            issues.append({
                "check": "cell_fitness",
                "cell_id": cell_id,
                "message": (
                    f"Cell '{cell_id}' has unhealthy fitness: "
                    f"{fp}/{total} false positives "
                    f"({rate:.0%} FP rate)"
                ),
            })
    return issues


def check_cell_conventions(root: Path) -> list[dict]:
    issues = []  # type: List[dict]
    from soma_core.cell_inventory import CellInventoryError, inventory_cells

    try:
        inventory = inventory_cells(str(root))
    except CellInventoryError as exc:
        path = Path(exc.path)
        issues.append(_failure(
            "cell_conventions", root, path, exc.operation, exc
        ))
        return issues

    from soma_mcp.jit_engine import parse_frontmatter

    for entry in inventory.entries:
        if os.path.basename(entry.relative_path) == "README.md":
            continue
        parts = entry.relative_path.split("/")
        if len(parts) < 4 or parts[:2] != [".soma", "cells"]:
            continue
        type_dir_name = parts[2]
        expected_type = DIR_TO_TYPE.get(type_dir_name)
        if expected_type is None:
            continue
        rel = entry.relative_path
        try:
            content = entry.content.decode("utf-8")
        except UnicodeDecodeError as exc:
            issues.append(_failure(
                "cell_conventions", root, Path(entry.absolute_path), "decode", exc
            ))
            continue
        if not content.startswith("---"):
            issues.append({
                "check": "cell_conventions",
                "file": rel,
                "message": f"{rel}: missing YAML frontmatter",
            })
            continue
        lines = content.splitlines()
        closing = next(
            (index for index, line in enumerate(lines[1:], 1) if line.strip() == "---"),
            None,
        )
        if closing is None:
            issues.append({
                "check": "cell_conventions",
                "file": rel,
                "message": f"{rel}: unterminated YAML frontmatter",
            })
            continue
        try:
            meta = parse_frontmatter(content)
        except Exception as exc:
            issues.append(_failure(
                "cell_conventions", root, Path(entry.absolute_path), "parse", exc
            ))
            continue
        if meta is None:
            frontmatter_lines = [line.strip() for line in lines[1:closing] if line.strip()]
            if frontmatter_lines and frontmatter_lines[0].startswith("-"):
                message = f"{rel}: cell frontmatter must be a mapping"
            else:
                message = f"{rel}: malformed YAML frontmatter"
            issues.append({
                "check": "cell_conventions", "file": rel, "message": message,
            })
            continue
        if not isinstance(meta, dict) or not meta:
            issues.append({
                "check": "cell_conventions",
                "file": rel,
                "message": f"{rel}: cell frontmatter must be a non-empty mapping",
            })
            continue

        required = ["id", "domain", "type"]
        if expected_type in ("wall", "vacuole"):
            required.append("enforcement")
        for field in required:
            if field not in meta:
                issues.append({
                    "check": "cell_conventions",
                    "file": rel,
                    "message": f"{rel}: missing required field '{field}'",
                })
        cell_type = meta.get("type", "")
        if cell_type != expected_type:
            issues.append({
                "check": "cell_conventions",
                "file": rel,
                "message": (
                    f"{rel}: type '{cell_type}' doesn't match directory "
                    f"'{type_dir_name}' (expected '{expected_type}')"
                ),
            })
        if expected_type == "wall" and meta.get("enforcement") != "gate":
            issues.append({
                "check": "cell_conventions",
                "file": rel,
                "message": (
                    f"{rel}: wall enforcement is '{meta.get('enforcement')}' "
                    "but walls must use 'gate'"
                ),
            })
        stem = os.path.splitext(os.path.basename(entry.relative_path))[0]
        if meta.get("id") != stem:
            issues.append({
                "check": "cell_conventions",
                "file": rel,
                "message": (
                    f"{rel}: frontmatter id '{meta.get('id')}' "
                    f"doesn't match filename '{stem}'"
                ),
            })
    return issues


def check_arbitration_evidence(root: Path, strict: bool = False) -> list[dict]:
    issues = []  # type: List[dict]
    evidence_dir = root / ".soma" / "evidence"
    try:
        info = os.stat(evidence_dir, follow_symlinks=False)
    except FileNotFoundError:
        if strict:
            return [{
                "check": "arbitration_evidence",
                "file": _relative(root, evidence_dir),
                "message": f"{_relative(root, evidence_dir)}: evidence directory not found",
            }]
        return issues
    except (OSError, UnicodeError) as exc:
        return [_failure(
            "arbitration_evidence", root, evidence_dir, "stat", exc
        )]
    if not stat.S_ISDIR(info.st_mode):
        return [{
            "check": "arbitration_evidence",
            "file": _relative(root, evidence_dir),
            "message": f"{_relative(root, evidence_dir)}: expected a directory",
        }]
    files: list[Path] = []
    try:
        with os.scandir(evidence_dir) as it:
            for entry in it:
                if entry.name.startswith("arbitration_cycle_") and entry.name.endswith(".json") and entry.is_file():
                    files.append(Path(entry.path))
    except (OSError, UnicodeError) as exc:
        return [_failure(
            "arbitration_evidence", root, evidence_dir, "list", exc
        )]
    if not files:
        if strict:
            return [{
                "check": "arbitration_evidence",
                "file": _relative(root, evidence_dir),
                "message": f"{_relative(root, evidence_dir)}: no arbitration cycles found in evidence directory",
            }]
        return issues


    def cycle_number(path: Path) -> int:
        match = re.search(r"cycle_(\d+)", str(path))
        return int(match.group(1)) if match else 0

    latest = sorted(files, key=cycle_number)[-1]
    if not _is_regular_file(
        "arbitration_evidence", root, latest, issues
    ):
        return issues
    try:
        text = latest.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [_failure(
            "arbitration_evidence", root, latest, "read", exc
        )]
    try:
        record = json.loads(text)
    except (json.JSONDecodeError, UnicodeError) as exc:
        return [_failure(
            "arbitration_evidence", root, latest, "parse", exc
        )]
    if not isinstance(record, dict):
        return [{
            "check": "arbitration_evidence",
            "file": _relative(root, latest),
            "message": f"{_relative(root, latest)}: evidence must be a JSON object",
        }]

    verdict = str(record.get("verdict", "unknown")).lower()
    cycle = record.get("cycle", "?")
    divergences = record.get("divergence_count", 0)
    if verdict == "block":
        message = (
            f"Arbiter verdict is BLOCK for cycle {cycle} "
            f"({divergences} divergence(s)). Fix all findings before ship."
        )
    elif verdict == "revise":
        message = (
            f"Arbiter verdict is REVISE for cycle {cycle} "
            f"({divergences} divergence(s)). Address high-severity findings."
        )
    elif verdict != "ship":
        message = (
            f"Unknown arbiter verdict '{verdict}' for cycle {cycle}. "
            "Only 'ship' passes the gate."
        )
    else:
        return issues
    issues.append({
        "check": "arbitration_evidence",
        "file": _relative(root, latest),
        "message": message,
    })
    return issues


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


def run_all_checks(root: Path, strict: bool = False) -> list[dict]:
    """Run every check and convert unexpected check failures into issues."""
    issues = []  # type: List[dict]
    for check_fn in ALL_CHECKS:
        try:
            if check_fn == check_arbitration_evidence:
                issues.extend(check_fn(root, strict=strict))
            else:
                issues.extend(check_fn(root))
        except Exception as exc:
            check_name = check_fn.__name__.replace("check_", "", 1)
            issues.append(_failure(check_name, root, root, "check", exc))
    return issues

