"""Fitness updater: extract session evidence and update cell fitness data.

Reads an agent session transcript (JSONL), identifies which files were modified,
matches those files against cell target_paths globs, and appends fitness records
to .soma/evidence/fitness.jsonl.

Usage:
    python3 enzymes/fitness_updater.py <transcript_path> [--platform NAME] [--cells-dir DIR] [--evidence-dir DIR] [--repo-root DIR]
"""

import json
import os
import sys
import fnmatch
try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment]  # Windows fallback
from datetime import datetime, timezone
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from soma_sdk.cells import parse_cell_file


# Platform-specific transcript format configs.
# Each platform defines: write tool names, arg key variants, target file keys,
# and directory names to skip when resolving conversation ID from path.
PLATFORMS = {
    "antigravity": {
        "write_tools": {"write_to_file", "replace_file_content", "multi_replace_file_content"},
        "target_file_keys": ["TargetFile"],
        "args_keys": ["arguments", "args"],
        "id_skip_dirs": {"logs", ".system_generated"},
    },
    "claude": {
        "write_tools": {"write_to_file", "edit_file", "create_file"},
        "target_file_keys": ["path", "file_path", "TargetFile"],
        "args_keys": ["arguments", "args", "input"],
        "id_skip_dirs": {"logs"},
    },
}

# Generic fallback: union of all known write tools and arg keys
PLATFORMS["generic"] = {
    "write_tools": PLATFORMS["antigravity"]["write_tools"] | PLATFORMS["claude"]["write_tools"],
    "target_file_keys": list(set(PLATFORMS["antigravity"]["target_file_keys"] + PLATFORMS["claude"]["target_file_keys"])),
    "args_keys": list(set(PLATFORMS["antigravity"]["args_keys"] + PLATFORMS["claude"]["args_keys"])),
    "id_skip_dirs": PLATFORMS["antigravity"]["id_skip_dirs"] | PLATFORMS["claude"]["id_skip_dirs"],
}

DEFAULT_PLATFORM = "antigravity"


def _get_platform_config(platform=None):
    """Get platform config by name, defaulting to DEFAULT_PLATFORM.
    Falls back to 'generic' for unknown platforms."""
    name = platform or DEFAULT_PLATFORM
    if name not in PLATFORMS:
        import sys
        print(f"Warning: unknown platform '{name}', using generic config", file=sys.stderr)
        return PLATFORMS["generic"]
    return PLATFORMS[name]


def detect_platform(transcript_path):
    """Auto-detect platform by probing transcript for known tool names.

    Returns the platform name string, or DEFAULT_PLATFORM if no match.
    """
    transcript_path = Path(transcript_path)
    if not transcript_path.exists():
        return DEFAULT_PLATFORM

    # Build reverse lookup: tool_name → platform
    # Skip 'generic' (it's a fallback, not detectable) and prefer
    # more specific platforms by iterating them first
    tool_to_platform = {}
    for name, config in PLATFORMS.items():
        if name == "generic":
            continue
        for tool in config["write_tools"]:
            # Don't overwrite — first registered platform wins
            if tool not in tool_to_platform:
                tool_to_platform[tool] = name

    try:
        for line in transcript_path.open(encoding="utf-8"):
            if not line.strip():
                continue
            try:
                step = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            for tc in step.get("tool_calls", []):
                tool_name = tc.get("name", "")
                if tool_name in tool_to_platform:
                    return tool_to_platform[tool_name]
    except Exception:
        pass

    return DEFAULT_PLATFORM


def resolve_transcript_id(transcript_path, platform=None):
    """Extract a session/conversation ID from the transcript file path.

    Walks up from the transcript file, skipping platform-specific directory
    names (e.g. 'logs', '.system_generated' for Antigravity).
    """
    config = _get_platform_config(platform)
    candidate = Path(transcript_path).resolve().parent
    while candidate.name in config["id_skip_dirs"]:
        candidate = candidate.parent
    return candidate.name


def extract_modified_files(transcript_path, platform=None):
    """Extract absolute file paths modified by write tool calls in a transcript.

    Args:
        transcript_path: Path to a transcript.jsonl file.
        platform: Platform name (auto-detected if None).

    Returns:
        set[str]: Absolute paths of files modified during the session.
    """
    transcript_path = Path(transcript_path)
    if not transcript_path.exists():
        return set()

    config = _get_platform_config(platform)
    write_tools = config["write_tools"]
    args_keys = config["args_keys"]
    target_file_keys = config["target_file_keys"]

    modified = set()
    try:
        text = transcript_path.read_text(encoding="utf-8")
    except Exception:
        return set()

    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            step = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue  # Skip malformed lines

        for tc in step.get("tool_calls", []):
            tool_name = tc.get("name", "")
            if tool_name not in write_tools:
                continue
            # Try each known args key
            args = {}
            for key in args_keys:
                args = tc.get(key) or args
                if args:
                    break
            # Try each known target file key
            if not isinstance(args, dict):
                continue
            for tf_key in target_file_keys:
                target = args.get(tf_key, "")
                if isinstance(target, str):
                    target = target.strip('"').strip("'")
                if target:
                    modified.add(target)

    return modified


