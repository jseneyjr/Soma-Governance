"""Soma CLI — Quarantine management subcommand.

Provides pure Python inspection and lifecycle management for quarantined
corrupted files:
    soma quarantine list [--json]
    soma quarantine inspect <file>
    soma quarantine prune [--older-than-days N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from soma_core.quarantine import (
    list_quarantine,
    inspect_quarantined_file,
    prune_quarantine,
)


def resolve_workspace() -> Optional[Path]:
    """Find current project root with .soma/ directory."""
    soma_root = os.environ.get("SOMA_WORKSPACE") or os.environ.get("SOMA_ROOT")
    if soma_root and os.path.isdir(soma_root):
        return Path(soma_root).resolve()
    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if "vendor" in candidate.parts:
            continue
        if (candidate / ".soma").is_dir():
            return candidate
    return cwd


def run_quarantine(args: argparse.Namespace) -> int:
    """Entry point for soma quarantine commands."""
    ws = resolve_workspace()
    action = getattr(args, "quarantine_action", None) or "list"

    if action == "list":
        items = list_quarantine(workspace=ws)
        if getattr(args, "json", False):
            # Strip private internal keys
            clean_items = [{k: v for k, v in item.items() if not k.startswith("_")} for item in items]
            print(json.dumps(clean_items, indent=2))
            return 0

        if not items:
            print("No quarantined files found. System state is healthy.")
            return 0

        print(f"Quarantined Files ({len(items)} found):")
        print("-" * 80)
        for item in items:
            print(f"  File:      {item['filename']}")
            print(f"  Timestamp: {item['timestamp']}")
            print(f"  Size:      {item['size_bytes']} bytes")
            print(f"  Reason:    {item['reason']}")
            if item.get("original_path"):
                print(f"  Original:  {item['original_path']}")
            print("-" * 80)
        return 0

    elif action == "inspect":
        target = getattr(args, "target", None)
        if not target:
            print("Error: Target filename or path is required for inspect.", file=sys.stderr)
            return 1

        detail = inspect_quarantined_file(target, workspace=ws)
        if not detail:
            print(f"Error: Quarantined file '{target}' not found.", file=sys.stderr)
            return 1

        if getattr(args, "json", False):
            clean = {k: v for k, v in detail.items() if not k.startswith("_")}
            print(json.dumps(clean, indent=2))
            return 0

        print(f"Quarantine Detail: {detail['filename']}")
        print(f"  Path:      {detail['path']}")
        print(f"  Timestamp: {detail['timestamp']}")
        print(f"  Size:      {detail['size_bytes']} bytes")
        print(f"  Reason:    {detail['reason']}")
        if detail.get("original_path"):
            print(f"  Original:  {detail['original_path']}")
        print("\nContent Preview (first 2000 chars):")
        print("-" * 60)
        print(detail.get("preview", ""))
        print("-" * 60)
        return 0

    elif action == "prune":
        older_than_days = getattr(args, "older_than_days", 30)
        pruned_count = prune_quarantine(older_than_days=older_than_days, workspace=ws)
        print(f"Pruned {pruned_count} quarantined file(s) older than {older_than_days} day(s).")
        return 0

    else:
        print(f"Error: Unknown quarantine action '{action}'.", file=sys.stderr)
        return 1
