"""soma_core.sync — Protocol escalation, liveness sentinels, team sync, HGT ribosome, and hooks.

Consolidates:
- Subagent liveness & deadlock sentinel (formerly enzymes/liveness_sentinel.py)
- Protocol escalation recommender & last-gasp sentinel (formerly enzymes/escalation_sentinel.py)
- Team cell & metrics synchronization (formerly enzymes/team_sync.py)
- Horizontal Gene Transfer ribosome translation (formerly enzymes/hgt_ribosome.py)
- Periodic governance sweep (formerly enzymes/immune_sweep.py)
- Post-session transcript fitness and evidence hook (formerly enzymes/post_session_hook.py)
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fnmatch
import glob
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

from soma_core.workspace import resolve_workspace
from soma_core.frontmatter import parse_frontmatter, _get_body, dump_frontmatter

# ── Liveness Sentinel ──────────────────────────────────────────────────────


def check_liveness(payload_str: str) -> int:
    """Detect stalled or deadlocked subagents that fail to report back."""
    try:
        data = json.loads(payload_str)
        now = datetime.now(timezone.utc)
        for agent in data.get("agents", []):
            name = agent.get("name", "Unknown")
            dispatch_str = agent.get("dispatched", "")
            timeout = agent.get("timeout_seconds", 0)

            try:
                if dispatch_str.endswith("Z"):
                    dispatch_str = dispatch_str[:-1] + "+00:00"
                dispatch_time = datetime.fromisoformat(dispatch_str)
            except ValueError:
                print(f"[{name}] INVALID_DATE: {dispatch_str}")
                continue

            elapsed = (now - dispatch_time).total_seconds()

            if elapsed > timeout:
                print(
                    f"[{name}] STALLED (Elapsed: {elapsed:.1f}s, Timeout: {timeout}s) - Action suggested: kill or escalate"
                )
            elif elapsed > timeout * 0.8:
                print(
                    f"[{name}] WARNING (Elapsed: {elapsed:.1f}s, Timeout: {timeout}s) - Action suggested: nudge"
                )
            else:
                print(f"[{name}] HEALTHY (Elapsed: {elapsed:.1f}s, Timeout: {timeout}s)")
        return 0
    except json.JSONDecodeError:
        print("Error: Invalid JSON provided.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cli_liveness_sentinel(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Subagent liveness sentinel")
    parser.add_argument("--check", dest="payload", default="", help="JSON string with agent list")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if not args.payload:
        print("Usage: liveness_sentinel.py --check '{\"agents\": [...]}'")
        return 0

    return check_liveness(args.payload)


# ── Escalation Sentinel ────────────────────────────────────────────────────

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
        else:
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
                with open(cell_path, "r", encoding="utf-8-sig") as cf:
                    metadata = parse_frontmatter(cf.read())
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

    if branch_ops == "CRITICAL":
        protocol = "maelstrom"
        reasons_list.append("Branch operation detected (rename/force-push/rebase)")

    if high_count >= 3:
        protocol = "maelstrom"
        reasons_list.append(f"{high_count} high-sensitivity files: {high_files}")
    elif high_count >= 1:
        if protocol not in ("maelstrom", "tempest"):
            protocol = "trident"
            reasons_list.append(f"High-sensitivity file(s): {high_files}")

    if re.search(r"auth|credential|secret|token|password", high_files, re.IGNORECASE):
        protocol = "maelstrom"
        reasons_list.append("Security-sensitive path detected")

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

    if high_count == 0 and medium_count == 0 and low_count > 0:
        protocol = "breeze"
        reasons_list = ["All changes are low-sensitivity (docs/README)"]

    if high_count == 0 and test_count > 0 and (test_count + low_count) == total_files:
        protocol = "gale"
        reasons_list = [f"Test-only changes ({test_count} test file(s); test changes do not need Trident)"]

    if protocol == "breeze" and total_files == 1 and high_count == 0 and test_count == 0:
        reasons_list = ["Single file, non-infrastructure change"]

    protocol, mem_override = check_membrane_overrides(root, files, protocol)
    if mem_override:
        reasons_list.append(mem_override)

    reasons = "; ".join(reasons_list) if reasons_list else "Default classification"

    print(f"PROTOCOL={protocol}")
    print(f"REASON={reasons}")
    print(f"FILES_TOTAL={total_files}")
    print(f"FILES_HIGH={high_count}")
    print(f"FILES_MEDIUM={medium_count}")
    print(f"FILES_LOW={low_count}")
    print(f"FILES_TEST={test_count}")
    print(f"DIFF_LINES={diff_lines}")
    print(f"BRANCH_OPS={branch_ops}")

    print(f"⚡ Escalation Sentinel: {protocol.upper()} recommended", file=sys.stderr)
    print(f"   {reasons}", file=sys.stderr)
    print(
        f"   Files: {total_files} ({high_count} high, {medium_count} medium, {low_count} low, {test_count} test)",
        file=sys.stderr,
    )
    return 0


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
    try:
        import yaml
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("---\n")
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)
            f.write("---\n")
            if body.startswith("\n"):
                f.write(body[1:])
            else:
                f.write(body)
    except ImportError:
        dumped = dump_frontmatter(metadata)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"---\n{dumped}\n---\n")
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
            with open(fpath, "r", encoding="utf-8-sig") as cf:
                content = cf.read()
            metadata = parse_frontmatter(content)
            body = _get_body(content)
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
            conf_path = os.path.join(ws, "steering.conf")
            if os.path.exists(conf_path):
                with open(conf_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                with open(conf_path, "w", encoding="utf-8") as f:
                    for line in lines:
                        if line.startswith("REVIEW_MODE="):
                            f.write("REVIEW_MODE=TEMPEST\n")
                        else:
                            f.write(line)

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

            new_content = "---\n" + dump_frontmatter(metadata) + "---\n" + body
            with open(new_path, "w", encoding="utf-8") as outf:
                outf.write(new_content)
            os.remove(fpath)
        else:
            print(f"[Sentinel] Organ '{organ}' REFUTED the cell! Brutally punishing and archiving.")
            if "fitness" not in metadata:
                metadata["fitness"] = {}
            metadata["fitness"]["score"] = 0.0
            metadata["fitness"]["false_positives"] = metadata["fitness"].get("false_positives", 0) + 10

            os.makedirs(archive_dir, exist_ok=True)
            new_path = os.path.join(archive_dir, filename)

            new_content = "---\n" + dump_frontmatter(metadata) + "---\n" + body
            with open(new_path, "w", encoding="utf-8") as outf:
                outf.write(new_content)
            os.remove(fpath)

    return 0


def cli_escalation_sentinel(argv: Optional[List[str]] = None) -> int:
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


# ── Team Sync ──────────────────────────────────────────────────────────────


def load_soma_config(repo_dir: Path) -> dict[str, str]:
    conf_path = repo_dir / "soma.conf"
    cfg = {}
    if conf_path.is_file():
        with open(conf_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


def run_push(repo_dir: Path, team_repo: Path, org_repo: Path | None, member_id: str) -> int:
    clean_id = re.sub(r"[^a-zA-Z0-9._-]", "_", str(member_id)).lstrip("-")
    if not clean_id or ".." in str(member_id):
        raise ValueError(f"Invalid member_id: {member_id}")

    print(f"Syncing local promoted cells to team repo ({team_repo})...")
    promoted_dir = team_repo / "cells" / "promoted"
    promoted_dir.mkdir(parents=True, exist_ok=True)
    snap_dir = team_repo / "snapshots" / clean_id
    snap_dir.mkdir(parents=True, exist_ok=True)

    cells_dir = repo_dir / ".soma" / "cells"
    cell_fitness_py = repo_dir / "enzymes" / "cell_fitness.py"

    try:
        res = subprocess.run([sys.executable, str(cell_fitness_py), "--json"], capture_output=True, text=True)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            for item in data:
                if item.get("score") is not None and item.get("score") > 0.85:
                    cell_name = item["cell"]
                    src = cells_dir / cell_name
                    if not src.is_file():
                        for match in cells_dir.rglob(cell_name):
                            if match.is_file():
                                src = match
                                break
                    if src.is_file():
                        shutil.copy2(str(src), str(promoted_dir / cell_name))
                        print(f"Promoted: {cell_name}")
                        if org_repo:
                            org_promoted_dir = org_repo / "cells" / "promoted"
                            org_promoted_dir.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(str(src), str(org_promoted_dir / cell_name))
    except Exception as e:
        print(f"Error syncing cells: {e}", file=sys.stderr)

    print("Syncing metrics snapshot...")
    metrics_snapshot_py = repo_dir / "enzymes" / "metrics_snapshot.py"
    if metrics_snapshot_py.is_file():
        subprocess.run([sys.executable, str(metrics_snapshot_py), "--save"], capture_output=True)

    metrics_repo = repo_dir / "docs" / "snapshots"
    snapshots = sorted(metrics_repo.glob("*.json"), key=os.path.getmtime, reverse=True)
    if snapshots:
        shutil.copy2(str(snapshots[0]), str(snap_dir / snapshots[0].name))

    if (team_repo / ".git").is_dir():
        subprocess.run(["git", "add", "--", "cells/promoted", f"snapshots/{clean_id}"], cwd=str(team_repo))
        subprocess.run(
            ["git", "commit", "-m", f"chore(sync): update promoted cells and metrics for {clean_id}"],
            cwd=str(team_repo),
            capture_output=True,
        )
        subprocess.run(["git", "push"], cwd=str(team_repo), capture_output=True)

    if org_repo and (org_repo / ".git").is_dir():
        subprocess.run(["git", "add", "--", "cells/promoted"], cwd=str(org_repo))
        subprocess.run(
            ["git", "commit", "-m", f"chore(sync): update org promoted cells from {member_id}"],
            cwd=str(org_repo),
            capture_output=True,
        )
        subprocess.run(["git", "push"], cwd=str(org_repo), capture_output=True)

    print("Push complete.")
    return 0


def run_pull(repo_dir: Path, team_repo: Path, org_repo: Path | None) -> int:
    print(f"Pulling promoted cells from team repo ({team_repo})...")
    if (team_repo / ".git").is_dir():
        subprocess.run(["git", "pull", "--rebase"], cwd=str(team_repo), capture_output=True)

    if org_repo and (org_repo / ".git").is_dir():
        print(f"Pulling from org repo ({org_repo})...")
        subprocess.run(["git", "pull", "--rebase"], cwd=str(org_repo), capture_output=True)

    local_cells = repo_dir / ".soma" / "cells"
    ribosomes_dir = local_cells / "ribosomes"
    ribosomes_dir.mkdir(parents=True, exist_ok=True)

    team_promoted = team_repo / "cells" / "promoted"
    if team_promoted.is_dir():
        for f in team_promoted.glob("*.md"):
            dest = ribosomes_dir / f.name
            if not dest.exists():
                shutil.copy2(str(f), str(dest))
                print(f"Imported from team: {f.name} -> ribosomes/")

    if org_repo:
        org_promoted = org_repo / "cells" / "promoted"
        if org_promoted.is_dir():
            for f in org_promoted.glob("*.md"):
                dest = ribosomes_dir / f.name
                if not dest.exists():
                    shutil.copy2(str(f), str(dest))
                    print(f"Imported from org: {f.name} -> ribosomes/")

    print("Pull complete.")
    return 0


def run_status(repo_dir: Path, team_repo: Path, org_repo: Path | None) -> int:
    print("=== Team Sync Status ===")
    print(f"Local repo:  {repo_dir}")
    print(f"Team repo:   {team_repo} (exists: {team_repo.is_dir()})")
    if org_repo:
        print(f"Org repo:    {org_repo} (exists: {org_repo.is_dir()})")

    team_promoted = team_repo / "cells" / "promoted"
    team_count = len(list(team_promoted.glob("*.md"))) if team_promoted.is_dir() else 0
    print(f"Team promoted cells: {team_count}")

    if org_repo:
        org_promoted = org_repo / "cells" / "promoted"
        org_count = len(list(org_promoted.glob("*.md"))) if org_promoted.is_dir() else 0
        print(f"Org promoted cells:  {org_count}")

    return 0


def cli_team_sync(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Synchronize cells and metrics with team repositories")
    parser.add_argument("command", choices=["push", "pull", "status"], default="status", nargs="?")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    repo_dir = Path(resolve_workspace())
    cfg = load_soma_config(repo_dir)

    team_repo_str = cfg.get("TEAM_REPO", "../soma-team")
    team_repo = (repo_dir / team_repo_str).resolve()
    org_repo_str = cfg.get("ORG_REPO")
    org_repo = (repo_dir / org_repo_str).resolve() if org_repo_str else None
    member_id = cfg.get("MEMBER_ID", os.environ.get("USER", "anonymous"))

    if args.command == "push":
        return run_push(repo_dir, team_repo, org_repo, member_id)
    elif args.command == "pull":
        return run_pull(repo_dir, team_repo, org_repo)
    else:
        return run_status(repo_dir, team_repo, org_repo)


# ── Horizontal Gene Transfer (Ribosome) ────────────────────────────────────


def prompt_llm_translation(cell_content: str, mock: bool = False) -> str:
    """Translate domain-specific strategy into universal engineering law."""
    if mock:
        if "draft all combat-capable pawns" in cell_content:
            return """# Resource Consolidation (HGT)
