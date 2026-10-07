"""CLI command handler for ``soma genesis``."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def run_genesis(args: argparse.Namespace) -> int:
    """Scan a codebase and generate governance cell files."""
    from soma_cli.genesis_scanner import scan, detect_project_type
    from soma_cli.genesis_generator import generate_cells, generate_report

    from soma_core.workspace import Workspace

    raw_root = (
        getattr(args, "project_root", None)
        or getattr(args, "workspace", None)
        or getattr(args, "_project_root", None)
    )
    if raw_root is not None and not Path(raw_root).is_dir():
        print(f"Error: {raw_root} is not a directory", file=sys.stderr)
        return 1

    ws = getattr(args, "ws", None) or Workspace.resolve(raw_root)
    project_root = ws.root
    if not project_root.is_dir():
        print(f"Error: {project_root} is not a directory", file=sys.stderr)
        return 1

    min_confidence = getattr(args, "min_confidence", 0.5)
    dry_run = getattr(args, "dry_run", False)
    use_json = getattr(args, "json", False)
    force = getattr(args, "force", False)

    # Phase 1: Scan
    project_type = detect_project_type(project_root)
    candidates = scan(project_root, min_confidence=min_confidence)

    if not candidates:
        msg = "No governance candidates detected."
        if use_json:
            print(json.dumps({
                "status": "empty",
                "message": msg,
                "project_type": project_type,
            }))
        else:
            print(f"🔬 {msg}")
        return 0

    # Display candidates
    if use_json:
        output = {
            "project_type": project_type,
            "candidates": [
                {
                    "name": c.name,
                    "proposed_type": c.proposed_type,
                    "hypothesis": c.hypothesis,
                    "confidence": c.confidence,
                    "target_paths": c.target_paths,
                }
                for c in candidates
            ],
        }
        if dry_run:
            print(json.dumps(output, indent=2))
            return 0
    else:
        # Pretty-print scan results
        print("\n🔬 Scanning repository...")
        print(f"  Language: {project_type.title()}")
        print(f"  Source files: {_count_source_files(project_root, project_type)}")
        print(f"\n🧬 Detected {len(candidates)} governance candidates:\n")

        type_emoji = {
            "wall": "🧱",
            "membrane": "🫧",
            "vacuole": "🟤",
            "chloroplast": "🟢",
            "plasmodesmata": "🔗",
        }
        groups: dict[str, list] = {}
        for c in candidates:
            groups.setdefault(c.proposed_type, []).append(c)

        for ptype in ["wall", "membrane", "vacuole", "chloroplast", "plasmodesmata"]:
            if ptype not in groups:
                continue
            emoji = type_emoji.get(ptype, "")
            print(f"  {emoji} {ptype.upper()}S ({len(groups[ptype])})")
            for c in groups[ptype]:
                branch = "├" if c != groups[ptype][-1] else "└"
                print(
                    f"  {branch}── {c.name:<30s} "
                    f"({c.confidence:.0%}) {c.hypothesis}"
                )
            print()

        if dry_run:
            print("  (dry run — no files written)")
            return 0

        # Confirm unless --yes
        if not getattr(args, "yes", False):
            try:
                answer = input(
                    f"  Write {len(candidates)} cells to .soma/cells/vacuoles/? [Y/n] "
                )
                if answer.strip().lower() in ("n", "no"):
                    print("  Aborted.")
                    return 0
            except (EOFError, KeyboardInterrupt):
                print("\n  Aborted.")
                return 0

    # Phase 2: Generate
    cells_dir = project_root / ".soma" / "cells"
    results = generate_cells(candidates, cells_dir, dry_run=dry_run, force=force)

    # Generate organelle report
    report = generate_report(candidates, project_type)
    report_path = project_root / "docs" / "organelles.md"
    if not dry_run:
        if report_path.is_symlink():
            if not use_json:
                print(f"  ⚠️  Skipping report: {report_path} is a symlink")
        elif report_path.exists() and not force:
            if not use_json:
                print(f"  ℹ️  {report_path.name}: already exists (use --force to overwrite)")
        else:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report, encoding="utf-8")

    created = sum(1 for r in results if r["action"] == "created")
    skipped = sum(1 for r in results if r["action"] == "skipped")

    install_hooks_flag = getattr(args, "install_hooks", False)
    no_hooks_flag = getattr(args, "no_hooks", False)
    hook_installed = False

    if not dry_run and not no_hooks_flag:
        from soma_cli.hooks import install_hook
        if install_hooks_flag:
            hook_installed = install_hook(project_root)
        elif not getattr(args, "yes", False) and not use_json and sys.stdin.isatty():
            try:
                answer = input("  🪝 Install git pre-commit hook in this repository? [Y/n] ")
                if answer.strip().lower() not in ("n", "no"):
                    hook_installed = install_hook(project_root)
            except (EOFError, KeyboardInterrupt):
                pass

    if use_json:
        print(json.dumps({
            "status": "done",
            "created": created,
            "skipped": skipped,
            "results": results,
            "hook_installed": hook_installed,
        }))
    else:
        print(f"\n✅ Created {created} cells, skipped {skipped} existing")
        print(f"📄 Organelle map: {report_path}")
        if hook_installed:
            print("🪝 Git pre-commit hook installed (.git/hooks/pre-commit)")
        print("🚀 Repository is fully governed! Next step: run 'git commit' or 'soma verify'")

    return 0


def _count_source_files(root: Path, project_type: str) -> int:
    """Count source files, skipping non-essential dirs."""
    from soma_cli.genesis_scanner import _iter_source_files
    return len(_iter_source_files(root, project_type, include_tests=True))
