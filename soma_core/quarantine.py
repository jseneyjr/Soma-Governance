"""soma_core.quarantine — Self-healing quarantine for corrupted governance state.

Automatically isolates damaged YAML cells or unparseable JSONL files to prevent
fatal crashes, logging diagnostic telemetry and preserving system uptime.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Tuple

import yaml

from soma_core.frontmatter import parse_frontmatter

QUARANTINE_DIR = "quarantine"
QUARANTINE_LOG = "quarantine_log.jsonl"


def _resolve_workspace(file_path: Path, workspace: Optional[Path | str] = None) -> Path:
    if workspace:
        return Path(workspace).resolve()
    # Search upward for .soma or genome/
    curr = file_path.resolve().parent
    for _ in range(5):
        if (curr / ".soma").exists() or (curr / "genome").exists():
            return curr
        if curr.parent == curr:
            break
        curr = curr.parent
    return file_path.resolve().parent


def quarantine_file(
    file_path: Path,
    reason: str,
    workspace: Optional[Path | str] = None,
) -> Path:
    """Isolate a damaged file into .soma/quarantine/ and record diagnostics.

    Returns:
        The new quarantined file path.
    """
    path = Path(file_path).resolve()
    ws = _resolve_workspace(path, workspace)
    q_dir = ws / ".soma" / QUARANTINE_DIR
    q_dir.mkdir(parents=True, exist_ok=True)

    timestamp = int(time.time())
    dest_name = f"{path.stem}.{timestamp}.corrupt"
    dest_path = q_dir / dest_name

    # Copy / move file into quarantine
    shutil.copy2(str(path), str(dest_path))
    try:
        path.unlink()
    except OSError:
        pass

    # Log structured incident entry
    log_file = q_dir / QUARANTINE_LOG
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "original_path": str(path),
        "quarantined_file": dest_name,
        "reason": str(reason),
    }
    with open(log_file, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(log_entry) + "\n")

    return dest_path


def safe_parse_cell_file(
    cell_path: Path,
    workspace: Optional[Path | str] = None,
) -> Tuple[dict[str, Any], str, str]:
    """Parse cell frontmatter and body, automatically quarantining corrupt files.

    Returns:
        (metadata, body, status) where status is 'ok', 'quarantined', or 'missing'.
    """
    path = Path(cell_path)
    if not path.exists():
        return {}, "", "missing"

    try:
        content = path.read_text(encoding="utf-8")
        metadata = parse_frontmatter(content)
        if metadata is None:
            quarantine_file(path, reason="unparseable_or_unclosed_frontmatter", workspace=workspace)
            return {}, "", "quarantined"
        end = content.find("---", 3)
        body = content[end + 3:].strip() if end != -1 else content
        return metadata, body, "ok"
    except Exception as exc:
        quarantine_file(path, reason=f"frontmatter_parse_error: {exc}", workspace=workspace)
        return {}, "", "quarantined"


def safe_read_jsonl(
    file_path: Path,
    workspace: Optional[Path | str] = None,
) -> Tuple[list[dict[str, Any]], str]:
    """Read a JSONL file, automatically quarantining files with severe corruption.

    Returns:
        (records, status) where status is 'ok', 'quarantined', or 'missing'.
    """
    path = Path(file_path)
    if not path.exists():
        return [], "missing"

    records = []
    has_valid_json = False
    invalid_lines = 0

    try:
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()
        for idx, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
                has_valid_json = True
            except json.JSONDecodeError:
                invalid_lines += 1
    except (UnicodeDecodeError, Exception) as exc:
        quarantine_file(path, reason=f"unreadable_binary: {exc}", workspace=workspace)
        return [], "quarantined"

    # If file had content but zero valid JSON entries, quarantine it
    if lines and not has_valid_json:
        quarantine_file(path, reason="corrupted_non_jsonl", workspace=workspace)
        return [], "quarantined"

    return records, "ok"
