"""Evidence collector — correlates rule compliance with session outcomes.

Scans Antigravity/Claude transcript JSONL files for tool-call patterns
that indicate compliance or violation of governance rules. Aggregates
per-rule statistics for the evidence enrichment pipeline.

Security invariant: NEVER stores source code, file paths, or diff content.
Only aggregate integer metrics and ratios are produced.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

# Minimum path depth to count as a valid "read" for compliance.
# Rejects root ("/") and near-root ("/repo") reads that would
# trivially match every write.
_MIN_READ_DEPTH = 2


# ── Tool-call pattern definitions per rule ──────────────────────────

# Maps rule_id → detector function name
# Each detector receives a list of parsed transcript steps and returns
# a dict with compliant_count and non_compliant_count.

WRITE_TOOLS = frozenset({
    "replace_file_content",
    "multi_replace_file_content",
})

READ_TOOLS = frozenset({
    "view_file",
    "grep_search",
})


def _extract_tool_calls(steps: list[dict]) -> list[dict]:
    """Flatten all tool calls from transcript steps into a sequential list.

    Each returned dict has: step_index, tool_name, and a sanitized args
    dict containing only the keys needed for pattern detection (file paths
    only, no content).
    """
    calls = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        for tc in step.get("tool_calls", []):
            if not isinstance(tc, dict):
                continue
            name = tc.get("name", "")
            args = tc.get("args", {})
            if not isinstance(args, dict):
                continue
            # Extract ONLY the file path — never content
            raw_path = (
                args.get("TargetFile")
                or args.get("AbsolutePath")
                or args.get("SearchPath")
            )
            # Strip surrounding quotes from serialized arguments
            target_file = _sanitize_path(raw_path) if raw_path else None
            calls.append({
                "step_index": step.get("step_index", 0),
                "tool_name": name,
                "target_file": target_file,
            })
    return calls


def _check_read_before_write(steps: list[dict]) -> dict:
    """Check read-before-write compliance.

    For each replace_file_content / multi_replace_file_content call,
    check whether the same file was read (view_file / grep_search)
    at any prior point in the session.

    Uses a session-level "files read" set instead of a fixed lookback
    window, preventing false violations on multi-edit sessions where
    intermediate operations push the initial read out of range.

    write_to_file (new file creation) is excluded — the rule applies
    only to modifications of existing files.
    """
    calls = _extract_tool_calls(steps)
    compliant = 0
    non_compliant = 0

    # Session-level set of files that have been read
    files_read: set[str] = set()

    for call in calls:
        target = call["target_file"]
        if not target:
            continue

        # Track reads
        if call["tool_name"] in READ_TOOLS:
            files_read.add(target)
            continue

        # Check writes
        if call["tool_name"] not in WRITE_TOOLS:
            continue

        # Check if any prior read covers this write target
        found_read = any(
            _paths_match(read_path, target)
            for read_path in files_read
        )

        if found_read:
            compliant += 1
        else:
            non_compliant += 1

    return {"compliant_count": compliant, "non_compliant_count": non_compliant}


def _paths_match(read_path: str, write_path: str) -> bool:
    """Check if a read path covers a write path.

    Handles cases where grep_search uses a directory path that is a
    parent of the written file, or an exact file match.

    Security: Rejects root or near-root reads that would trivially
    match every write. Normalizes paths to handle relative/absolute
    mismatches.
    """
    # Normalize both paths to resolve .., ., and trailing slashes
    rp = os.path.normpath(read_path)
    wp = os.path.normpath(write_path)

    # Exact match after normalization
    if rp == wp:
        return True

    # Reject root or near-root reads (too broad to be meaningful)
    # Count path components: "/" has 0, "/repo" has 1, "/repo/src" has 2
    rp_depth = len(Path(rp).parts) - (1 if rp.startswith("/") else 0)
    if rp_depth < _MIN_READ_DEPTH:
        return False

    # Directory ancestor check: read_path is a parent of write_path
    if wp.startswith(rp + os.sep):
        return True

    return False


# Registry of rule detectors
_DETECTORS: dict[str, Any] = {
    "read-before-write": _check_read_before_write,
}


# ── Public API ──────────────────────────────────────────────────────


def check_compliance(transcript_path: Path | str, rule_id: str) -> dict:
    """Check a transcript for compliance with a specific rule.

    Args:
        transcript_path: Path to a transcript.jsonl file (str or Path).
        rule_id: The rule to check (must be in _DETECTORS).

    Returns:
        dict with 'compliant_count' and 'non_compliant_count' (integers).
    """
    transcript_path = Path(transcript_path)
    detector = _DETECTORS.get(rule_id)
    if detector is None:
        return {"compliant_count": 0, "non_compliant_count": 0}

    steps = _parse_transcript(transcript_path)
    return detector(steps)


def aggregate_evidence(observations: list[dict]) -> dict:
    """Aggregate per-session compliance observations into evidence stats.

    Args:
        observations: List of dicts, each with:
            - rule_id: str
            - compliant: bool
            - session_steps: int
            - session_fpsr: float (0.0 - 1.0)

    Returns:
        dict keyed by rule_id, each value a dict with:
            samples, compliant_fpsr, non_compliant_fpsr,
            compliant_avg_steps, non_compliant_avg_steps,
            rework_multiplier, confidence
    """
    if not observations:
        return {}

    # Group by rule_id
    by_rule: dict[str, list[dict]] = defaultdict(list)
    for obs in observations:
        by_rule[obs["rule_id"]].append(obs)

    evidence = {}
    for rule_id, obs_list in by_rule.items():
        compliant = [o for o in obs_list if o["compliant"]]
        non_compliant = [o for o in obs_list if not o["compliant"]]

        c_fpsr = (_mean([o["session_fpsr"] for o in compliant])
                  if compliant else None)
        nc_fpsr = (_mean([o["session_fpsr"] for o in non_compliant])
                   if non_compliant else None)
        c_steps = (_mean([o["session_steps"] for o in compliant])
                   if compliant else None)
        nc_steps = (_mean([o["session_steps"] for o in non_compliant])
                    if non_compliant else None)

        # Rework multiplier: how many more steps non-compliant sessions take
        if c_steps and nc_steps and c_steps > 0:
            rework = nc_steps / c_steps
        else:
            rework = None

        # Confidence based on sample count
        n = len(obs_list)
        if n >= 10:
            confidence = "high"
        elif n >= 5:
            confidence = "medium"
        else:
            confidence = "low"

        evidence[rule_id] = {
            "samples": n,
            "compliant_fpsr": c_fpsr if c_fpsr is not None else 0,
            "non_compliant_fpsr": nc_fpsr if nc_fpsr is not None else 0,
            "compliant_avg_steps": c_steps if c_steps is not None else 0,
            "non_compliant_avg_steps": nc_steps if nc_steps is not None else 0,
            "rework_multiplier": rework if rework is not None else 0,
            "confidence": confidence,
        }

    return evidence


# ── Internal helpers ────────────────────────────────────────────────


def _parse_transcript(path: Path) -> list[dict]:
    """Parse a JSONL transcript file into a list of step dicts.

    Streams line-by-line to handle large transcripts (>50MB)
    without loading the entire file into memory.
    """
    steps = []
    if not path.exists():
        return steps
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    steps.append(parsed)
            except json.JSONDecodeError:
                continue
    return steps


def _sanitize_path(raw: str) -> str:
    """Strip surrounding quotes and whitespace from a tool argument path."""
    return raw.strip().strip('"').strip("'").strip()


def _mean(values: list[float]) -> float:
    """Compute arithmetic mean of a non-empty list."""
    return sum(values) / len(values)
