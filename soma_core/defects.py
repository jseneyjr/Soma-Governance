"""soma_core.defects — Defect analysis, escaped defect tracking, and cell expiry.

Consolidates:
- Hot zone analysis and diagnostics (formerly soma_sdk.hot_zones & enzymes/diagnose_hot_zones.py)
- Escaped defect detection and prevention rate tracking (formerly enzymes/cell_escaped_defects.py)
- Cell lifecycle expiry enforcement and pruning (formerly enzymes/cell_expiry.py)
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import fnmatch
import glob
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from soma_core.workspace import resolve_workspace
from soma_core.frontmatter import parse_frontmatter, _get_body, dump_frontmatter

# ── Hot Zone Analysis ──────────────────────────────────────────────────────


@dataclass
class BoostConfig:
    """Tunable parameters for hot zone scoring."""
    file_heat_threshold: int = 2
    pattern_heat_threshold: int = 3
    release_window: int = 10
    min_outcomes_for_boost: int = 3
    max_file_boost: float = 0.5
    max_pattern_boost: float = 0.3


@dataclass
class HotZoneReport:
    """Computed boost data from the bug registry."""
    file_heat: dict[str, int] = field(default_factory=dict)
    pattern_heat: dict[str, int] = field(default_factory=dict)
    active_file_zones: list[str] = field(default_factory=list)
    active_pattern_zones: list[str] = field(default_factory=list)
    config: BoostConfig = field(default_factory=BoostConfig)
    total_bugs_analyzed: int = 0


def load_config(registry: dict) -> BoostConfig:
    """Extract boost config from registry, falling back to defaults."""
    raw = registry.get("boost_config", {})
    return BoostConfig(
        file_heat_threshold=raw.get("file_heat_threshold", 2),
        pattern_heat_threshold=raw.get("pattern_heat_threshold", 3),
        release_window=raw.get("release_window", 10),
        min_outcomes_for_boost=raw.get("min_outcomes_for_boost", 3),
        max_file_boost=raw.get("max_file_boost", 0.5),
        max_pattern_boost=raw.get("max_pattern_boost", 0.3),
    )


def compute_hot_zones(registry: dict) -> HotZoneReport:
    """Pure function: registry dict -> HotZoneReport."""
    config = load_config(registry)
    bugs = registry.get("bugs", [])

    file_heat: dict[str, int] = {}
    for bug in bugs:
        for f in bug.get("affected_files", []):
            file_heat[f] = file_heat.get(f, 0) + 1

    pattern_heat: dict[str, int] = {}
    for bug in bugs:
        cat = bug.get("root_cause", "")
        if cat:
            pattern_heat[cat] = pattern_heat.get(cat, 0) + 1

    active_files = sorted(
        [f for f, count in file_heat.items() if count >= config.file_heat_threshold],
        key=lambda f: -file_heat[f],
    )
    active_patterns = sorted(
        [p for p, count in pattern_heat.items() if count >= config.pattern_heat_threshold],
        key=lambda p: -pattern_heat[p],
    )

    return HotZoneReport(
        file_heat=file_heat,
        pattern_heat=pattern_heat,
        active_file_zones=active_files,
        active_pattern_zones=active_patterns,
        config=config,
        total_bugs_analyzed=len(bugs),
    )


def compute_cell_boost(
    cell: dict[str, Any],
    report: HotZoneReport,
    outcome_count: int = 0,
) -> float:
    """Compute the fitness boost multiplier for a single cell."""
    if outcome_count < report.config.min_outcomes_for_boost:
        return 0.0

    file_boost = 0.0
    pattern_boost = 0.0

    target_paths = cell.get("target_paths", [])
    if target_paths and report.active_file_zones:
        for hot_file in report.active_file_zones:
            for pattern in target_paths:
                if fnmatch.fnmatch(hot_file, pattern):
                    heat = report.file_heat.get(hot_file, 0)
                    file_boost += heat * 0.1
                    break

    cell_tags = set(cell.get("tags", []))
    tag_to_category = {
        "data_path": "path_error",
        "path": "path_error",
        "schema": "schema_drift",
        "data_model": "schema_drift",
        "silent": "silent_failure",
        "error_handling": "silent_failure",
        "mapping": "mapping_error",
        "type_coercion": "mapping_error",
        "dead_code": "dead_code",
        "unused": "dead_code",
    }
    for tag in cell_tags:
        category = tag_to_category.get(tag, tag)
        if category in report.active_pattern_zones:
            heat = report.pattern_heat.get(category, 0)
            pattern_boost += heat * 0.1

    file_boost = min(file_boost, report.config.max_file_boost)
    pattern_boost = min(pattern_boost, report.config.max_pattern_boost)

    return file_boost + pattern_boost


def load_registry(workspace: str) -> dict | None:
    """Load BUG_REGISTRY.json, returning None if missing."""
    path = os.path.join(workspace, "docs", "project", "BUG_REGISTRY.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def load_report_from_workspace(workspace: str) -> HotZoneReport | None:
    """Convenience: load registry from disk and compute report."""
    registry = load_registry(workspace)
    if registry is None:
        return None
    try:
        return compute_hot_zones(registry)
    except Exception:
        return None


def proximity_alerts(report: HotZoneReport) -> list[str]:
    """Report how close each category/file is to activating."""
    alerts = []
    config = report.config

    for cat, count in sorted(report.pattern_heat.items(), key=lambda x: -x[1]):
        remaining = config.pattern_heat_threshold - count
        if remaining <= 0:
            alerts.append(f"  🔥 {cat}: {count}/{config.pattern_heat_threshold} — ACTIVE")
        elif remaining <= 2:
            alerts.append(
                f"  ⚠️  {cat}: {count}/{config.pattern_heat_threshold} "
                f"— {remaining} more bug(s) to activate"
            )
        else:
            alerts.append(f"  ·  {cat}: {count}/{config.pattern_heat_threshold}")

    for f, count in sorted(report.file_heat.items(), key=lambda x: -x[1]):
        remaining = config.file_heat_threshold - count
        if remaining <= 0:
            alerts.append(f"  🔥 {f}: {count}/{config.file_heat_threshold} — ACTIVE")
        elif remaining == 1:
            alerts.append(
                f"  ⚠️  {f}: {count}/{config.file_heat_threshold} "
                f"— 1 more bug to activate"
            )

    return alerts


def threshold_sanity(report: HotZoneReport) -> list[str]:
    """Check if thresholds seem miscalibrated."""
    warnings = []
    total = report.total_bugs_analyzed
    config = report.config
    active_count = len(report.active_file_zones) + len(report.active_pattern_zones)

    if total < 10:
        warnings.append(
            f"ℹ️  Insufficient data ({total} bugs). "
            f"Thresholds untested — revisit after 10+ bugs."
        )
        return warnings

    if total >= 20 and active_count == 0:
        warnings.append(
            f"⚠️  {total} bugs registered but zero hot zones activated. "
            f"Consider lowering thresholds "
            f"(file: {config.file_heat_threshold}, pattern: {config.pattern_heat_threshold})."
        )

    total_files = len(report.file_heat)
    if total_files > 0 and len(report.active_file_zones) > total_files / 3:
        warnings.append(
            f"⚠️  {len(report.active_file_zones)}/{total_files} files are hot zones. "
            f"Thresholds may be too low — consider raising file_heat_threshold "
            f"from {config.file_heat_threshold}."
        )

    total_patterns = len(report.pattern_heat)
    if total_patterns > 0 and len(report.active_pattern_zones) > total_patterns / 2:
        warnings.append(
            f"⚠️  {len(report.active_pattern_zones)}/{total_patterns} categories "
            f"are hot zones. Consider raising pattern_heat_threshold "
            f"from {config.pattern_heat_threshold}."
        )

    return warnings


def run_diagnostic(workspace: str) -> dict:
    """Run full diagnostic and return structured results."""
    registry = load_registry(workspace)
    if registry is None:
        return {"error": "BUG_REGISTRY.json not found"}

    report = compute_hot_zones(registry)

    return {
        "total_bugs": report.total_bugs_analyzed,
        "proximity": proximity_alerts(report),
        "sanity": threshold_sanity(report),
        "active_files": report.active_file_zones,
        "active_patterns": report.active_pattern_zones,
        "file_heat": report.file_heat,
        "pattern_heat": report.pattern_heat,
        "config": {
            "file_heat_threshold": report.config.file_heat_threshold,
            "pattern_heat_threshold": report.config.pattern_heat_threshold,
            "max_file_boost": report.config.max_file_boost,
            "max_pattern_boost": report.config.max_pattern_boost,
        },
    }


def cli_diagnose_hot_zones(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnose Hot Zones")
    parser.add_argument("--workspace", default=None, help="Workspace root")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if args.workspace:
        workspace = args.workspace
    elif os.path.exists(os.path.join(".", "docs", "project", "BUG_REGISTRY.json")):
        workspace = "."
    else:
        workspace = resolve_workspace()

    result = run_diagnostic(workspace)

    if "error" in result:
        print(f"ERROR: {result['error']}")
        return 0

    print(f"=== Hot Zone Diagnostic ({result['total_bugs']} bugs) ===\n")
    print("Proximity to activation:")
    for line in result["proximity"]:
        print(line)

    print(
        f"\nActive hot zones: "
        f"{len(result['active_files'])} files, "
        f"{len(result['active_patterns'])} patterns"
    )

    if result["sanity"]:
        print("\nThreshold health:")
        for line in result["sanity"]:
            print(f"  {line}")

    cfg = result["config"]
    print(
        f"\nConfig: file_heat≥{cfg['file_heat_threshold']}, "
        f"pattern_heat≥{cfg['pattern_heat_threshold']}, "
        f"max_file_boost={cfg['max_file_boost']}, "
        f"max_pattern_boost={cfg['max_pattern_boost']}"
    )
    return 0


# ── Escaped Defects Tracking ──────────────────────────────────────────────


def match_glob(filepath: str, pattern: str) -> bool:
    """Match a filepath against a glob pattern, supporting ** globstar."""
    regex = pattern.replace(".", r"\.")
    regex = regex.replace("?", "[^/]")
    regex = regex.replace("**/", "(?:.+/)?")
    regex = regex.replace("**", ".*")
    regex = regex.replace("*", "[^/]*")
    return bool(re.match(regex + "$", filepath))


def load_cells(cells_dir: str) -> list[dict]:
    """Load all cells with their metadata."""
    cells = []
    for cell_file in glob.glob(os.path.join(cells_dir, "**", "*.md"), recursive=True):
        if os.path.basename(cell_file) == "README.md":
            continue
        try:
            with open(cell_file, "r", encoding="utf-8-sig") as f:
                raw = f.read()
            fm = parse_frontmatter(raw)
            if not fm or not isinstance(fm, dict):
                continue
            body = _get_body(raw)
            fm["_path"] = cell_file
            fm["_name"] = os.path.splitext(os.path.basename(cell_file))[0]
            fm["_body"] = body.strip()
            fm["_raw"] = raw
            cells.append(fm)
        except Exception:
            pass
    return cells


def find_covering_cells(cells: list[dict], files: list[str]) -> list[dict]:
    """Find cells whose target_paths match the given files."""
    covering = []
    for cell in cells:
        target_paths = cell.get("target_paths", [])
        if isinstance(target_paths, str):
            target_paths = [target_paths]
        matched_files = []
        for f in files:
            for pattern in target_paths:
                if match_glob(f, pattern):
                    matched_files.append(f)
                    break
        if matched_files:
            covering.append({
                "cell": cell,
                "matched_files": matched_files,
            })
    return covering


def record_escaped_defect(
    cell: dict,
    event_type: str,
    files: list[str],
    severity: str,
    workspace: str,
) -> dict:
    """Record an escaped defect against a cell."""
    metrics_dir = os.path.join(workspace, ".soma", "metrics")
    os.makedirs(metrics_dir, exist_ok=True)

    log_path = os.path.join(metrics_dir, "escaped_defects.jsonl")
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "cell": cell.get("_name") or cell.get("name", ""),
        "cell_type": cell.get("type", ""),
        "enforcement": cell.get("enforcement", "advisory"),
        "event": event_type,
        "files": files,
        "severity": severity,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return entry


def update_cell_escaped_rate(cell: dict, workspace: str) -> float:
    """Recalculate a cell's escaped_defect_rate from the log."""
    metrics_dir = os.path.join(workspace, ".soma", "metrics")
    log_path = os.path.join(metrics_dir, "escaped_defects.jsonl")
    if not os.path.exists(log_path):
        return 0.0

    escaped = 0
    cell_name = cell.get("_name") or cell.get("name", "")
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry.get("cell") == cell_name:
                    escaped += 1
            except Exception:
                continue

    tp = cell.get("fitness", {}).get("true_positives", 0)
    total = escaped + tp
    if total == 0:
        return 0.0

    return round(escaped / total, 4)


