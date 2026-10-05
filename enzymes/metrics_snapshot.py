#!/usr/bin/env python3
"""metrics_snapshot.py: Generates governance metrics and idle token overhead snapshots.

Usage:
    python enzymes/metrics_snapshot.py [--json] [--raw] [--save] [--compare <file>]
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from datetime import timezone
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from enzymes.soma_resolve import resolve_workspace


def resolve_metrics_dir(workspace: Path | str) -> Path:
    """Resolve where metrics snapshots are stored. Respects TEAM_REPO or METRICS_REPO."""
    team_repo = os.environ.get("TEAM_REPO")
    team_member = os.environ.get("TEAM_MEMBER_ID", "local_user")
    metrics_repo = os.environ.get("METRICS_REPO")

    ws = Path(workspace).resolve()
    conf_path = ws / "soma.conf"
    if (not team_repo or not metrics_repo) and conf_path.is_file():
        with open(conf_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("TEAM_REPO=") and not line.startswith("#"):
                    team_repo = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("TEAM_MEMBER_ID=") and not line.startswith("#"):
                    team_member = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("METRICS_REPO=") and not line.startswith("#"):
                    metrics_repo = line.split("=", 1)[1].strip().strip('"').strip("'")

    if team_repo:
        path = Path(os.path.expanduser(team_repo)) / "snapshots" / team_member
        path.mkdir(parents=True, exist_ok=True)
        return path

    if metrics_repo:
        path = Path(os.path.expanduser(metrics_repo))
        path.mkdir(parents=True, exist_ok=True)
        return path

    default = ws / "docs" / "snapshots"
    default.mkdir(parents=True, exist_ok=True)
    return default


def take_snapshot(
    json_mode: bool = False,
    raw_mode: bool = False,
    compare_file: str | None = None,
    save: bool = False,
    workspace: Path | None = None,
) -> int:
    ws = Path(workspace).resolve() if workspace else Path(resolve_workspace(__file__)).resolve()
    metrics_dir = resolve_metrics_dir(ws)

    census_script = ws / "enzymes" / "token_census.py"
    result = subprocess.run([sys.executable, str(census_script), "--json"], capture_output=True, text=True)
    if result.returncode != 0:
        print("Error running token_census.py", file=sys.stderr)
        return 1

    census = json.loads(result.stdout)

    always_on_rules = sum(1 for r in census["files"] if r["type"] == "always_on_rule")
    conditional_rules = sum(1 for r in census["files"] if r["type"] == "conditional_rule")
    skills_count = sum(1 for r in census["files"] if r["type"] == "skill")

    prong_budgets = {}
    staff_review_path = ws / "organs" / "staff-review" / "SKILL.md"
    if staff_review_path.is_file():
        content = staff_review_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            match = re.search(
                r'\|\s*.*?(Spores|Mycelium|Roots|Thorns|Bedrock|Mulch).*?\|\s*\**([0-9,]+\s*tokens).*?\|',
                line,
                re.IGNORECASE,
            )
            if match:
                prong_budgets[match.group(1)] = match.group(2).strip()

    waste_rate_best = "1.1%"
    waste_rate_avg = "18.8%"

    cells_count = 0
    cells_dir = ws / ".soma" / "cells"
    if cells_dir.is_dir():
        for f in cells_dir.rglob("*.md"):
            cells_count += 1

    metrics = {
        "rules_always_on": always_on_rules,
        "rules_conditional": conditional_rules,
        "skills_count": skills_count,
        "cells_count": cells_count,
        "tokens": census["subtotals"],
        "grand_total_idle_overhead": census["grand_total_idle"],
        "calibrated_ratio": census["calibrated_ratio"],
        "waste_rate_best": waste_rate_best,
        "waste_rate_avg": waste_rate_avg,
        "prong_budgets": prong_budgets,
        "metrics_dir": str(metrics_dir),
    }

    if raw_mode:
        metrics["timestamp"] = datetime.datetime.now(timezone.utc).isoformat() + "Z"

    compare_data = None
    if compare_file and os.path.exists(compare_file):
        with open(compare_file, "r", encoding="utf-8") as f:
            compare_data = json.load(f)

    if save:
        ts = datetime.datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        save_path = metrics_dir / f"snapshot-{ts}.json"
        save_metrics = dict(metrics)
        save_metrics["timestamp"] = datetime.datetime.now(timezone.utc).isoformat() + "Z"
        save_metrics.pop("metrics_dir", None)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(save_metrics, f, indent=2)
        print(f"Saved to: {save_path}", file=sys.stderr)

    if json_mode:
        output = dict(metrics)
        output.pop("metrics_dir", None)
        print(json.dumps(output, indent=2))
    else:
        print("=== SOMA: METRICS SNAPSHOT ===")
        if raw_mode:
            print(f"Timestamp: {metrics.get('timestamp')}")
        print(f"Metrics Dir: {metrics_dir}")
        print("\n[ Counts ]")
        print(f"Rules:  {always_on_rules} always-on, {conditional_rules} conditional")
        print(f"Skills: {skills_count}")
        print(f"Cells:  {metrics.get('cells_count', 0)}")

        print("\n[ Tokens ]")
        print(f"Always-On Rules (Idle):    {metrics['tokens']['always_on_rules_idle_tokens']}")
        print(f"Conditional Rules Idle:    {metrics['tokens']['conditional_rules_idle_tokens']}")
        print(f"Skills Idle:               {metrics['tokens']['skills_idle_tokens']}")
        print(f"GRAND TOTAL IDLE OVERHEAD: {metrics['grand_total_idle_overhead']}")
        print(f"Calibrated Ratio:          {metrics['calibrated_ratio']}")

        print("\n[ Waste Rates ]")
        print(f"Best Governed:             {waste_rate_best}")
        print(f"Avg Governed:              {waste_rate_avg}")

        if prong_budgets:
            print("\n[ Prong Budgets ]")
            for p, b in prong_budgets.items():
                print(f"  {p}: {b}")

        if compare_data:
            print("\n[ Deltas vs Previous ]")
            prev_total = compare_data.get("grand_total_idle_overhead", 0)
            diff = metrics["grand_total_idle_overhead"] - prev_total
            print(f"Grand Total Idle Overhead: {diff:+d}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Metrics snapshot generator")
    parser.add_argument("--json", action="store_true", default=False, help="Output JSON format")
    parser.add_argument("--raw", action="store_true", default=False, help="Include timestamp in output")
    parser.add_argument("--save", action="store_true", default=False, help="Save snapshot to file")
    parser.add_argument("--compare", dest="compare_file", default=None, help="Compare with previous snapshot")
    args = parser.parse_args(argv)

    return take_snapshot(
        json_mode=args.json,
        raw_mode=args.raw,
        compare_file=args.compare_file,
        save=args.save,
    )


if __name__ == "__main__":
    sys.exit(main())