- When a catastrophic event is detected (e.g., massive production outage), immediately consolidate resources to a defensible position.
- Halt all exploratory or non-essential feature work until the primary threat is neutralized.
- Do not engage in risky ad-hoc fixes unless core stability is breached."""
        else:
            return "# Generalized Strategy\n- Apply caution and verify inputs."

    return "# Generalized Strategy\n- Apply caution and verify inputs."


def cli_hgt_ribosome(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="HGT Ribosome Translator")
    parser.add_argument("source_file", help="Path to foreign cell")
    parser.add_argument("--mock", action="store_true", help="Use mock LLM output")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if not os.path.exists(args.source_file):
        print(f"Error: {args.source_file} not found.")
        return 1

    with open(args.source_file, "r", encoding="utf-8-sig") as f:
        content = f.read()

    metadata = parse_frontmatter(content)
    body = _get_body(content)

    print(f"🧬 Ribosome intercepting: {args.source_file}")
    translated_body = prompt_llm_translation(body, mock=args.mock)

    ws = resolve_workspace()
    genome_dir = os.path.join(ws, "genome")
    os.makedirs(genome_dir, exist_ok=True)

    first_line = translated_body.split("\n")[0]
    filename_base = re.sub(r"[^a-z0-9]+", "-", first_line.lower().replace("#", "").strip()).strip("-")
    gene_id = f"hgt-{filename_base}"
    filename = f"{gene_id}.md"

    output_path = os.path.join(genome_dir, filename)
    new_metadata = {
        "id": gene_id,
        "domain": "governance",
        "name": filename_base,
        "type": "gene",
    }
    with open(output_path, "w", encoding="utf-8") as outf:
        outf.write("---\n" + dump_frontmatter(new_metadata) + "---\n" + translated_body + "\n")

    print(f"✅ Translated and saved gene: {output_path}")
    return 0


# ── Immune Sweep ───────────────────────────────────────────────────────────


def resolve_home() -> Path:
    home_str = os.environ.get("USERPROFILE") or os.environ.get("HOME")
    if home_str:
        return Path(home_str)
    return Path.home()


def run_sweep(active_only: bool = False, soma_data_dir: Path | None = None) -> int:
    """Run periodic governance sweep."""
    from collections import Counter
    import time
    try:
        from enzymes.sweep_session import scan_transcript, to_session_metrics
    except ImportError:
        try:
            from sweep_session import scan_transcript, to_session_metrics
        except ImportError:
            scan_transcript = None
            to_session_metrics = None

    resolved_home = resolve_home()

    if soma_data_dir is None:
        env_data = os.environ.get("SOMA_DATA_DIR")
        soma_data_dir = Path(env_data) if env_data else resolved_home / ".gemini" / "antigravity"

    governance_dir = soma_data_dir / "scratch" / "ai-conversation-logs" / "governance"
    brain_dir = soma_data_dir / "brain"
    metrics_dir = governance_dir / "session_metrics"
    sweep_log = governance_dir / "sweep_log.jsonl"
    proposals = governance_dir / "pending_proposals.md"
    audit_log = governance_dir / "auto_applied_log.jsonl"
    gate_log = governance_dir / "gate_events.jsonl"

    metrics_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    sessions_scanned = 0
    metrics_generated = 0
    warnings_tallied = 0
    active_flagged = 0

    print(f"🔄 Governance Sweep — {timestamp}\n")

    # ── Check 1: Unreviewed Sessions ──────────────────────────────────────────
    if not active_only:
        print("📋 Check 1: Scanning for unreviewed sessions (>100 steps)...")
        if brain_dir.is_dir():
            for child in brain_dir.iterdir():
                if not child.is_dir():
                    continue

                session_id = child.name
                short_id = session_id[:8]
                transcript = child / ".system_generated" / "logs" / "transcript.jsonl"
                metrics_file = metrics_dir / f"{short_id}.json"

                if not transcript.is_file():
                    continue
                if metrics_file.is_file():
                    continue

                try:
                    with open(transcript, "r", encoding="utf-8", errors="replace") as fh:
                        step_count = sum(1 for _ in fh)
                except OSError:
                    step_count = 0

                if step_count > 100:
                    print(f"  🔍 {short_id} ({step_count} steps) — generating metrics...")
                    if scan_transcript and to_session_metrics:
                        try:
                            result = scan_transcript(str(transcript))
                            if result:
                                metrics = to_session_metrics(short_id, result)
                                with open(metrics_file, "w", encoding="utf-8") as out_f:
                                    json.dump(metrics, out_f, indent=2)
                                metrics_generated += 1
                                print(f"  ✅ {short_id}: metrics generated")
                            else:
                                print(f"  ⚠️  {short_id}: scan failed")
                        except Exception:
                            print(f"  ⚠️  {short_id}: scan failed")
                            if metrics_file.exists():
                                metrics_file.unlink(missing_ok=True)
                    sessions_scanned += 1

        print(f"  Done: {sessions_scanned} scanned, {metrics_generated} metrics generated\n")

    # ── Check 2: Warning Trends ──────────────────────────────────────────────
    warning_report = ""
    if not active_only:
        print("📋 Check 2: Tallying warning-level findings...")
        if audit_log.is_file() and audit_log.stat().st_size > 0:
            counts: Counter[str] = Counter()
            try:
                with open(audit_log, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            if entry.get("severity") == "warning":
                                counts[entry.get("rule", "unknown")] += 1
                        except json.JSONDecodeError:
                            continue

                hardening_candidates = []
                for rule, count in counts.most_common():
                    flag = "⚠️  CONSIDER HARDENING" if count >= 3 else ""
                    line_str = f"  {count}x {rule} {flag}".rstrip()
                    print(line_str)
                    warnings_tallied += 1
                    if count >= 3:
                        hardening_candidates.append(line_str)

                if hardening_candidates:
                    warning_report = "\n".join(hardening_candidates)
            except OSError:
                print("  (parse error)")
        else:
            print("  (no audit log entries)")
        print()

    # ── Check 3: Metrics Recomputation ───────────────────────────────────────
    if not active_only:
        print("📋 Check 3: Recomputing aggregate metrics...")
        total_steps = 0
        total_waste = 0
        session_count = 0
        deep_sessions = 0
        sweep_sessions = 0

        if metrics_dir.is_dir():
            for f in sorted(metrics_dir.glob("*.json")):
                try:
                    with open(f, "r", encoding="utf-8", errors="replace") as fh:
                        m = json.load(fh)
                    if "total_steps" not in m:
                        continue
                    steps = int(m.get("total_steps", 0))
                    flat_waste = m.get("wasted_steps")
                    nested_waste = None
                    if isinstance(m.get("waste"), dict):
                        nested_waste = m["waste"].get("total_wasted_steps")

                    if nested_waste is not None and (flat_waste is None or flat_waste == 0):
                        waste = int(nested_waste)
                    elif flat_waste is not None:
                        waste = int(flat_waste)
                    else:
                        waste = 0

                    is_sweep = m.get("scan_type") == "lightweight_sweep" or m.get("review_tier") == "heuristic_sweep"
                    if is_sweep:
                        sweep_sessions += 1
                    else:
                        deep_sessions += 1

                    total_steps += steps
                    total_waste += waste
                    session_count += 1
                except (json.JSONDecodeError, KeyError, TypeError, ValueError, OSError):
                    continue

        rate = round(total_waste / total_steps * 100, 1) if total_steps > 0 else 0
        print(f"  Sessions: {session_count} (deep: {deep_sessions}, sweep: {sweep_sessions})")
        print(f"  Total steps: {total_steps:,}")
        print(f"  Total waste: {total_waste:,} ({rate}%)\n")

    # ── Check 4: Active Session Monitoring ───────────────────────────────────
    print("📋 Check 4: Checking active sessions (modified in last 2 hours)...")
    active_report_lines: list[str] = []
    now_ts = time.time()
    two_hours_ago = now_ts - (120 * 60)

    if brain_dir.is_dir():
        for transcript_path in brain_dir.glob("*/.system_generated/logs/transcript.jsonl"):
            try:
                st = transcript_path.stat()
                if st.st_mtime < two_hours_ago:
                    continue
            except OSError:
                continue

            try:
                with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
                    step_count = sum(1 for _ in f)
            except OSError:
                step_count = 0

            if step_count > 50:
                session_id = transcript_path.parent.parent.parent.name
                short_id = session_id[:8]

                waste_pct = 0
                top_pattern = "unknown"
                if scan_transcript:
                    try:
                        res = scan_transcript(str(transcript_path))
                        if res:
                            waste_pct = int(float(res.get("estimated_waste_rate", 0)) * 100)
                            top_patterns = res.get("top_patterns", [])
                            top_pattern = top_patterns[0]["pattern"] if top_patterns else "clean"
                    except Exception:
                        pass

                if waste_pct > 15:
                    print(f"  ⚠️  {short_id}: {step_count} steps, ~{waste_pct}% waste, top: {top_pattern}")
                    active_flagged += 1
                    active_report_lines.append(f"  ⚠️  {short_id}: {waste_pct}% waste ({top_pattern})")
                else:
                    print(f"  ✅ {short_id}: {step_count} steps, ~{waste_pct}% waste")

    if active_flagged == 0:
        print("  All active sessions clean.")
    print()

    # ── Check 5: Gate Event Summary ──────────────────────────────────────────
    if gate_log.is_file() and not active_only:
        print("📋 Check 5: Gate event summary...")
        try:
            with open(gate_log, "r", encoding="utf-8", errors="replace") as gf:
                lines = gf.readlines()
            gate_count = len(lines)
            blocked = sum(1 for l in lines if '"BLOCKED"' in l)
            print(f"  Total events: {gate_count}")
            print(f"  Blocked: {blocked}\n")
        except OSError:
            pass

    # ── Generate Sweep Report ────────────────────────────────────────────────
    has_actionable = metrics_generated > 0 or bool(warning_report) or active_flagged > 0

    if has_actionable:
        proposals_content = [
            "",
            f"## Governance Sweep — {timestamp}",
            "",
        ]
        if metrics_generated > 0:
            proposals_content.extend([
                f"### New Session Metrics ({metrics_generated} generated)",
                "Run `staff-review` post-mortem for deep analysis on high-waste sessions.",
                "",
            ])
        if warning_report:
            proposals_content.extend([
                "### Warning Trends — Hardening Candidates",
                warning_report,
                "",
            ])
        if active_flagged > 0:
            proposals_content.extend([
                "### Active Session Alerts",
                "\n".join(active_report_lines),
                "",
            ])

        try:
            with open(proposals, "a", encoding="utf-8") as pf:
                pf.write("\n".join(proposals_content) + "\n")
            print("📝 Sweep report appended to pending_proposals.md")
        except OSError:
            pass

    # ── Log Sweep ────────────────────────────────────────────────────────────
    sweep_entry = {
        "timestamp": timestamp,
        "sessions_scanned": sessions_scanned,
        "metrics_generated": metrics_generated,
        "warnings_tallied": warnings_tallied,
        "active_flagged": active_flagged,
        "has_actionable": has_actionable,
    }
    try:
        with open(sweep_log, "a", encoding="utf-8") as sf:
            sf.write(json.dumps(sweep_entry) + "\n")
    except OSError:
        pass

    print()
    print("✅ Governance sweep complete.")
    print(
        f"   Scanned: {sessions_scanned} | Generated: {metrics_generated} | "
        f"Warnings: {warnings_tallied} | Active flags: {active_flagged}"
    )
    return 0


def cli_immune_sweep(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Governance Sweep")
    parser.add_argument("--active-only", action="store_true", help="Only check active sessions")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    return run_sweep(active_only=args.active_only)


# ── Post-Session Hook ──────────────────────────────────────────────────────


def run_post_session_hook(
    transcript_path: Path,
    platform: str | None = None,
    cells_dir: Path | None = None,
    evidence_dir: Path | None = None,
    repo_root: Path | None = None,
) -> int:
    """Run post-session transcript fitness and evidence collection."""
    if not transcript_path.is_file():
        print(f"Error: transcript not found: {transcript_path}", file=sys.stderr)
        return 1

    root = repo_root or Path(resolve_workspace())
    cells_dir = cells_dir or root / ".soma" / "cells"
    evidence_dir = evidence_dir or root / ".soma" / "evidence"

    from soma_core.telemetry import (
        detect_platform,
        extract_modified_files,
        match_cells,
        resolve_transcript_id,
        update_fitness,
    )
    try:
        from enzymes.evidence_collector import aggregate_evidence, build_observation, check_compliance
    except ImportError:
        try:
            from evidence_collector import aggregate_evidence, build_observation, check_compliance
        except ImportError:
            aggregate_evidence = build_observation = check_compliance = None

    resolved_platform = platform or detect_platform(transcript_path)
    transcript_id = resolve_transcript_id(transcript_path, resolved_platform)

    print(f"Processing transcript: {transcript_path}")
    print(f"  Platform: {resolved_platform}")
    modified = extract_modified_files(transcript_path, platform=resolved_platform)
    print(f"  Modified files: {len(modified)}")

    triggered = match_cells(modified, cells_dir, repo_root=str(root))
    print(f"  Cells triggered: {len(triggered)}")
    for t in triggered:
        print(f"    - {t['cell_id']} ({len(t['matched_files'])} files)")

    update_fitness(triggered, transcript_id, evidence_dir)
    print(f"  Fitness updated: {evidence_dir / 'signals.jsonl'}")

    try:
        from soma_cli.sync import aggregate_evidence as sync_aggregate_evidence
        from soma_cli.sync import sync_frontmatter

        counts = sync_aggregate_evidence(str(evidence_dir))
        if counts:
            changes = sync_frontmatter(str(cells_dir), counts)
            if changes:
                print(f"  Frontmatter synced: {len(changes)} cells updated")
    except ImportError:
        pass

    rules = ["read-before-write", "test-before-implementation", "no-hardcoded-paths"]
    observations = []
    for rule_id in rules:
        result = check_compliance(transcript_path, rule_id)
        obs = build_observation(result, transcript_path, rule_id)
        if obs is not None:
            observations.append(obs)

    if observations:
        summary = aggregate_evidence(observations)
        evidence_dir.mkdir(parents=True, exist_ok=True)
        outfile = evidence_dir / "compliance.jsonl"
        try:
            with open(outfile, "a", encoding="utf-8") as f:
                f.write(json.dumps(summary) + "\n")
        except OSError as exc:
            print(f"Warning: could not write compliance evidence: {exc}", file=sys.stderr)

    return 0


def cli_post_session_hook(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Post-session hook for Soma governance")
    parser.add_argument("transcript_path", type=Path, help="Path to transcript.jsonl")
    parser.add_argument("--platform", default=None, help="Platform name")
    parser.add_argument("--cells-dir", type=Path, default=None, help="Cells directory")
    parser.add_argument("--evidence-dir", type=Path, default=None, help="Evidence directory")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    return run_post_session_hook(
        transcript_path=args.transcript_path,
        platform=args.platform,
        cells_dir=args.cells_dir,
        evidence_dir=args.evidence_dir,
    )


__all__ = [
    "HIGH_PATTERNS",
    "MEDIUM_PATTERNS",
    "LOW_PATTERNS",
    "TEST_PATTERNS",
    "PROTOCOL_RANKS",
    "check_liveness",
    "cli_liveness_sentinel",
    "classify_file",
    "is_test_file",
    "gather_files",
    "get_diff_size",
    "detect_branch_ops",
    "check_membrane_overrides",
    "recommend_protocol",
    "set_review_mode",
    "write_frontmatter",
    "run_last_gasp",
    "cli_escalation_sentinel",
    "load_soma_config",
    "run_push",
    "run_pull",
    "run_status",
    "cli_team_sync",
    "prompt_llm_translation",
    "cli_hgt_ribosome",
    "resolve_home",
    "run_sweep",
    "cli_immune_sweep",
    "run_post_session_hook",
    "cli_post_session_hook",
]
