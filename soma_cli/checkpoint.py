"""soma checkpoint — deterministic quality checks (no LLM required).

Checks:
- Test file coverage for implementation files
- Hardcoded absolute paths (/home, /Users, /tmp)
- Assertion density in test files
- Cell fitness scores from .soma/evidence ledger
- Cell convention enforcement (frontmatter, type/dir match)
- Arbitration evidence (un-bypassable review gate)

Supports --pre-commit (warn mode), --strict, --json, --workspace flags.

All check implementations live in immune_system.verification.checkpoint_checks
to share logic with soma_mcp without copy-paste.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from immune_system.verification.checkpoint_checks import (
    CHECK_NAMES,
    run_all_checks,
)


def run_checkpoint(args: argparse.Namespace) -> int:
    """Run deterministic quality checkpoint on a workspace.

    Args:
        args: Parsed CLI arguments with workspace, pre_commit, strict, json.

    Returns:
        Exit code: 0 for pass, 1 for failures.
    """
    workspace = getattr(args, "workspace", None) or os.getcwd()
    root = Path(workspace)

    pre_commit = getattr(args, "pre_commit", False)
    strict = getattr(args, "strict", False)
    use_json = getattr(args, "json", False)

    # Validate workspace exists
    if not root.is_dir():
        msg = f"Error: workspace does not exist: {workspace}"
        if use_json:
            print(json.dumps({
                "status": "error",
                "passed": False,
                "checks": [],
                "issues": [{"check": "workspace", "message": msg}],
            }))
        else:
            print(msg, file=sys.stderr)
        return 1

    # Sync evidence → frontmatter so fitness data is fresh
    from soma_cli.sync import aggregate_evidence, sync_frontmatter
    evidence_dir = str(root / ".soma" / "evidence")
    cells_dir = str(root / ".soma" / "cells")
    counts = aggregate_evidence(evidence_dir)
    if counts:
        sync_frontmatter(cells_dir, counts)

    # Run all checks (from shared module)
    all_issues = run_all_checks(root)
    has_issues = len(all_issues) > 0

    # Determine exit code
    if has_issues:
        if pre_commit and not strict:
            exit_code = 0  # Warn mode
        else:
            exit_code = 1
    else:
        exit_code = 0

    # Output
    if use_json:
        output = {
            "status": "failed" if has_issues else "passed",
            "passed": not has_issues,
            "checks": CHECK_NAMES,
            "issues": all_issues,
        }
        print(json.dumps(output, indent=2))
    else:
        if has_issues:
            warn_label = "[WARN]" if (pre_commit and not strict) else "[FAIL]"
            for issue in all_issues:
                print(f"{warn_label} {issue['message']}")
        else:
            print("checkpoint: all checks passed")

    return exit_code
