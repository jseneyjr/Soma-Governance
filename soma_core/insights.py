"""soma_core.insights — Human insight capture, correlation, and candidate synthesis.

Consolidates:
- Human insight capture & coverage correlation (formerly enzymes/insight_capture.py)
- Insight clustering and cell candidate synthesis (formerly enzymes/insight_correlator.py)
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import sys
from typing import Any, Dict, List, Optional

from soma_core.workspace import resolve_workspace
from soma_core.defects import find_covering_cells, load_cells
from soma_core.frontmatter import parse_frontmatter, parse_yaml_subset, dump_frontmatter
from soma_core.evidence import aggregate_signals


def _load_signal_weight(workspace: str) -> float:
    """Load insight_signal_weight from .soma/config.yaml, defaulting to 0.5."""
    default = 0.5
    config_path = os.path.join(workspace, ".soma", "config.yaml")
    if not os.path.exists(config_path):
        return default
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        if content.startswith('\ufeff'):
            content = content[1:]
        cfg = parse_frontmatter(content) if content.startswith("---") else parse_yaml_subset(content)
        if isinstance(cfg, dict):
            return float(cfg.get("insight_signal_weight", default))
    except Exception:
        pass
    return default


def _parse_timestamp(ts_str: str) -> datetime:
    """Parse an ISO-8601 timestamp string to a timezone-aware datetime."""
    if ts_str.endswith("Z"):
        ts_str = ts_str[:-1] + "+00:00"
    return datetime.fromisoformat(ts_str)


def capture_insight(
    workspace: str,
    insight: str,
    context_files: list,
    source_conversation: Optional[str] = None,
    category: Optional[str] = None,
) -> dict:
    """Capture a human insight and persist it to JSONL."""
    if not isinstance(context_files, list):
        raise ValueError("context_files must be a list, not " + type(context_files).__name__)
    if not context_files:
        raise ValueError("context_files must not be empty")
    if not insight or not insight.strip():
        raise ValueError("insight must not be empty")

    cells_dir = os.path.join(workspace, ".soma", "cells")
    if os.path.isdir(cells_dir):
        cells = load_cells(cells_dir)
    else:
        cells = []

    covering = find_covering_cells(cells, context_files)
    covering_cell_names = [c["cell"]["_name"] for c in covering]
    was_covered = len(covering_cell_names) > 0

    signal_weight = _load_signal_weight(workspace)

    record = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "insight": insight,
        "context_files": context_files,
        "source_conversation": source_conversation,
        "category": category,
        "covering_cells": covering_cell_names,
        "was_covered": was_covered,
        "signal_weight": signal_weight,
    }

    jsonl_path = os.path.join(workspace, ".soma", "human_insights.jsonl")
    os.makedirs(os.path.dirname(jsonl_path), exist_ok=True)
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return record


def cluster_insights(
    workspace: str,
    min_cluster_size: int = 3,
    window_days: int = 30,
) -> list[dict]:
    """Read human insights and cluster by category within rolling window."""
    jsonl_path = os.path.join(workspace, ".soma", "human_insights.jsonl")
    if not os.path.isfile(jsonl_path):
        return []

    records: list[dict] = []
    with open(jsonl_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not records:
        return []

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)

    recent: list[dict] = []
    for rec in records:
        ts_str = rec.get("timestamp")
        if not ts_str:
            continue
        try:
            ts = _parse_timestamp(ts_str)
        except (ValueError, TypeError):
            continue
        if ts >= cutoff:
            recent.append(rec)

    if not recent:
        return []

    groups: dict[str, list[dict]] = {}
    for rec in recent:
        cat = rec.get("category") or "uncategorized"
        groups.setdefault(cat, []).append(rec)

    clusters: list[dict] = []
    for category, group in sorted(groups.items()):
        if len(group) < min_cluster_size:
            continue

        common_files: list[str] = []
        seen_files: set[str] = set()
        for rec in group:
            for f in rec.get("context_files", []):
                if f not in seen_files:
                    seen_files.add(f)
                    common_files.append(f)

        insight_count = len(group)
        confidence = round(insight_count / (insight_count + 2), 4)

        slug = category.replace(" ", "-").lower()
        file_hash = hashlib.sha256(
            "-".join(sorted(seen_files)).encode()
        ).hexdigest()[:8]
        pattern_id = f"{slug}-{file_hash}"

        clusters.append({
            "pattern_id": pattern_id,
            "insight_count": insight_count,
            "common_files": common_files,
            "common_category": category,
            "confidence": confidence,
        })

    return clusters


def generate_cell_candidates(
    clusters: list[dict],
    workspace: str,
) -> list[dict]:
    """Produce governance-cell candidate dicts from insight clusters."""
    if not clusters:
        return []

    candidates: list[dict] = []
    for cluster in clusters:
        category = cluster.get("common_category", "unknown")
        files = cluster.get("common_files", [])
        files_str = ", ".join(files) if files else "project-wide"

        hypothesis = f"Human attention pattern detected: {category} in {files_str}"

        candidates.append({
            "hypothesis": hypothesis,
            "target_paths": list(files),
            "origin": "human_insight",
            "type": "vacuole",
            "enforcement": "advisory",
        })

    return candidates
 
 
def create_cell_from_insight_cluster(cluster: dict, workspace: str) -> str:
    """Create a governance cell from an insight cluster."""
    import re
 
    category = cluster.get("common_category") or "unknown"
    files = cluster.get("common_files", [])
    confidence = cluster.get("confidence", 0.5)
    files_str = ", ".join(files) if files else "project-wide"
 
    hypothesis = f"Human attention pattern detected: {category} in {files_str}"
 
    slug = re.sub(r"[^a-z0-9]+", "-", category.lower())[:50].strip("-") or "unknown"
    cell_id = f"vacuole-{slug}"
 
    frontmatter = {
        "id": cell_id,
        "type": "vacuole",
        "domain": "correctness",
        "hypothesis": hypothesis,
        "prediction": f"Recurring {category} issues will continue if unaddressed",
        "falsification": f"No {category} insights observed for 60 days",
        "target_paths": list(files),
        "minimum_mode": "breeze",
        "origin": "human_insight",
        "tags": ["auto-generated", "insight-cluster", category],
    }
 
    fm_text = dump_frontmatter(frontmatter)
 
    body = (
        f"This vacuole was auto-generated from a cluster of human insights "
        f"about **{category}** (confidence {confidence:.2f}).\n"
    )
    cell_content = f"---\n{fm_text}---\n\n{body}"
 
    filename = f"vacuole-{slug}.md"
    target_dir = os.path.join(workspace, ".soma", "cells", "vacuoles")
    os.makedirs(target_dir, exist_ok=True)
 
    filepath = os.path.join(target_dir, filename)
    if os.path.isfile(filepath):
        evidence_dir = os.path.join(workspace, ".soma", "evidence")
        signal_counts = aggregate_signals(evidence_dir).counts
        c_id = frontmatter.get("id", "")
        if signal_counts.get(c_id, {}).get("has_triggers", False):
            return filepath
 
    try:
        os.unlink(filepath)
    except OSError:
        pass
    fd = os.open(filepath, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with open(fd, "w", encoding="utf-8") as f:
        f.write(cell_content)
 
    return filepath
 
 
def cli_insight_capture(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Capture human insight")
    parser.add_argument("--insight", required=True, help="Insight description")
    parser.add_argument("--files", nargs="+", required=True, help="Context files")
    parser.add_argument("--conversation", default=None, help="Source conversation ID")
    parser.add_argument("--category", default=None, help="Insight category")
    parser.add_argument("--workspace", default=None, help="Workspace root")

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    workspace = args.workspace or resolve_workspace()

    record = capture_insight(
        workspace=workspace,
        insight=args.insight,
        context_files=args.files,
        source_conversation=args.conversation,
        category=args.category,
    )
    print(f"Captured insight: {record['insight'][:60]} (covered: {record['was_covered']})")
    return 0


def cli_insight_correlator(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Cluster human insights into cell candidates")
    parser.add_argument("--workspace", default=None, help="Workspace root")
    parser.add_argument("--min-cluster-size", type=int, default=3, help="Min cluster size")
    parser.add_argument("--window-days", type=int, default=30, help="Rolling window days")
    parser.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    workspace = args.workspace or resolve_workspace()

    clusters = cluster_insights(
        workspace=workspace,
        min_cluster_size=args.min_cluster_size,
        window_days=args.window_days,
    )
    candidates = generate_cell_candidates(clusters, workspace)

    if args.json:
        print(json.dumps({"clusters": clusters, "candidates": candidates}, indent=2))
    else:
        print(f"Clustered {len(clusters)} insight patterns ({len(candidates)} candidates):")
        for c in candidates:
            print(f"  • {c['hypothesis']}")

    return 0


__all__ = [
    "capture_insight",
    "cluster_insights",
    "generate_cell_candidates",
    "create_cell_from_insight_cluster",
    "cli_insight_capture",
    "cli_insight_correlator",
]
