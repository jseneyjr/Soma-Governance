"""Cell lifecycle engine — deterministic promotion and demotion decisions.

Reads JSONL evidence data (fitness.jsonl + outcomes.jsonl) and cell metadata
to compute lifecycle transitions:

    vacuole (hypothesis) → wall (proven gate) → genome (universal law)
         ↑                                            ↓
         └──────────── demote (false positives) ───────┘

Promotion criteria (deterministic):
    triggers ≥ 20 AND tp_rate > 0.85 AND age > 30 days

Demotion criteria (deterministic):
    fp_rate > 0.5 OR triggers == 0 for 90+ days
"""
from __future__ import annotations

import collections
import glob
import json
import os
from datetime import datetime, timedelta
from typing import Any

import yaml


# ── Constants ───────────────────────────────────────────────────────────────

MIN_TRIGGERS_FOR_PROMOTION = 20
MIN_TP_RATE_FOR_PROMOTION = 0.85
MIN_AGE_DAYS_FOR_PROMOTION = 30

MAX_FP_RATE_FOR_DEMOTION = 0.5
DORMANT_DAYS_THRESHOLD = 90

# Lifecycle path: vacuole → wall → genome
PROMOTION_PATH = {
    "vacuole": "wall",
    "wall": "genome",
}

DEMOTION_PATH = {
    "genome": "wall",
    "wall": "vacuole",
}


# ── Evidence Loading ────────────────────────────────────────────────────────

def _load_evidence(workspace: str) -> dict[str, dict[str, int]]:
    """Load trigger counts and outcomes from JSONL evidence files.

    Returns:
        Dict mapping cell_id → {triggers: int, tp: int, fp: int}
    """
    evidence: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: {"triggers": 0, "tp": 0, "fp": 0}
    )

    fitness_path = os.path.join(workspace, ".soma", "evidence", "fitness.jsonl")
    if os.path.isfile(fitness_path):
        with open(fitness_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    cell_id = record.get("cell_id", "")
                    if cell_id:
                        evidence[cell_id]["triggers"] += 1
                except (json.JSONDecodeError, KeyError):
                    continue

    outcomes_path = os.path.join(workspace, ".soma", "evidence", "outcomes.jsonl")
    if os.path.isfile(outcomes_path):
        with open(outcomes_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    cell_id = record.get("cell_id", "")
                    outcome = record.get("outcome", "")
                    if cell_id and outcome in ("tp", "fp"):
                        evidence[cell_id][outcome] += 1
                except (json.JSONDecodeError, KeyError):
                    continue

    return dict(evidence)


def _load_cells(workspace: str) -> list[dict[str, Any]]:
    """Load cell metadata from .soma/cells/**/*.md files.

    Returns:
        List of cell metadata dicts with at minimum: id, type, created, source_path.
    """
    cells = []
    cells_root = os.path.join(workspace, ".soma", "cells")
    if not os.path.isdir(cells_root):
        return cells

    for md_path in glob.glob(os.path.join(cells_root, "**", "*.md"), recursive=True):
        if os.path.basename(md_path) == "README.md":
            continue
        try:
            with open(md_path, encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue

        # Parse YAML frontmatter
        if not content.startswith("---"):
            continue
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        try:
            meta = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError:
            continue

        cell_id = meta.get("id", os.path.splitext(os.path.basename(md_path))[0])
        cell_type = meta.get("type", "vacuole")
        created = meta.get("created", "")

        cells.append({
            "id": cell_id,
            "type": cell_type,
            "created": created,
            "source_path": md_path,
            "meta": meta,
        })

    return cells


def _cell_age_days(cell: dict) -> int:
    """Return cell age in days from its 'created' field."""
    created = cell.get("created", "")
    if not created:
        return 0
    try:
        if isinstance(created, str):
            created_dt = datetime.strptime(created, "%Y-%m-%d")
        else:
            created_dt = datetime.combine(created, datetime.min.time())
        return (datetime.now() - created_dt).days
    except (ValueError, TypeError):
        return 0


# ── Promotion ───────────────────────────────────────────────────────────────

def evaluate_promotions(workspace: str) -> list[dict]:
    """Evaluate cells for promotion based on JSONL evidence.

    Returns:
        List of promotion candidate dicts:
        [{cell_id, from_type, to_type, triggers, tp_rate, age_days}]
    """
    evidence = _load_evidence(workspace)
    cells = _load_cells(workspace)
    candidates = []

    for cell in cells:
        cell_id = cell["id"]
        cell_type = cell["type"]

        # Only promotable types
        if cell_type not in PROMOTION_PATH:
            continue

        ev = evidence.get(cell_id, {"triggers": 0, "tp": 0, "fp": 0})
        triggers = ev["triggers"]
        tp = ev["tp"]
        age_days = _cell_age_days(cell)

        # Check criteria
        if triggers < MIN_TRIGGERS_FOR_PROMOTION:
            continue
        tp_rate = tp / triggers if triggers > 0 else 0.0
        if tp_rate < MIN_TP_RATE_FOR_PROMOTION:
            continue
        if age_days < MIN_AGE_DAYS_FOR_PROMOTION:
            continue

        candidates.append({
            "cell_id": cell_id,
            "from_type": cell_type,
            "to_type": PROMOTION_PATH[cell_type],
            "triggers": triggers,
            "tp_rate": round(tp_rate, 4),
            "age_days": age_days,
        })

    return candidates


# ── Demotion ────────────────────────────────────────────────────────────────

def evaluate_demotions(workspace: str) -> list[dict]:
    """Evaluate cells for demotion based on JSONL evidence.

    Returns:
        List of demotion candidate dicts:
        [{cell_id, from_type, to_type, reason, fp_rate, triggers}]
    """
    evidence = _load_evidence(workspace)
    cells = _load_cells(workspace)
    candidates = []

    for cell in cells:
        cell_id = cell["id"]
        cell_type = cell["type"]

        # Only demotable types
        if cell_type not in DEMOTION_PATH:
            continue

        ev = evidence.get(cell_id, {"triggers": 0, "tp": 0, "fp": 0})
        triggers = ev["triggers"]
        tp = ev["tp"]
        fp = ev["fp"]
        age_days = _cell_age_days(cell)

        reason = None

        # Check high false positive rate
        if triggers > 0:
            fp_rate = fp / triggers
            if fp_rate > MAX_FP_RATE_FOR_DEMOTION:
                reason = "high_fp_rate"
        else:
            fp_rate = 0.0

        # Check dormancy (zero triggers for 90+ days)
        if triggers == 0 and age_days >= DORMANT_DAYS_THRESHOLD:
            reason = "dormant"

        if reason is None:
            continue

        candidates.append({
            "cell_id": cell_id,
            "from_type": cell_type,
            "to_type": DEMOTION_PATH[cell_type],
            "reason": reason,
            "fp_rate": round(fp_rate, 4) if triggers > 0 else 0.0,
            "triggers": triggers,
            "age_days": age_days,
        })

    return candidates
