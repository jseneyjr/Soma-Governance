#!/usr/bin/env python3
"""cell_selection.py: Selection pressure engine for Soma immune cells.

Evaluates fitness and archives extinct or apoptotic cells.

Usage:
    python enzymes/cell_selection.py [--execute]
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import sys
from datetime import timezone
from pathlib import Path


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


def run_cell_selection(workspace: Path | str | None = None, execute: bool = False) -> int:
    repo_root = Path(workspace).resolve() if workspace else resolve_workspace()
    cells_dir = repo_root / ".soma" / "cells"
    archive_dir = cells_dir / ".archive"
    evidence_dir = repo_root / ".soma" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    fitness_log = evidence_dir / "lifecycle.jsonl"

    if not cells_dir.exists():
        print("No cells directory found.")
        return 0

    print(f"Running cell selection (execute={execute})...")

    if execute:
        archive_dir.mkdir(parents=True, exist_ok=True)

    for root_str, dirs, files in os.walk(cells_dir):
        if ".archive" in root_str:
            continue
        for f in files:
            if not f.endswith(".md") or f == "README.md":
                continue
            fpath = Path(root_str) / f

            try:
                content = fpath.read_text(encoding="utf-8")
            except Exception:
                continue

            fm_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
            if not fm_match:
                continue
            fm = fm_match.group(1)

            def get_val(key: str, default: float = 0.0) -> float:
                m = re.search(rf"{key}:\s*(\S+)", fm)
                if m and m.group(1) != "null":
                    try:
                        return float(m.group(1))
                    except ValueError:
                        return default
                return default

            triggers = get_val("triggers", 0.0)
            tp = get_val("true_positives", 0.0)
            fp = get_val("false_positives", 0.0)
            type_match = re.search(r"type:\s*([^\s\n]+)", fm)
            cell_type = type_match.group(1) if type_match else ""
            dormant = "dormant_since" in fm

            if triggers == 0:
                category = "DORMANT"
                score = 0.0
            else:
                score = tp / triggers
                if fp > 0 and tp > 0 and fp > 2 * tp:
                    if cell_type == "wall":
                        category = "APOPTOSIS_WARNING"
                    else:
                        category = "APOPTOSIS"
                elif score > 0.7:
                    category = "SURVIVE"
                elif score >= 0.3:
                    category = "ADAPT"
                else:
                    category = "EXTINCT"

            print(f"[{category}] {f} (Score: {score:.2f})")

            if execute:
                action = None
                if category in ("EXTINCT", "APOPTOSIS"):
                    if category == "APOPTOSIS":
                        last_gasp_dir = cells_dir / ".last_gasp_queue"
                        last_gasp_dir.mkdir(parents=True, exist_ok=True)
                        dest = last_gasp_dir / f
                        shutil.move(str(fpath), str(dest))
                        action = "last_gasp_requested"
                    else:
                        dest = archive_dir / f
                        shutil.move(str(fpath), str(dest))
                        action = "moved_to_archive"

                    if action == "moved_to_archive":
                        spores_file = cells_dir / ".spores.jsonl"

                        def get_str(key: str) -> str:
                            m = re.search(rf"{key}:\s*(.+?)$", fm, re.MULTILINE)
                            return m.group(1).strip().strip("\"'") if m else ""

                        name_val = get_str("name") or f.replace(".md", "")
                        type_val = get_str("type")
                        hypo_val = get_str("hypothesis")

                        tp_list: list[str] = []
                        tp_m = re.search(r"target_paths:\s*\[(.*?)\]", fm, re.DOTALL)
                        if tp_m:
                            tp_list = [p.strip().strip("\"'") for p in tp_m.group(1).split(",") if p.strip()]

                        spore = {
                            "name": name_val,
                            "type": type_val,
                            "hypothesis": hypo_val,
                            "target_paths": tp_list,
                            "peak_fitness": score,
                            "extinction_date": datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                            "reactivation_patterns": tp_list,
                        }
                        with open(spores_file, "a", encoding="utf-8") as sf:
                            sf.write(json.dumps(spore) + "\n")

                elif category == "DORMANT" and not dormant:
                    timestamp = datetime.datetime.now(timezone.utc).isoformat() + "Z"
                    new_content = content.replace("fitness:", f"dormant_since: {timestamp}\nfitness:")
                    fpath.write_text(new_content, encoding="utf-8")
                    action = "marked_dormant"

                if action:
                    with open(fitness_log, "a", encoding="utf-8") as log:
                        log.write(
                            json.dumps({
                                "timestamp": datetime.datetime.now(timezone.utc).isoformat() + "Z",
                                "cell": f,
                                "action": action,
                            })
                            + "\n"
                        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Selection pressure engine for Soma immune cells")
    parser.add_argument("--execute", action="store_true", default=False, help="Execute selection decisions")
    parser.add_argument("--workspace", type=str, default="", help="Path to workspace root")
    args = parser.parse_args(argv)

    ws = Path(args.workspace) if args.workspace else None
    return run_cell_selection(workspace=ws, execute=args.execute)


if __name__ == "__main__":
    sys.exit(main())
