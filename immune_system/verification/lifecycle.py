"""Cell lifecycle engine — deterministic promotion and demotion decisions.

Uses canonical signal evidence and cell metadata to compute lifecycle
transitions:

    vacuole (hypothesis) → wall (proven gate) → genome (universal law)
         ↑                                            ↓
         └──────────── demote (false positives) ───────┘

Promotion criteria (deterministic):
    triggers ≥ 20 AND tp_rate ≥ 0.85 AND age ≥ 30 days

Demotion criteria (deterministic):
    fp_rate > 0.5 (min 5 triggers) OR last trigger ≥ 90 days ago
"""
from __future__ import annotations

import glob
import os
from datetime import datetime, timezone
from typing import Any, Optional

import yaml

from soma_core.evidence import aggregate_signals


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

def _naive_utc(timestamp: Any) -> Optional[datetime]:
    """Parse a canonical timestamp and normalize it to naive UTC."""
    if not isinstance(timestamp, str) or not timestamp:
        return None
    normalized = timestamp[:-1] + "+00:00" if timestamp.endswith("Z") else timestamp
    try:
        parsed = datetime.fromisoformat(normalized)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _load_evidence(workspace: str) -> dict[str, dict[str, Any]]:
    """Load lifecycle dimensions from the canonical signal ledger."""
    evidence_dir = os.path.join(workspace, ".soma", "evidence")
    aggregation = aggregate_signals(evidence_dir)
    return {
        cell_id: {
            "triggers": counts["triggers"],
            "tp": counts["tp"],
            "fp": counts["fp"],
            "last_trigger_ts": _naive_utc(counts["last_trigger"]),
            "has_triggers": counts["has_triggers"],
        }
        for cell_id, counts in aggregation.counts.items()
    }


def _load_cells(workspace: str) -> list[dict[str, Any]]:
    """Load cell metadata from .soma/cells/**/*.md and genome/**/*.md files.

    Returns:
        List of cell metadata dicts with at minimum: id, type, created, source_path.
    """
    cells = []
    scan_roots = [
        os.path.join(workspace, ".soma", "cells"),
        os.path.join(workspace, "genome"),
    ]

    for cells_root in scan_roots:
        if not os.path.isdir(cells_root):
            continue

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
        return (datetime.now(timezone.utc).replace(tzinfo=None) - created_dt).days
    except (ValueError, TypeError):
        return 0


# ── Promotion ───────────────────────────────────────────────────────────────

def evaluate_promotions(workspace: str) -> list[dict]:
    """Evaluate cells for promotion based on canonical signal evidence.

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

        ev = evidence.get(cell_id, {
            "triggers": 0, "tp": 0, "fp": 0,
            "last_trigger_ts": None, "has_triggers": True,
        })
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
    """Evaluate cells for demotion based on canonical signal evidence.

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

        ev = evidence.get(cell_id, {
            "triggers": 0, "tp": 0, "fp": 0,
            "last_trigger_ts": None, "has_triggers": True,
        })
        triggers = ev["triggers"]
        tp = ev["tp"]
        fp = ev["fp"]
        age_days = _cell_age_days(cell)

        reason = None

        # Check high false positive rate (minimum 5 triggers required)
        if triggers >= 5:
            fp_rate = fp / triggers
            if fp_rate > MAX_FP_RATE_FOR_DEMOTION:
                reason = "high_fp_rate"
        else:
            fp_rate = 0.0

        # Check dormancy based on time since last trigger
        last_trigger_ts = ev.get("last_trigger_ts")
        if last_trigger_ts is not None:
            last_trigger_age = (datetime.now(timezone.utc).replace(tzinfo=None) - last_trigger_ts).days
        else:
            # With no evidence at all, preserve the established cell-age proxy.
            # Outcome-only evidence leaves the trigger dimension unknown.
            last_trigger_age = (
                age_days
                if triggers == 0 and ev.get("has_triggers", True)
                else 0
            )

        if reason is None and last_trigger_age >= DORMANT_DAYS_THRESHOLD:
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
