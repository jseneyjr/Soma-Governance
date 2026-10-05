#!/usr/bin/env python3
"""export_logs.py: Conversation log exporter with secret scrubbing.

Exports conversation transcripts from ~/.gemini/antigravity/brain to
ai-conversation-logs repository.

Usage:
    python enzymes/export_logs.py [--brain-dir <dir>] [--repo-dir <dir>]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SECRET_PATTERNS = [
    (re.compile(r"GEMINI_API_KEY=[^\s]+"), "GEMINI_API_KEY=REDACTED"),
    (re.compile(r"AIzaSy[a-zA-Z0-9_-]{33}"), "AIzaSy_REDACTED"),
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "sk-REDACTED"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "ghp_REDACTED"),
    (re.compile(r"github_pat_[a-zA-Z0-9_]{20,}"), "github_pat_REDACTED"),
    (re.compile(r"Bearer [a-zA-Z0-9._-]{20,}"), "Bearer REDACTED"),
]


def scrub_secrets(text: str) -> str:
    """Scrub sensitive credentials from transcript text."""
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def export_logs(brain_dir: Path | None = None, repo_dir: Path | None = None, min_steps: int = 50) -> int:
    home = Path.home()
    b_dir = brain_dir or (home / ".gemini" / "antigravity" / "brain")
    r_dir = repo_dir or (home / ".gemini" / "antigravity" / "scratch" / "ai-conversation-logs")

    if not b_dir.is_dir():
        print(f"Brain dir not found: {b_dir}", file=sys.stderr)
        return 0

    r_dir.mkdir(parents=True, exist_ok=True)
    convs_dir = r_dir / "conversations"
    convs_dir.mkdir(parents=True, exist_ok=True)

    print("=== Conversation Log Export ===")
    print(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")

    # Find transcript files
    for transcript_path in b_dir.glob("*/.system_generated/logs/transcript.jsonl"):
        try:
            conv_id = transcript_path.parent.parent.parent.name
            lines = transcript_path.read_text(encoding="utf-8", errors="replace").splitlines()
            step_count = len(lines)
            if step_count < min_steps:
                continue

            # Detect primary (has USER_INPUT)
            is_primary = any('"type":"USER_INPUT"' in line for line in lines[:20])

            conv_target_dir = convs_dir / conv_id
            conv_target_dir.mkdir(parents=True, exist_ok=True)
            target_transcript = conv_target_dir / "transcript.jsonl"
            metadata_file = conv_target_dir / "metadata.json"

            scrubbed_content = scrub_secrets("\n".join(lines) + "\n")

            needs_update = True
            if target_transcript.is_file() and metadata_file.is_file():
                existing = target_transcript.read_text(encoding="utf-8", errors="replace")
                if existing == scrubbed_content:
                    needs_update = False

            if needs_update:
                target_transcript.write_text(scrubbed_content, encoding="utf-8")
                metadata = {
                    "conversation_id": conv_id,
                    "step_count": step_count,
                    "is_primary": is_primary,
                    "last_exported": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "transcript_bytes": len(scrubbed_content.encode("utf-8")),
                }
                metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
                print(f"Updated: {conv_id} ({step_count} steps, primary={is_primary})")

        except Exception as e:
            print(f"Warning: Failed to export {transcript_path}: {e}", file=sys.stderr)

    # Generate index.json
    index_entries = []
    for meta in convs_dir.glob("*/metadata.json"):
        try:
            index_entries.append(json.loads(meta.read_text(encoding="utf-8")))
        except Exception:
            pass
    (convs_dir / "index.json").write_text(json.dumps(index_entries, indent=2), encoding="utf-8")

    # Git operations if tracked
    if (r_dir / ".git").is_dir():
        try:
            status = subprocess.run(
                ["git", "status", "--porcelain", "conversations/", "governance/"],
                cwd=str(r_dir),
                capture_output=True,
                text=True,
            )
            if status.stdout.strip():
                subprocess.run(["git", "add", "conversations/", "governance/"], cwd=str(r_dir))
                msg = f"Log export: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} | {len(index_entries)} conversations"
                subprocess.run(["git", "commit", "-m", msg], cwd=str(r_dir), capture_output=True)
                subprocess.run(["git", "push"], cwd=str(r_dir), capture_output=True)
                print("Pushed to GitHub.")
            else:
                print("No changes to push.")
        except Exception as e:
            print(f"Warning: Git operations skipped: {e}", file=sys.stderr)

    print("Export complete.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export conversation logs")
    parser.add_argument("--brain-dir", dest="brain_dir", default="", help="Path to brain directory")
    parser.add_argument("--repo-dir", dest="repo_dir", default="", help="Path to logs repo")
    args = parser.parse_args(argv)

    b_dir = Path(args.brain_dir) if args.brain_dir else None
    r_dir = Path(args.repo_dir) if args.repo_dir else None
    return export_logs(brain_dir=b_dir, repo_dir=r_dir)


if __name__ == "__main__":
    sys.exit(main())
