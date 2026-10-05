#!/usr/bin/env python3
"""team_sync.py: Synchronizes local promoted cells and metrics with team repositories.

Usage:
    python enzymes/team_sync.py [push|pull|status]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def resolve_workspace() -> Path:
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
    print(f"Syncing local promoted cells to team repo ({team_repo})...")
    promoted_dir = team_repo / "cells" / "promoted"
    promoted_dir.mkdir(parents=True, exist_ok=True)
    snap_dir = team_repo / "snapshots" / member_id
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

    # Metrics snapshot sync
    print("Syncing metrics snapshot...")
    metrics_snapshot_py = repo_dir / "enzymes" / "metrics_snapshot.py"
    if metrics_snapshot_py.is_file():
        subprocess.run([sys.executable, str(metrics_snapshot_py), "--save"], capture_output=True)

    metrics_repo = repo_dir / "docs" / "snapshots"
    snapshots = sorted(metrics_repo.glob("*.json"), key=os.path.getmtime, reverse=True)
    if snapshots:
        shutil.copy2(str(snapshots[0]), str(snap_dir / snapshots[0].name))

    # Git operations
    if (team_repo / ".git").is_dir():
        subprocess.run(["git", "add", "cells/promoted", f"snapshots/{member_id}"], cwd=str(team_repo))
        subprocess.run(
            ["git", "commit", "-m", f"chore(sync): update promoted cells and metrics for {member_id}"],
            cwd=str(team_repo),
            capture_output=True,
        )
        subprocess.run(["git", "push"], cwd=str(team_repo), capture_output=True)

    if org_repo and (org_repo / ".git").is_dir():
        subprocess.run(["git", "add", "cells/promoted"], cwd=str(org_repo))
        subprocess.run(
            ["git", "commit", "-m", f"chore(sync): update org promoted cells from {member_id}"],
            cwd=str(org_repo),
            capture_output=True,
        )
        subprocess.run(["git", "push"], cwd=str(org_repo), capture_output=True)

    print("Push complete.")
    return 0


def run_pull(repo_dir: Path, team_repo: Path, org_repo: Path | None) -> int:
    print(f"Pulling cells from team repo ({team_repo})...")
    if (team_repo / ".git").is_dir():
        subprocess.run(["git", "pull"], cwd=str(team_repo), capture_output=True)
    if org_repo and (org_repo / ".git").is_dir():
        subprocess.run(["git", "pull"], cwd=str(org_repo), capture_output=True)

    local_cells_dir = repo_dir / ".soma" / "cells"
    local_cells_dir.mkdir(parents=True, exist_ok=True)

    existing_cells = {f.name for f in local_cells_dir.rglob("*.md")}

    def pull_from_dir(src_dir: Path, source_label: str) -> None:
        if not src_dir.is_dir():
            return
        for f in src_dir.glob("*.md"):
            if f.name not in existing_cells:
                content = f.read_text(encoding="utf-8")
                if "source:" not in content:
                    content = content.replace("---\n", f"---\nsource: {source_label}\n", 1)
                dest = local_cells_dir / f.name
                dest.write_text(content, encoding="utf-8")
                print(f"Pulled: {f.name} (from {source_label})")
                existing_cells.add(f.name)

    pull_from_dir(team_repo / "cells" / "promoted", "team")
    if org_repo:
        pull_from_dir(org_repo / "cells" / "promoted", "org")

    print("Pull complete.")
    return 0


def run_status(repo_dir: Path, team_repo: Path, org_repo: Path | None) -> int:
    local_cells = 0
    local_cells_dir = repo_dir / ".soma" / "cells"
    if local_cells_dir.is_dir():
        local_cells = sum(1 for _ in local_cells_dir.rglob("*.md"))

    team_cells = 0
    team_promoted = team_repo / "cells" / "promoted"
    if team_promoted.is_dir():
        team_cells = sum(1 for f in team_promoted.glob("*.md"))

    org_cells = 0
    if org_repo:
        org_promoted = org_repo / "cells" / "promoted"
        if org_promoted.is_dir():
            org_cells = sum(1 for f in org_promoted.glob("*.md"))

    print(f"Local cells: {local_cells}")
    print(f"Team cells ({team_repo}): {team_cells}")
    if org_repo:
        print(f"Org cells ({org_repo}): {org_cells}")

    cell_fitness_py = repo_dir / "enzymes" / "cell_fitness.py"
    if cell_fitness_py.is_file():
        try:
            res = subprocess.run([sys.executable, str(cell_fitness_py), "--json"], capture_output=True, text=True)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                eligible = [
                    item["cell"]
                    for item in data
                    if item.get("score") is not None and item.get("score") > 0.85
                ]
                print(f"Cells eligible for promotion: {len(eligible)}")
        except Exception:
            pass
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Team synchronization enzyme")
    parser.add_argument("command", nargs="?", default="status", choices=["push", "pull", "status"])
    args = parser.parse_args(argv)

    repo_dir = resolve_workspace()
    cfg = load_soma_config(repo_dir)

    team_repo_str = os.environ.get("TEAM_REPO") or cfg.get("TEAM_REPO")
    if not team_repo_str:
        print("TEAM_REPO not configured.")
        print("Please set it in soma.conf (see soma.conf.example).")
        return 0

    team_repo = Path(os.path.expanduser(team_repo_str)).resolve()
    org_repo_str = os.environ.get("ORG_REPO") or cfg.get("ORG_REPO")
    org_repo = Path(os.path.expanduser(org_repo_str)).resolve() if org_repo_str else None
    member_id = os.environ.get("TEAM_MEMBER_ID") or cfg.get("TEAM_MEMBER_ID") or "local_user"

    if args.command == "push":
        return run_push(repo_dir, team_repo, org_repo, member_id)
    elif args.command == "pull":
        return run_pull(repo_dir, team_repo, org_repo)
    else:
        return run_status(repo_dir, team_repo, org_repo)


if __name__ == "__main__":
    sys.exit(main())
