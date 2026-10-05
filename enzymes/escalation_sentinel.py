#!/usr/bin/env python3
"""escalation_sentinel.py — Zero-token protocol escalation recommender & last-gasp sentinel.

Dual-function enzyme:
1. Recommender mode (default): Analyzes staged/unstaged git changes and recommends
   minimum review protocol based on file sensitivity patterns and diff size.
   Usage:
     python3 enzymes/escalation_sentinel.py [--staged]
     python3 enzymes/escalation_sentinel.py [--all]
     python3 enzymes/escalation_sentinel.py [file...]

2. Last-gasp mode: Checks cells queued for apoptosis in .soma/cells/.last_gasp_queue.
   Usage:
     python3 enzymes/escalation_sentinel.py --last-gasp
"""
from __future__ import annotations

import argparse
import fnmatch
import glob
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from soma_sdk.cells import parse_cell_file

# ── Sensitivity Classification Patterns ──────────────────────────────────────

HIGH_PATTERNS = [
    r"enzymes/.*\.sh$",
    r"install\.sh$",
    r"install\.ps1$",
    r"Makefile$",
    r"hooks\.json",
    r"\.github/workflows/",
    r"auth|credential|secret|token|password",
    r"docker|Dockerfile",
    r"requirements\.txt$|package\.json$|go\.mod$",
]

MEDIUM_PATTERNS = [
    r"genome/.*\.md$",
    r"organs/.*/SKILL\.md$",
    r"steering\.conf",
    r"\.py$|\.js$|\.ts$|\.go$",
]

LOW_PATTERNS = [
    r"(?:^|/)docs/",
    r"README\.md$",
    r"LICENSE$",
    r"CHANGELOG|EVOLUTION|METRICS|EXPERIMENTS",
    r"\.txt$|\.csv$|\.json$",
]

TEST_PATTERNS = [
    r"\.test\.",
    r"_test\.",
    r"^tests/",
]

PROTOCOL_RANKS = {
    "breeze": 1,
    "gale": 2,
    "trident": 3,
    "maelstrom": 4,
    "tempest": 5,
}


def classify_file(filepath: str) -> str:
    norm = filepath.replace("\\", "/").lstrip("./")
    for pat in HIGH_PATTERNS:
        if re.search(pat, norm, re.IGNORECASE):
            return "HIGH"
    for pat in MEDIUM_PATTERNS:
        if re.search(pat, norm, re.IGNORECASE):
            return "MEDIUM"
    for pat in LOW_PATTERNS:
        if re.search(pat, norm, re.IGNORECASE):
            return "LOW"
    return "MEDIUM"


def is_test_file(filepath: str) -> bool:
    norm = filepath.replace("\\", "/").lstrip("./")
    for pat in TEST_PATTERNS:
        if re.search(pat, norm, re.IGNORECASE):
            return True
    return False


def gather_files(mode: str, file_args: list[str], workspace: Path) -> list[str]:
    if file_args:
        return [f.strip() for f in file_args if f.strip()]

    files: set[str] = set()
    try:
        if mode == "--staged":
            out = subprocess.check_output(
                ["git", "diff", "--cached", "--name-only"],
                cwd=workspace,
                text=True,
                stderr=subprocess.DEVNULL,
            )
            files.update(line.strip() for line in out.splitlines() if line.strip())
        else:  # --all
            out1 = subprocess.check_output(
                ["git", "diff", "--name-only"],
                cwd=workspace,
                text=True,
                stderr=subprocess.DEVNULL,
            )
            out2 = subprocess.check_output(
                ["git", "diff", "--cached", "--name-only"],
                cwd=workspace,
                text=True,
                stderr=subprocess.DEVNULL,
            )
            files.update(line.strip() for line in out1.splitlines() if line.strip())
            files.update(line.strip() for line in out2.splitlines() if line.strip())
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass

    return sorted(files)


def get_diff_size(mode: str, file_args: list[str], workspace: Path) -> int:
    total_lines = 0
    try:
        commands: list[list[str]] = []
        if file_args:
            commands.append(["git", "diff", "--numstat", "--"] + file_args)
            commands.append(["git", "diff", "--cached", "--numstat", "--"] + file_args)
        elif mode == "--staged":
            commands.append(["git", "diff", "--cached", "--numstat"])
        else:
            commands.append(["git", "diff", "--numstat"])
            commands.append(["git", "diff", "--cached", "--numstat"])

        for cmd in commands:
            out = subprocess.check_output(
                cmd,
                cwd=workspace,
                text=True,
                stderr=subprocess.DEVNULL,
            )
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        ins = int(parts[0]) if parts[0] != "-" else 0
                        dele = int(parts[1]) if parts[1] != "-" else 0
                        total_lines += ins + dele
                    except ValueError:
                        pass
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass

    return total_lines


