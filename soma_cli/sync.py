"""soma sync — reconcile JSONL evidence with cell frontmatter.

Reads .soma/evidence/fitness.jsonl and outcomes.jsonl, aggregates
trigger/tp/fp counts per cell, and updates cell frontmatter fitness
blocks. Idempotent — can be run repeatedly.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from datetime import datetime, timezone

import yaml

from soma_cli import resolve_root
from soma_sdk.cells import parse_cell_file


def aggregate_evidence(evidence_dir: str) -> dict[str, dict]:
    """Read JSONL files and aggregate counts per cell_id.

    Returns:
        Dict mapping cell_id → {triggers: int, tp: int, fp: int,
        last_trigger: str | None}
    """
    counts: dict[str, dict] = {}

    # Read fitness.jsonl — trigger events
    fitness_path = os.path.join(evidence_dir, "fitness.jsonl")
    if os.path.isfile(fitness_path):
        with open(fitness_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    if not isinstance(record, dict):
                        continue
                    cid = record.get("cell_id", "")
                    if not cid:
                        continue
                    entry = counts.setdefault(cid, {
                        "triggers": 0, "tp": 0, "fp": 0,
                        "last_trigger": None,
                    })
                    entry["triggers"] += 1
                    ts = record.get("triggered_at")
                    if ts and (entry["last_trigger"] is None
                               or ts > entry["last_trigger"]):
                        entry["last_trigger"] = ts
                except (json.JSONDecodeError, ValueError):
                    continue

    # Read outcomes.jsonl — tp/fp classification
    outcomes_path = os.path.join(evidence_dir, "outcomes.jsonl")
    if os.path.isfile(outcomes_path):
        with open(outcomes_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    if not isinstance(record, dict):
                        continue
                    cid = record.get("cell_id", "")
                    if not cid:
                        continue
                    entry = counts.setdefault(cid, {
                        "triggers": 0, "tp": 0, "fp": 0,
                        "last_trigger": None,
                    })
                    outcome = record.get("outcome", "")
                    if outcome in ("tp", "success"):
                        entry["tp"] += 1
                    elif outcome in ("fp", "failure"):
                        entry["fp"] += 1
                except (json.JSONDecodeError, ValueError):
                    continue

    return counts


def sync_frontmatter(
    cells_dir: str,
    counts: dict[str, dict],
    dry_run: bool = False,
) -> list[dict]:
    """Update cell frontmatter from aggregated evidence.

    Returns list of changes made (or would-be-made in dry_run).
    """
    changes = []

    for cell_file in glob.glob(
        os.path.join(cells_dir, "**", "*.md"), recursive=True
    ):
        if os.path.basename(cell_file) == "README.md":
            continue

        try:
            fm, body = parse_cell_file(cell_file)
            cid = fm.get(
                "id", os.path.splitext(os.path.basename(cell_file))[0]
            )

            if cid not in counts:
                continue

            evidence = counts[cid]
            t = evidence["triggers"]
            tp = evidence["tp"]
            fp = evidence["fp"]

            # Read current frontmatter fitness
            fitness = fm.get("fitness", {})
            if not isinstance(fitness, dict):
                fitness = {"score": None, "impact_weight": 1.0}

            old_triggers = fitness.get("triggers", 0)
            old_tp = fitness.get("true_positives", 0)
            old_fp = fitness.get("false_positives", 0)

            # Skip if already in sync
            if old_triggers == t and old_tp == tp and old_fp == fp:
                continue

            # Update
            fitness["triggers"] = t
            fitness["true_positives"] = tp
            fitness["false_positives"] = fp
            # Only update score if there's actual outcome data.
            # Cells with triggers but no tp/fp should keep existing score,
            # not be clobbered to 0.0 (Bug 4 fix).
            if tp + fp > 0:
                fitness["score"] = round(tp / t, 4) if t > 0 else None
            elif t == 0:
                fitness["score"] = None
            if evidence["last_trigger"]:
                fitness["last_trigger_date"] = (
                    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                )
            fm["fitness"] = fitness

            change = {
                "cell_id": cid,
                "triggers": f"{old_triggers} → {t}",
                "tp": f"{old_tp} → {tp}",
                "fp": f"{old_fp} → {fp}",
                "score": fitness["score"],
            }
            changes.append(change)

            if not dry_run:
                new_fm = yaml.dump(
                    fm, sort_keys=False, default_flow_style=False,
                    allow_unicode=True,
                )
                new_content = f"---\n{new_fm}---\n{body}"

                with open(cell_file, "w", encoding="utf-8") as f:
                    f.write(new_content)

        except Exception:  # noqa: BLE001
            continue

    return changes


def run_sync(args: argparse.Namespace) -> int:
    """CLI entrypoint for soma sync."""
    root = resolve_root(args)
    evidence_dir = str(root / ".soma" / "evidence")
    cells_dir = str(root / ".soma" / "cells")

    dry_run = getattr(args, "dry_run", False)
    as_json = getattr(args, "json", False)

    counts = aggregate_evidence(evidence_dir)
    if not counts:
        print("No evidence found in .soma/evidence/")
        return 0

    changes = sync_frontmatter(cells_dir, counts, dry_run=dry_run)

    if as_json:
        print(json.dumps({"changes": changes, "dry_run": dry_run}, indent=2))
        return 0

    verb = "Would update" if dry_run else "Updated"
    if not changes:
        print("All cells already in sync with evidence.")
        return 0

    for c in changes:
        print(f"  ✓ {c['cell_id']}: triggers {c['triggers']}, "
              f"tp {c['tp']}, fp {c['fp']} → score={c['score']}")

    print(f"\n{verb} {len(changes)} cells.")
    return 0