def compute_enhanced_fitness(cell: dict, escaped_defect_rate: float) -> float:
    """Compute fitness with independent outcome signal."""
    tier_weights = {"advisory": 1.0, "mechanical": 1.2, "gate": 1.5}

    tp = cell.get("fitness", {}).get("true_positives", 0)
    fp = cell.get("fitness", {}).get("false_positives", 0)

    a = tp + 0.5
    b = fp + 0.5
    bayesian_mean = a / (a + b)

    enforcement = cell.get("enforcement", "advisory")
    tier_weight = tier_weights.get(enforcement, 1.0)

    enhanced = bayesian_mean * (1 - escaped_defect_rate) * tier_weight
    return round(enhanced, 4)


def scan_git_for_defects(workspace: str, since: str) -> list[dict]:
    """Scan git history for reverted commits, fix-after-fix patterns."""
    git_args = ["git", "log", "--format=%H %s", f"--since={since}"]
    result = subprocess.run(git_args, capture_output=True, text=True, cwd=workspace)

    defect_commits = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        sha, *msg_parts = line.split(" ")
        msg = " ".join(msg_parts).lower()

        if any(kw in msg for kw in ["revert", "hotfix", "fix:", "bugfix", "patch:", "workaround"]):
            try:
                diff_result = subprocess.run(
                    ["git", "diff", "--name-only", f"{sha}~1", sha],
                    capture_output=True, text=True, cwd=workspace
                )
                if diff_result.returncode != 0:
                    continue
                files = [f for f in diff_result.stdout.strip().split("\n") if f]
            except Exception:
                continue
            if files:
                defect_commits.append({
                    "sha": sha[:8],
                    "message": " ".join(msg_parts),
                    "files": files,
                    "severity": "high" if "revert" in msg else "medium",
                })

    return defect_commits