def detect_branch_ops(workspace: Path) -> str:
    try:
        out = subprocess.check_output(
            ["git", "reflog", "--format=%gs", "-5"],
            cwd=workspace,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        if re.search(r"branch -[mMdD]|push.*force|rebase|reset.*hard", out, re.IGNORECASE):
            return "CRITICAL"
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass
    return "NONE"


def check_membrane_overrides(workspace: Path, files: list[str], current_protocol: str) -> tuple[str, str]:
    best_protocol = current_protocol
    best_rank = PROTOCOL_RANKS.get(current_protocol, 1)
    override_reason = ""

    cells_dir = workspace / ".soma" / "cells"
    for cell_subdir in ["membranes", "walls"]:
        target_dir = cells_dir / cell_subdir
        if not target_dir.is_dir():
            continue
        for cell_path in target_dir.glob("*.md"):
            if not cell_path.is_file():
                continue
            try:
                metadata, _ = parse_cell_file(str(cell_path))
                if not metadata:
                    continue
                min_mode = str(metadata.get("minimum_mode", "")).strip().lower()
                target_paths = metadata.get("target_paths", [])
                if isinstance(target_paths, str):
                    target_paths = [target_paths]

                if min_mode in PROTOCOL_RANKS and target_paths:
                    mem_rank = PROTOCOL_RANKS[min_mode]
                    path_matched = False
                    matched_target = ""
                    for tp in target_paths:
                        for f in files:
                            if f == tp or fnmatch.fnmatch(f, tp) or fnmatch.fnmatch(f, f"*{tp}*"):
                                path_matched = True
                                matched_target = tp
                                break
                        if path_matched:
                            break

                    if path_matched and mem_rank > best_rank:
                        best_rank = mem_rank
                        best_protocol = min_mode
                        override_reason = f"Membrane escalation for {matched_target} ({min_mode})"
            except Exception:
                continue

    return best_protocol, override_reason


def recommend_protocol(mode: str, file_args: list[str], workspace: Path | None = None) -> int:
    root = workspace or Path.cwd()
    files = gather_files(mode, file_args, root)

    if not files:
        print("PROTOCOL=none")
        print("REASON=No changes detected")
        return 1

    total_files = len(files)
    high_count = 0
    medium_count = 0
    low_count = 0
    test_count = 0
    high_files_list: list[str] = []

    for f in files:
        level = classify_file(f)
        if level == "HIGH":
            high_count += 1
            high_files_list.append(f)
        elif level == "MEDIUM":
            medium_count += 1
        elif level == "LOW":
            low_count += 1

        if is_test_file(f):
            test_count += 1

    high_files = ", ".join(high_files_list)
    branch_ops = detect_branch_ops(root)
    diff_lines = get_diff_size(mode, file_args, root)

    protocol = "breeze"
    reasons_list: list[str] = []

    # Rule 1: Branch operations -> minimum Maelstrom
    if branch_ops == "CRITICAL":
        protocol = "maelstrom"
        reasons_list.append("Branch operation detected (rename/force-push/rebase)")

    # Rule 2: HIGH sensitivity files
    if high_count >= 3:
        protocol = "maelstrom"
        reasons_list.append(f"{high_count} high-sensitivity files: {high_files}")
    elif high_count >= 1:
        if protocol not in ("maelstrom", "tempest"):
            protocol = "trident"
            reasons_list.append(f"High-sensitivity file(s): {high_files}")

    # Rule 3: Security-sensitive paths -> Maelstrom minimum
    if re.search(r"auth|credential|secret|token|password", high_files, re.IGNORECASE):
        protocol = "maelstrom"
        reasons_list.append("Security-sensitive path detected")

    # Rule 4: Large diffs -> escalate one level
    if diff_lines > 200:
        if protocol == "breeze":
            protocol = "gale"
            reasons_list.append(f"Large diff ({diff_lines} lines)")
        elif protocol == "gale":
            protocol = "trident"
            reasons_list.append(f"Large diff ({diff_lines} lines)")
        elif protocol == "trident":
            protocol = "maelstrom"
            reasons_list.append(f"Large diff ({diff_lines} lines)")

    # Rule 5: Pure docs -> Breeze
    if high_count == 0 and medium_count == 0 and low_count > 0:
        protocol = "breeze"
        reasons_list = ["All changes are low-sensitivity (docs/README)"]

    # Rule 5b: Test-only changes -> Gale
    if high_count == 0 and test_count > 0 and (test_count + low_count) == total_files:
        protocol = "gale"
        reasons_list = [f"Test-only changes ({test_count} test file(s); test changes do not need Trident)"]

    # Rule 6: Single known-location fix -> Breeze
    if protocol == "breeze" and total_files == 1 and high_count == 0 and test_count == 0:
        reasons_list = ["Single file, non-infrastructure change"]

    # Membrane Overrides
    protocol, mem_override = check_membrane_overrides(root, files, protocol)
    if mem_override:
        reasons_list.append(mem_override)

    reasons = "; ".join(reasons_list) if reasons_list else "Default classification"

    # Outputs
    print(f"PROTOCOL={protocol}")
    print(f"REASON={reasons}")
    print(f"FILES_TOTAL={total_files}")
    print(f"FILES_HIGH={high_count}")
    print(f"FILES_MEDIUM={medium_count}")
    print(f"FILES_LOW={low_count}")
    print(f"FILES_TEST={test_count}")
    print(f"DIFF_LINES={diff_lines}")
    print(f"BRANCH_OPS={branch_ops}")

    # Human-readable summary to stderr
    print(f"⚡ Escalation Sentinel: {protocol.upper()} recommended", file=sys.stderr)
    print(f"   {reasons}", file=sys.stderr)
    print(
        f"   Files: {total_files} ({high_count} high, {medium_count} medium, {low_count} low, {test_count} test)",
        file=sys.stderr,
    )
    return 0


# ── Last Gasp Apoptosis Check ────────────────────────────────────────────────

def set_review_mode(workspace: str, mode: str) -> None:
    conf_path = os.path.join(workspace, "steering.conf")
    if not os.path.exists(conf_path):
        return

    with open(conf_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    with open(conf_path, "w", encoding="utf-8") as f:
        for line in lines:
            if line.startswith("REVIEW_MODE="):
                f.write(f"REVIEW_MODE={mode}\n")
            else:
                f.write(line)
    print(f"[Sentinel] Escalated REVIEW_MODE to {mode}")


def write_frontmatter(filepath: str, metadata: dict[str, Any], body: str) -> None:
    import yaml
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)
        f.write("---\n")
        if body.startswith("\n"):
            f.write(body[1:])
        else:
            f.write(body)


def run_last_gasp(workspace: Path | None = None) -> int:
    ws = str(workspace or Path.cwd())
    cells_dir = os.path.join(ws, ".soma", "cells")
    if not os.path.exists(cells_dir):
        return 0

    last_gasp_dir = os.path.join(cells_dir, ".last_gasp_queue")
    archive_dir = os.path.join(cells_dir, ".archive")

    if not os.path.exists(last_gasp_dir):
        return 0

    queued_files = glob.glob(os.path.join(last_gasp_dir, "*.md"))
    if not queued_files:
        return 0

    for fpath in queued_files:
        filename = os.path.basename(fpath)
        try:
            metadata, body = parse_cell_file(fpath)
        except Exception:
            continue
        if not metadata:
            continue

        organ = metadata.get("organ", "governance-auditor")
        print(f"[Sentinel] Cell {filename} faces APOPTOSIS. Invoking Last Gasp Organ: {organ}...")

        result_file = os.path.join(last_gasp_dir, filename.replace(".md", ".result"))
        organ_validates_cell = os.path.exists(result_file)

        if organ_validates_cell:
            print(f"[Sentinel] Organ '{organ}' VALIDATED the cell! Saving from Apoptosis.")
            set_review_mode(ws, "TEMPEST")
            if "fitness" not in metadata:
                metadata["fitness"] = {}
            metadata["fitness"]["score"] = 0.75
            metadata["fitness"]["stress_survived"] = metadata["fitness"].get("stress_survived", 0) + 1

            raw_type = str(metadata.get("type", "wall")).rstrip("s")
            allowed_types = {"wall", "membrane", "vacuole", "chloroplast", "ribosome", "nucleus"}
            cell_type = raw_type if raw_type in allowed_types else "wall"
            parent_type = cell_type + "s"
            target_dir = os.path.abspath(os.path.join(cells_dir, parent_type))
            abs_cells_dir = os.path.abspath(cells_dir)
            if not target_dir.startswith(abs_cells_dir) or os.path.commonpath([abs_cells_dir, target_dir]) != abs_cells_dir:
                target_dir = os.path.join(abs_cells_dir, "walls")
            os.makedirs(target_dir, exist_ok=True)
            new_path = os.path.join(target_dir, filename)

            write_frontmatter(new_path, metadata, body)
            os.remove(fpath)
        else:
            print(f"[Sentinel] Organ '{organ}' REFUTED the cell! Brutally punishing and archiving.")
            if "fitness" not in metadata:
                metadata["fitness"] = {}
            metadata["fitness"]["score"] = 0.0
            metadata["fitness"]["false_positives"] = metadata["fitness"].get("false_positives", 0) + 10

            os.makedirs(archive_dir, exist_ok=True)
            new_path = os.path.join(archive_dir, filename)

            write_frontmatter(new_path, metadata, body)
            os.remove(fpath)

    return 0


# ── Unified Main ─────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args_list = argv if argv is not None else sys.argv[1:]

    if "--last-gasp" in args_list:
        return run_last_gasp()

    mode = "--all"
    file_args: list[str] = []

    for arg in args_list:
        if arg == "--staged":
            mode = "--staged"
        elif arg == "--all":
            mode = "--all"
        elif not arg.startswith("--"):
            file_args.append(arg)

    return recommend_protocol(mode=mode, file_args=file_args)


if __name__ == "__main__":
    sys.exit(main())
