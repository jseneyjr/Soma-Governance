#!/usr/bin/env bash

# Source common.sh
source "$(dirname "$0")/common.sh" 2>/dev/null || true

# Forward arguments to python logic
python3 - "$@" << 'PYEOF'
import sys
import json
import os
import re
import datetime
import subprocess

def parse_args():
    args = sys.argv[1:]
    json_mode = "--json" in args
    raw_mode = "--raw" in args
    save = "--save" in args
    compare_file = None
    if "--compare" in args:
        idx = args.index("--compare")
        if idx + 1 < len(args):
            compare_file = args[idx+1]
    return json_mode, raw_mode, compare_file, save

def resolve_workspace():
    """Find workspace root by walking up from this script's location."""
    d = os.path.dirname(os.path.abspath(__file__))
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, "rules")) and os.path.isdir(os.path.join(d, "skills")):
            return d
        d = os.path.dirname(d)
    return os.getcwd()

def resolve_metrics_dir(workspace):
    """Resolve where metrics snapshots are stored. Respects METRICS_REPO from env or steering.conf."""
    # Environment variable takes precedence
    metrics_repo = os.environ.get("METRICS_REPO")

    # Fall back to steering.conf
    if not metrics_repo:
        conf_path = os.path.join(workspace, "steering.conf")
        if os.path.exists(conf_path):
            with open(conf_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("METRICS_REPO=") and not line.startswith("#"):
                        metrics_repo = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break

    if metrics_repo:
        metrics_repo = os.path.expanduser(metrics_repo)
        os.makedirs(metrics_repo, exist_ok=True)
        return metrics_repo

    # Default: docs/snapshots/ within this repo
    default = os.path.join(workspace, "docs", "snapshots")
    os.makedirs(default, exist_ok=True)
    return default

def main():
    json_mode, raw_mode, compare_file, save = parse_args()
    workspace = resolve_workspace()
    metrics_dir = resolve_metrics_dir(workspace)

    # Call token_census.py
    census_script = os.path.join(workspace, "scripts", "token_census.py")
    result = subprocess.run(["python3", census_script, "--json"], capture_output=True, text=True)
    if result.returncode != 0:
        print("Error running token_census.py", file=sys.stderr)
        sys.exit(1)
        
    census = json.loads(result.stdout)
    
    # Counts
    always_on_rules = sum(1 for r in census["files"] if r["type"] == "always_on_rule")
    conditional_rules = sum(1 for r in census["files"] if r["type"] == "conditional_rule")
    skills_count = sum(1 for r in census["files"] if r["type"] == "skill")
    
    # Extract prong budget caps
    prong_budgets = {}
    staff_review_path = os.path.join(workspace, "skills/staff-review/SKILL.md")
    if os.path.exists(staff_review_path):
        with open(staff_review_path, "r") as f:
            content = f.read()
        
        for line in content.split("\n"):
            match = re.search(r'\|\s*.*?(Spores|Mycelium|Roots|Thorns|Bedrock|Mulch).*?\|\s*\**([0-9,]+\s*tokens).*?\|', line, re.IGNORECASE)
            if match:
                prong_budgets[match.group(1)] = match.group(2).strip()

    # Waste rate (hardcoded from telemetry as per Phase 11 baseline)
    waste_rate_best = "1.1%"
    waste_rate_avg = "18.8%"
    
    # Cells count
    cells_count = 0
    cells_dir = os.path.join(workspace, ".gemini/cells")
    if os.path.exists(cells_dir):
        for root, _, files in os.walk(cells_dir):
            for file in files:
                if file.endswith('.md'):
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
        "metrics_dir": metrics_dir
    }
    
    if raw_mode:
        metrics["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
        
    compare_data = None
    if compare_file and os.path.exists(compare_file):
        with open(compare_file, "r") as f:
            compare_data = json.load(f)

    # Save snapshot to configured metrics directory
    if save:
        ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        save_path = os.path.join(metrics_dir, f"snapshot-{ts}.json")
        save_metrics = dict(metrics)
        save_metrics["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
        save_metrics.pop("metrics_dir", None)  # Don't persist the path itself
        with open(save_path, "w") as f:
            json.dump(save_metrics, f, indent=2)
        print(f"Saved to: {save_path}", file=sys.stderr)

    if json_mode:
        output = dict(metrics)
        output.pop("metrics_dir", None)
        print(json.dumps(output, indent=2))
    else:
        print("=== PRISM AI STEERING: METRICS SNAPSHOT ===")
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

if __name__ == '__main__':
    main()
PYEOF