def generate_report(cells: list[dict], workspace: str) -> tuple[list[dict], int]:
    """Generate escaped defects report."""
    metrics_dir = os.path.join(workspace, ".soma", "metrics")
    log_path = os.path.join(metrics_dir, "escaped_defects.jsonl")

    cell_escapes: dict[str, int] = {}
    total_escapes = 0
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    name = entry.get("cell", "")
                    cell_escapes[name] = cell_escapes.get(name, 0) + 1
                    total_escapes += 1
                except Exception:
                    continue

    report = []
    for cell in cells:
        name = cell.get("_name") or cell.get("name", "")
        escapes = cell_escapes.get(name, 0)
        tp = cell.get("fitness", {}).get("true_positives", 0)
        fp = cell.get("fitness", {}).get("false_positives", 0)
        enforcement = cell.get("enforcement", "advisory")

        escaped_rate = update_cell_escaped_rate(cell, workspace)
        enhanced_fitness = compute_enhanced_fitness(cell, escaped_rate)
        prevention_rate = 1 - escaped_rate

        report.append({
            "cell": name,
            "type": cell.get("type", ""),
            "enforcement": enforcement,
            "tp": tp,
            "fp": fp,
            "escaped": escapes,
            "escaped_defect_rate": escaped_rate,
            "defect_prevention_rate": round(prevention_rate, 4),
            "enhanced_fitness": enhanced_fitness,
        })

    return report, total_escapes


