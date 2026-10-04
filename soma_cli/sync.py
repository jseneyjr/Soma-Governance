"""soma sync — reconcile canonical JSONL evidence with cell frontmatter.

Reads .soma/evidence/signals.jsonl, aggregates trigger/tp/fp signals per
cell, and updates cell frontmatter fitness blocks. Idempotent — can be run
repeatedly.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import tempfile
from typing import Optional

import yaml

from soma_cli import resolve_root
from soma_core.evidence import aggregate_signals
from soma_sdk.cells import parse_cell_file


def aggregate_evidence(evidence_dir: str) -> dict[str, dict]:
    """Preserve the established counts-only return shape for callers."""
    return aggregate_signals(evidence_dir).counts


def _fsync_dir(directory: str) -> None:
    """Best-effort directory fsync after a replace on POSIX."""
    if os.name != "posix":
        return
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _atomic_write(path: str, content: str) -> None:
    """Atomically replace path using a durable same-directory temp file."""
    directory = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(
        dir=directory,
        prefix=f".{os.path.basename(path)}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    _fsync_dir(directory)


def sync_frontmatter(
    cells_dir: str,
    counts: dict[str, dict],
    dry_run: bool = False,
    errors: Optional[list[dict]] = None,
) -> list[dict]:
    """Update cell frontmatter from aggregated evidence.

    Existing trigger or outcome values are preserved when the canonical ledger
    has no records for that dimension. Returns only changes successfully made,
    or would-be changes in dry-run mode. Per-cell failures are appended to the
    optional ``errors`` sink without changing the established list return type.
    """
    changes = []
    error_sink = errors if errors is not None else []

    for cell_file in glob.glob(
        os.path.join(cells_dir, "**", "*.md"), recursive=True
    ):
        if os.path.basename(cell_file) == "README.md":
            continue

        cid = os.path.splitext(os.path.basename(cell_file))[0]
        try:
            fm, body = parse_cell_file(cell_file)
            cid = fm.get("id", cid)
            if cid not in counts:
                continue

            evidence = counts[cid]
            fitness = fm.get("fitness", {})
            if not isinstance(fitness, dict):
                fitness = {"score": None, "impact_weight": 1.0}

            old_triggers = fitness.get("triggers", 0)
            old_tp = fitness.get("true_positives", 0)
            old_fp = fitness.get("false_positives", 0)
            old_score = fitness.get("score")
            old_last_trigger = fitness.get("last_trigger_date")

            has_triggers = evidence.get("has_triggers", "triggers" in evidence)
            has_outcomes = evidence.get("has_outcomes")
            has_tp = (
                False if has_outcomes is False else evidence.get("has_tp", "tp" in evidence)
            )
            has_fp = (
                False if has_outcomes is False else evidence.get("has_fp", "fp" in evidence)
            )
            triggers = evidence.get("triggers", 0) if has_triggers else old_triggers
            tp = evidence.get("tp", 0) if has_tp else old_tp
            fp = evidence.get("fp", 0) if has_fp else old_fp

            score = old_score
            if tp + fp > 0:
                score = round(tp / triggers, 4) if triggers > 0 else None
            elif triggers == 0:
                score = None

            last_trigger = old_last_trigger
            if has_triggers and evidence.get("last_trigger") is not None:
                last_trigger = str(evidence["last_trigger"])

            updated = dict(fitness)
            updated["triggers"] = triggers
            updated["true_positives"] = tp
            updated["false_positives"] = fp
            updated["score"] = score
            if last_trigger is not None:
                updated["last_trigger_date"] = last_trigger

            compared_keys = (
                "triggers", "true_positives", "false_positives", "score",
                "last_trigger_date",
            )
            if all(fitness.get(key) == updated.get(key) for key in compared_keys):
                continue

            change = {
                "cell_id": cid,
                "triggers": f"{old_triggers} → {triggers}",
                "tp": f"{old_tp} → {tp}",
                "fp": f"{old_fp} → {fp}",
                "score": score,
            }

            if dry_run:
                changes.append(change)
                continue

            fm["fitness"] = updated
            new_fm = yaml.safe_dump(
                fm,
                sort_keys=False,
                default_flow_style=False,
                allow_unicode=True,
            )
            _atomic_write(cell_file, f"---\n{new_fm}---\n{body}")
            changes.append(change)
        except Exception as exc:  # noqa: BLE001 - continue collecting cell failures
            error_sink.append({
                "cell_id": cid,
                "file": cell_file,
                "error": str(exc),
            })

    return changes


def run_sync(args: argparse.Namespace) -> int:
    """CLI entrypoint for soma sync."""
    root = resolve_root(args)
    evidence_dir = str(root / ".soma" / "evidence")
    cells_dir = str(root / ".soma" / "cells")

    dry_run = getattr(args, "dry_run", False)
    as_json = getattr(args, "json", False)

    aggregation = aggregate_signals(evidence_dir)
    counts = aggregation.counts
    errors: list[dict] = list(aggregation.errors)
    if not counts and not errors:
        if as_json:
            print(json.dumps({
                "status": "ok", "changes": [], "errors": [],
                "dry_run": dry_run,
            }, indent=2))
        else:
            print("No evidence found in .soma/evidence/")
        return 0

    if errors:
        if as_json:
            print(json.dumps({
                "status": "error", "changes": [], "errors": errors,
                "dry_run": dry_run,
            }, indent=2))
        else:
            for error in errors:
                subject = error.get("file", "evidence")
                detail = error.get("error", "unknown error")
                if error.get("line") is not None:
                    detail = f"line {error['line']}: {detail}"
                print(f"  ! {subject}: {detail}", file=sys.stderr)
            print(
                f"Sync failed for {len(errors)} evidence rows.",
                file=sys.stderr,
            )
        return 1

    changes = sync_frontmatter(
        cells_dir, counts, dry_run=dry_run, errors=errors
    )

    if as_json:
        print(json.dumps({
            "status": "error" if errors else "ok",
            "changes": changes,
            "errors": errors,
            "dry_run": dry_run,
        }, indent=2))
        return 1 if errors else 0

    for error in errors:
        subject = error.get("cell_id") or error.get("file", "evidence")
        detail = error.get("error") or error.get("message", "unknown error")
        if error.get("line") is not None:
            detail = f"line {error['line']}: {detail}"
        print(f"  ! {subject}: {detail}", file=sys.stderr)

    verb = "Would update" if dry_run else "Updated"
    if not changes and not errors:
        print("All cells already in sync with evidence.")
        return 0

    for change in changes:
        print(
            f"  ✓ {change['cell_id']}: triggers {change['triggers']}, "
            f"tp {change['tp']}, fp {change['fp']} → score={change['score']}"
        )

    if changes:
        print(f"\n{verb} {len(changes)} cells.")
    if errors:
        print(f"Sync failed for {len(errors)} cells.", file=sys.stderr)
        return 1
    return 0
