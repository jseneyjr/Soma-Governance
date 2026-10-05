#!/usr/bin/env python3
"""cell_signal.py: External Fitness Signal API for Soma immune cells.

Allows external systems and CLI to feed fitness signals back to cells.

Usage:
    python enzymes/cell_signal.py <cell_id> <tp|fp|fn> [--metric key=value] [--stress]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    import json as yaml  # fallback


def resolve_workspace() -> Path:
    """Walk up from CWD to find project root with .soma/cells/."""
    soma_root = os.environ.get("SOMA_ROOT")
    if soma_root and os.path.isdir(soma_root):
        return Path(soma_root).resolve()
    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if "vendor" in candidate.parts:
            continue
        if (candidate / ".soma" / "cells").is_dir():
            return candidate
    return cwd


def send_signal(
    cell_id: str,
    outcome: str,
    metric_key: Optional[str] = None,
    metric_val: Optional[str] = None,
    stress: bool = False,
    workspace: Path | None = None,
) -> int:
    outcome = outcome.lower()
    if outcome not in ("tp", "fp", "fn"):
        print("Error: Outcome must be tp, fp, or fn.", file=sys.stderr)
        return 2

    repo_root = workspace or resolve_workspace()
    cells_dir = repo_root / ".soma" / "cells"
    if not cells_dir.is_dir():
        print(f"Error: Directory {cells_dir} not found.", file=sys.stderr)
        return 1

    # Find matching cell files
    matches = list(cells_dir.rglob(f"*{cell_id}*.md"))
    if not matches:
        print(f"Error: No cells found matching '{cell_id}' in {cells_dir}.", file=sys.stderr)
        return 1
    if len(matches) > 1:
        print(f"Error: Multiple cells matched '{cell_id}':", file=sys.stderr)
        for m in matches:
            print(f"  - {m.name}", file=sys.stderr)
        return 1

    target_cell = matches[0]
    cell_basename = target_cell.stem
    metrics_file = repo_root / ".soma" / "metrics" / f"{cell_basename}.jsonl"

    try:
        content = target_cell.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {target_cell}: {e}", file=sys.stderr)
        return 1

    if not content.startswith("---"):
        print(f"Error: {target_cell} lacks YAML frontmatter", file=sys.stderr)
        return 1

    end_idx = content.find("---", 3)
    if end_idx == -1:
        print(f"Error: {target_cell} has malformed YAML frontmatter", file=sys.stderr)
        return 1

    frontmatter_str = content[3:end_idx].strip()
    body_str = content[end_idx + 3:]

    try:
        metadata = yaml.safe_load(frontmatter_str) or {}
    except Exception as e:
        print(f"Error parsing YAML: {e}", file=sys.stderr)
        return 1

    if "fitness" not in metadata or not isinstance(metadata["fitness"], dict):
        metadata["fitness"] = {}

    fitness = metadata["fitness"]
    triggers = fitness.get("triggers", 0)
    tp = fitness.get("true_positives", 0)
    fp = fitness.get("false_positives", 0)

    old_score = (tp / triggers) if triggers > 0 else 0.0

    if outcome == "tp":
        triggers += 1
        tp += 1
    elif outcome == "fp":
        triggers += 1
        fp += 1
    elif outcome == "fn":
        triggers += 1

    new_score = (tp / triggers) if triggers > 0 else 0.0
    fitness["triggers"] = triggers
    fitness["true_positives"] = tp
    fitness["false_positives"] = fp
    fitness["score"] = new_score
    fitness["last_trigger_date"] = datetime.now(timezone.utc).isoformat() + "Z"

    if stress:
        fitness["stress_survived"] = fitness.get("stress_survived", 0) + 1

    metadata["fitness"] = fitness

    try:
        new_frontmatter = yaml.dump(metadata, default_flow_style=False, sort_keys=False)
        clean_body = body_str[1:] if body_str.startswith("\n") else body_str
        new_content = f"---\n{new_frontmatter}---\n{clean_body}"
        target_cell.write_text(new_content, encoding="utf-8")
    except Exception as e:
        print(f"Error writing to {target_cell}: {e}", file=sys.stderr)
        return 1

    print(
        f"Cell {target_cell.name}: {outcome} recorded. Score: {old_score:.2f} -> {new_score:.2f} (triggers: {triggers})"
    )

    if metric_key:
        try:
            metrics_file.parent.mkdir(parents=True, exist_ok=True)
            metric_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "outcome": outcome,
                metric_key: metric_val,
            }
            with open(metrics_file, "a", encoding="utf-8") as mf:
                mf.write(json.dumps(metric_entry) + "\n")
        except Exception as e:
            print(f"Warning: Failed to write to metrics file {metrics_file}: {e}", file=sys.stderr)

    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) < 2 or args[0] in ("-h", "--help"):
        print("Usage: cell_signal.py <cell_id> <tp|fp|fn> [--metric key=value] [--stress]")
        return 2

    cell_id = args[0]
    outcome = args[1]
    metric_key = None
    metric_val = None
    stress = False

    i = 2
    while i < len(args):
        arg = args[i]
        if arg == "--metric" and i + 1 < len(args):
            m = args[i + 1]
            if "=" in m:
                metric_key, metric_val = m.split("=", 1)
            else:
                metric_key = m
                metric_val = ""
            i += 2
        elif arg == "--stress":
            stress = True
            i += 1
        else:
            i += 1

    return send_signal(
        cell_id=cell_id,
        outcome=outcome,
        metric_key=metric_key,
        metric_val=metric_val,
        stress=stress,
    )


if __name__ == "__main__":
    sys.exit(main())