def match_cells(modified_files, cells_dir, repo_root=""):
    """Match modified files against cell target_paths globs.

    Args:
        modified_files: Set of absolute file paths.
        cells_dir: Path to the cells directory (.soma/cells/).
        repo_root: Absolute path to the repo root (for relativizing paths).

    Returns:
        list[dict]: Each dict has cell_id, cell_path, matched_files.
    """
    cells_dir = Path(cells_dir)
    if not cells_dir.exists():
        return []

    if not modified_files:
        return []

    # Relativize modified files against repo root
    rel_modified = set()
    for abs_path in modified_files:
        if repo_root and abs_path.startswith(repo_root):
            rel = abs_path[len(repo_root):].lstrip("/")
            rel_modified.add(rel)
        else:
            rel_modified.add(abs_path)

    results = []
    for md_file in cells_dir.rglob("*.md"):
        if md_file.name == "README.md":
            continue
        try:
            fm, _body = parse_cell_file(str(md_file))
        except Exception:
            continue

        cell_id = fm.get("id", md_file.stem)
        target_paths = fm.get("target_paths", [])
        if not isinstance(target_paths, list) or not target_paths:
            continue

        matched = set()
        for rel_file in rel_modified:
            for pattern in target_paths:
                if fnmatch.fnmatch(rel_file, pattern):
                    matched.add(rel_file)
                    break

        if matched:
            rel_cell = str(md_file.relative_to(cells_dir))
            results.append({
                "cell_id": cell_id,
                "cell_path": rel_cell,
                "matched_files": sorted(matched),
            })

    return results


def update_fitness(triggered_cells, transcript_id, evidence_dir):
    """Append fitness records to fitness.jsonl with idempotency.

    Args:
        triggered_cells: List of dicts from match_cells().
        transcript_id: Unique identifier for the session.
        evidence_dir: Path to .soma/evidence/.
    """
    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    ledger_path = evidence_dir / "sessions_processed.jsonl"
    fitness_path = evidence_dir / "fitness.jsonl"
    lock_path = evidence_dir / ".fitness.lock"

    # Unified lock: protects idempotency check + both file writes
    # as a single atomic transaction to prevent TOCTOU races and
    # partial writes on crash between fitness.jsonl and ledger.
    lock_fd = open(lock_path, "a", encoding="utf-8")
    try:
        if fcntl is not None:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)

        # Idempotency check (under lock to prevent TOCTOU)
        if ledger_path.exists():
            for line in ledger_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    if record.get("transcript_id") == transcript_id:
                        return  # Already processed
                except (json.JSONDecodeError, ValueError):
                    continue

        now = datetime.now(timezone.utc).isoformat()

        # Append trigger signals via unified telemetry
        if triggered_cells:
            try:
                from soma_sdk.telemetry import append_signal
                workspace = str(evidence_dir.parent.parent)  # .soma/evidence → repo root
                for cell in triggered_cells:
                    append_signal(
                        workspace=workspace,
                        cell_name=cell["cell_id"],
                        signal_type='trigger',
                        source='session',
                        metadata={
                            'transcript_id': transcript_id,
                            'matched_files': cell.get("matched_files", []),
                        },
                    )
            except ImportError:
                # Fallback: write directly if telemetry module unavailable
                fitness_path = evidence_dir / "fitness.jsonl"
                with open(fitness_path, "a", encoding="utf-8") as f:
                    for cell in triggered_cells:
                        record = {
                            "cell_id": cell["cell_id"],
                            "transcript_id": transcript_id,
                            "triggered_at": now,
                            "matched_files": cell.get("matched_files", []),
                        }
                        f.write(json.dumps(record) + "\n")

        # Record session as processed (same lock scope as fitness write)
        with open(ledger_path, "a", encoding="utf-8") as f:
            ledger_record = {
                "transcript_id": transcript_id,
                "processed_at": now,
                "cells_triggered": len(triggered_cells),
            }
            f.write(json.dumps(ledger_record) + "\n")

    finally:
        if fcntl is not None:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


def main():
    """CLI entrypoint."""
    import argparse

    parser = argparse.ArgumentParser(description="Update cell fitness from session transcript")
    parser.add_argument("transcript", help="Path to transcript.jsonl")
    parser.add_argument("--platform", default=None,
                        help=f"Platform name (auto-detected if omitted). Known: {list(PLATFORMS.keys())}")
    parser.add_argument("--cells-dir", default=None, help="Path to cells directory")
    parser.add_argument("--evidence-dir", default=None, help="Path to evidence directory")
    parser.add_argument("--repo-root", default=None, help="Repo root for relativizing paths")
    args = parser.parse_args()

    # Resolve defaults relative to script location
    script_dir = Path(__file__).parent.parent
    cells_dir = Path(args.cells_dir) if args.cells_dir else script_dir / ".soma" / "cells"
    evidence_dir = Path(args.evidence_dir) if args.evidence_dir else script_dir / ".soma" / "evidence"
    repo_root = args.repo_root or str(script_dir)

    transcript = Path(args.transcript)
    platform = args.platform or detect_platform(transcript)
    transcript_id = resolve_transcript_id(transcript, platform)

    print(f"Processing transcript: {transcript}")
    print(f"  Platform: {platform}")
    modified = extract_modified_files(transcript, platform=platform)
    print(f"  Modified files: {len(modified)}")

    triggered = match_cells(modified, cells_dir, repo_root=repo_root)
    print(f"  Cells triggered: {len(triggered)}")
    for t in triggered:
        print(f"    - {t['cell_id']} ({len(t['matched_files'])} files)")

    update_fitness(triggered, transcript_id, evidence_dir)
    print(f"  Fitness updated: {evidence_dir / 'fitness.jsonl'}")

    # Sync JSONL evidence → cell frontmatter
    try:
        from soma_cli.sync import aggregate_evidence, sync_frontmatter
        counts = aggregate_evidence(str(evidence_dir))
        if counts:
            changes = sync_frontmatter(str(cells_dir), counts)
            if changes:
                print(f"  Frontmatter synced: {len(changes)} cells updated")
    except ImportError:
        pass  # soma_cli not installed — skip frontmatter sync


if __name__ == "__main__":
    main()
