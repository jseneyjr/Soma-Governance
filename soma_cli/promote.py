"""soma promote — evaluate and display cell promotion candidates."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


from soma_core.lifecycle import (
    PROMOTION_PATH,
    TYPE_TO_DIR,
    find_cell_file,
    promote_cell,
)


def _find_cell(cells_dir: Path, genome_dir: Path | None = None, cell_id: str = "") -> tuple[Path | None, str | None]:
    """Find a cell file by ID across vacuoles/, walls/, and genome/."""
    workspace = cells_dir.parent.parent
    return find_cell_file(workspace, cell_id)


def _force_promote(project_root: Path, cell_id: str, dry_run: bool, use_json: bool) -> int:
    """Force-promote a specific cell, bypassing evidence thresholds."""
    res = promote_cell(project_root, cell_id, force=True, dry_run=dry_run)
    status = res.get("status")

    if status == "not_found":
        msg = f"Cell '{cell_id}' not found in {project_root / '.soma' / 'cells'}"
        if use_json:
            print(json.dumps({"error": msg}))
        else:
            print(f"  ❌ {msg}")
        return 1

    if status == "already_terminal":
        msg = f"Cell '{cell_id}' is already at terminal promotion level ('{res.get('current_type')}')"
        if use_json:
            print(json.dumps({"info": msg}))
        else:
            print(f"  ℹ️  {msg}")
        return 0

    if status == "target_exists":
        msg = res.get("message", "Target already exists")
        if use_json:
            print(json.dumps({"error": msg}))
        else:
            print(msg)
        return 1

    if status == "dry_run":
        if use_json:
            print(json.dumps({"action": "promote", "cell_id": cell_id,
                             "from": res["from_type"], "to": res["to_type"], "dry_run": True}))
        else:
            print(f"  🧬 Would promote: {cell_id}: {res['from_type']} → {res['to_type']}")
            print(f"     {res['source_path']} → {res['target_path']}")
        return 0

    if status == "promoted":
        if use_json:
            print(json.dumps({"action": "promote", "cell_id": cell_id,
                             "from": res["from_type"], "to": res["to_type"]}))
        else:
            print(f"  ✅ Promoted: {cell_id}: {res['from_type']} → {res['to_type']}")
        return 0

    msg = res.get("message", "Promotion failed")
    if use_json:
        print(json.dumps({"error": msg}))
    else:
        print(f"  ❌ {msg}")
    return 1


def run_promote(args: argparse.Namespace) -> int:
    """Evaluate promotion candidates and display results.
    
    Returns 0 always (dry-run is advisory).
    """
    project_root = Path(getattr(args, "_project_root", Path.cwd()))
    use_json = getattr(args, "json", False)
    dry_run = getattr(args, "dry_run", False)
    force = getattr(args, "force", False)
    cell_id = getattr(args, "cell", None)

    if getattr(args, 'cell', None) and not getattr(args, 'force', False):
        print("Warning: --cell requires --force; running normal evaluation", file=sys.stderr)

    if force:
        if not cell_id:
            msg = "--force requires --cell <cell-id>"
            if use_json:
                print(json.dumps({"error": msg}))
            else:
                print(f"  ❌ {msg}")
            return 1
        return _force_promote(project_root, cell_id, dry_run, use_json)

    from immune_system.verification.lifecycle import evaluate_promotions

    candidates = evaluate_promotions(str(project_root))
    
    if use_json:
        print(json.dumps({"candidates": candidates}, indent=2, default=str))
    else:
        if not candidates:
            print("  No promotion candidates found.")
        else:
            print(f"  🧬 Promotion Candidates ({len(candidates)}):")
            print()
            for c in candidates:
                print(f"    {c['cell_id']}: {c['from_type']} → {c['to_type']}")
                print(f"      triggers={c['triggers']} tp_rate={c['tp_rate']:.0%} age={c['age_days']}d")
            print()
    
    return 0