def cli_cell_escaped_defects(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Track defects that escaped governance coverage")
    parser.add_argument("--event", choices=["crash", "test_failure", "build_failure", "rework", "regression"])
    parser.add_argument("--files", nargs="+", help="Files involved in the defect")
    parser.add_argument("--severity", choices=["low", "medium", "high", "critical"], default="medium")
    parser.add_argument("--scan-git", action="store_true", help="Auto-detect escaped defects from git")
    parser.add_argument("--since", default="7 days ago", help="Git history lookback")
    parser.add_argument("--report", action="store_true", help="Generate escaped defects report")
    parser.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    workspace = resolve_workspace()
    cells_dir = os.path.join(workspace, ".soma", "cells")
    cells = load_cells(cells_dir)

    if not cells:
        print("No cells found.")
        return 0

    if args.report:
        report, total = generate_report(cells, workspace)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"\n🛡️  Escaped Defects Report ({total} total escaped defects)\n")
            print(f"{'Cell':<25} {'Type':<10} {'Tier':<12} {'TP':>4} {'FP':>4} {'Esc':>4} {'Prevention':>10} {'Enhanced':>10}")
            print("─" * 90)
            for r in sorted(report, key=lambda x: x["enhanced_fitness"], reverse=True):
                print(f"{r['cell']:<25} {r['type']:<10} {r['enforcement']:<12} {r['tp']:>4} {r['fp']:>4} {r['escaped']:>4} {r['defect_prevention_rate']:>9.1%} {r['enhanced_fitness']:>10.4f}")
        return 0

    if args.scan_git:
        defects = scan_git_for_defects(workspace, args.since)
        if not defects:
            print(f"No escaped defects found in git history since \"{args.since}\".")
            return 0

        total_recorded = 0
        for defect in defects:
            covering = find_covering_cells(cells, defect["files"])
            for cov in covering:
                record_escaped_defect(
                    cov["cell"], "git_" + defect["severity"],
                    defect["files"], defect["severity"], workspace
                )
                total_recorded += 1
                if not args.json:
                    print(f"⚠️  {defect['sha']} \"{defect['message'][:60]}\"")
                    print(f"   Escaped cell: {cov['cell']['_name']} (covers {len(cov['matched_files'])} of {len(defect['files'])} files)")

        if args.json:
            print(json.dumps({"scanned_commits": len(defects), "escaped_recorded": total_recorded}))
        else:
            print(f"\nRecorded {total_recorded} escaped defects from {len(defects)} commits.")
        return 0

    if args.event and args.files:
        covering = find_covering_cells(cells, args.files)
        if not covering:
            if not args.json:
                print(f"No cells cover the affected files: {', '.join(args.files)}")
                print("This is a governance blind spot — consider creating cells for these paths.")
            return 0

        recorded = []
        for cov in covering:
            entry = record_escaped_defect(
                cov["cell"], args.event, args.files, args.severity, workspace
            )
            recorded.append(entry)
            if not args.json:
                escaped_rate = update_cell_escaped_rate(cov["cell"], workspace)
                print(f"⚠️  Escaped defect recorded against: {cov['cell']['_name']}")
                print(f"   Event: {args.event} | Severity: {args.severity}")
                print(f"   Escaped defect rate: {escaped_rate:.1%}")
                print(f"   Files: {', '.join(cov['matched_files'])}")

        if args.json:
            print(json.dumps(recorded, indent=2))
        return 0

    parser.print_help()
    return 0


