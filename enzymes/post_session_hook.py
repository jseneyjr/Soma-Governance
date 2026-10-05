#!/usr/bin/env python3
"""Post-session hook: update cell fitness and evidence from a session transcript (pure Python).

Usage:
    python3 enzymes/post_session_hook.py <transcript_path> [--platform NAME] [--cells-dir DIR] [--evidence-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure repository root and enzymes directory are on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
for p in (str(REPO_ROOT), str(SCRIPT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from enzymes.evidence_collector import aggregate_evidence, build_observation, check_compliance
from enzymes.fitness_updater import (
    detect_platform,
    extract_modified_files,
    match_cells,
    resolve_transcript_id,
    update_fitness,
)


def run_post_session_hook(
    transcript_path: Path,
    platform: str | None = None,
    cells_dir: Path | None = None,
    evidence_dir: Path | None = None,
    repo_root: Path | None = None,
) -> int:
    if not transcript_path.is_file():
        print(f"Error: transcript not found: {transcript_path}", file=sys.stderr)
        return 1

    root = repo_root or REPO_ROOT
    cells_dir = cells_dir or root / ".soma" / "cells"
    evidence_dir = evidence_dir or root / ".soma" / "evidence"

    # Step 1: Update fitness signals
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

    # Sync JSONL evidence → cell frontmatter if soma_cli available
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

    # Step 2: Evidence enrichment — correlate rule compliance patterns
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Post-session hook for Soma governance")
    parser.add_argument("transcript", help="Path to transcript JSONL file")
    parser.add_argument("--platform", default=None, help="Platform name (antigravity, claude)")
    parser.add_argument("--cells-dir", default=None, help="Path to cells directory")
    parser.add_argument("--evidence-dir", default=None, help="Path to evidence directory")
    parser.add_argument("--repo-root", default=None, help="Path to repository root")
    args = parser.parse_args(argv)

    return run_post_session_hook(
        transcript_path=Path(args.transcript),
        platform=args.platform,
        cells_dir=Path(args.cells_dir) if args.cells_dir else None,
        evidence_dir=Path(args.evidence_dir) if args.evidence_dir else None,
        repo_root=Path(args.repo_root) if args.repo_root else None,
    )


if __name__ == "__main__":
    sys.exit(main())