# ── Cell Expiry Enforcement ────────────────────────────────────────────────


def audit_expiry(workspace: str, session_count: Optional[int] = None) -> list[dict]:
    """Audit all cells for expiry violations."""
    cells_dir = os.path.join(workspace, ".soma", "cells")
    if not os.path.isdir(cells_dir):
        return []

    results = []
    now = datetime.now()

    for md_file in sorted(glob.glob(os.path.join(cells_dir, "**", "*.md"), recursive=True)):
        if os.path.basename(md_file) == "README.md":
            continue

        try:
            with open(md_file, "r", encoding="utf-8-sig") as f:
                content = f.read()
            metadata = parse_frontmatter(content)
            if not metadata or not isinstance(metadata, dict):
                continue
        except Exception:
            continue

        cell_id = metadata.get("id", os.path.basename(md_file))
        cell_type = metadata.get("type", "unknown")
        is_wall = cell_type == "wall"

        if metadata.get("expired_at"):
            results.append({
                "cell_id": cell_id,
                "filepath": md_file,
                "status": "ALREADY_EXPIRED",
                "reason": "previously_pruned",
                "details": f"Expired at {metadata['expired_at']}",
            })
            continue

        expired = False
        reason = None
        details = None

        expiry_days = metadata.get("expiry_days")
        created_val = metadata.get("created")
        if expiry_days and created_val:
            try:
                expiry_days = int(expiry_days)
                if isinstance(created_val, datetime):
                    created_date = created_val
                elif hasattr(created_val, "isoformat"):
                    created_date = datetime.combine(created_val, datetime.min.time())
                else:
                    created_str = str(created_val).replace("Z", "+00:00")
                    try:
                        created_date = datetime.fromisoformat(created_str)
                        if created_date.tzinfo:
                            created_date = created_date.replace(tzinfo=None)
                    except ValueError:
                        fmt = "%Y-%m-%d"
                        created_date = datetime.strptime(created_str[:10], fmt)
                days_elapsed = (now - created_date).days
                if days_elapsed > expiry_days:
                    expired = True
                    reason = "expiry_days"
                    details = f"{days_elapsed} days elapsed (limit: {expiry_days})"
            except Exception:
                pass

        if not expired and session_count is not None:
            expiry_sessions = metadata.get("expiry_sessions")
            if expiry_sessions:
                try:
                    expiry_sessions = int(expiry_sessions)
                    if session_count > expiry_sessions:
                        expired = True
                        reason = "expiry_sessions"
                        details = f"{session_count} sessions elapsed (limit: {expiry_sessions})"
                except (ValueError, TypeError):
                    pass

        if expired:
            status = "EXPIRY_WARNING" if is_wall else "EXPIRED"
        else:
            status = "OK"

        results.append({
            "cell_id": cell_id,
            "filepath": md_file,
            "status": status,
            "reason": reason,
            "details": details,
        })

    return results


def prune_expired(workspace: str, audit_results: list[dict]) -> int:
    """Add expired_at marker to expired cells."""
    pruned = 0
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    for result in audit_results:
        if result["status"] != "EXPIRED":
            continue

        filepath = result["filepath"]
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                content = f.read()
            metadata = parse_frontmatter(content) or {}
            body = _get_body(content)
        except Exception:
            continue

        metadata["expired_at"] = now_str
        metadata["expired_reason"] = result.get("reason", "unknown")

        try:
            import yaml
            new_fm = yaml.dump(metadata, default_flow_style=False, sort_keys=False)
            new_content = "---\n" + new_fm + "---\n" + body + ("\n" if not body.endswith("\n") else "")
        except Exception:
            new_fm = dump_frontmatter(metadata)
            new_content = "---\n" + new_fm + "---\n" + body + ("\n" if not body.endswith("\n") else "")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

        pruned += 1

    return pruned


def cli_cell_expiry(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit and enforce cell expiry limits")
    parser.add_argument("workspace", nargs="?", default=".", help="Project workspace root")
    parser.add_argument("--prune", action="store_true", help="Add expired_at marker to expired cells")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--session-count", type=int, default=None, help="Number of sessions elapsed")

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if args.workspace != ".":
        os.environ["SOMA_ROOT"] = os.path.abspath(args.workspace)
    workspace = resolve_workspace()
    results = audit_expiry(workspace, session_count=args.session_count)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        expired = [r for r in results if r["status"] in ("EXPIRED", "EXPIRY_WARNING")]
        ok = [r for r in results if r["status"] == "OK"]
        already = [r for r in results if r["status"] == "ALREADY_EXPIRED"]

        print(f"Cells audited: {len(results)}")
        print(f"  OK: {len(ok)}")
        print(f"  Expired: {len(expired)}")
        print(f"  Already pruned: {len(already)}")

        if expired:
            print("\nExpired cells:")
            for r in expired:
                icon = "⚠️" if r["status"] == "EXPIRY_WARNING" else "❌"
                print(f"  {icon} {r['cell_id']}: {r['details']} ({r['reason']})")

    if args.prune:
        pruned = prune_expired(workspace, results)
        print(f"\nPruned {pruned} cell(s)")
        if pruned > 0:
            return 0

    return 0 if not any(r["status"] == "EXPIRED" for r in results) else 1


__all__ = [
    "BoostConfig",
    "HotZoneReport",
    "load_config",
    "compute_hot_zones",
    "compute_cell_boost",
    "load_registry",
    "load_report_from_workspace",
    "proximity_alerts",
    "threshold_sanity",
    "run_diagnostic",
    "cli_diagnose_hot_zones",
    "match_glob",
    "load_cells",
    "find_covering_cells",
    "record_escaped_defect",
    "update_cell_escaped_rate",
    "compute_enhanced_fitness",
    "scan_git_for_defects",
    "generate_report",
    "cli_cell_escaped_defects",
    "audit_expiry",
    "prune_expired",
    "cli_cell_expiry",
]
