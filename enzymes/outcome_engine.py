#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.outcome_engine.

Delegates canonical outcome reflection, test capture, and credit weights to soma_core.telemetry.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from soma_core.telemetry import (
    VERIFY_TIMEOUT,
    append_fitness_log,
    capture_build_outcome,
    capture_git_signals,
    capture_human_insight_signals,
    capture_mcp_outcomes,
    capture_test_outcome,
    cli_outcome_engine,
    commit_insight_cursor,
    compute_credit_weights,
    compute_fitness_signals,
    detect_test_runner,
    match_cells_to_changes,
    read_human_insight_signals,
    run_outcome_engine,
    to_fraction,
    update_cell_fitness,
    _get_changed_files,
    _read_insight_cursor,
    _run_verify,
)

__all__ = [
    "VERIFY_TIMEOUT",
    "detect_test_runner",
    "capture_test_outcome",
    "capture_build_outcome",
    "capture_git_signals",
    "capture_mcp_outcomes",
    "commit_insight_cursor",
    "capture_human_insight_signals",
    "read_human_insight_signals",
    "match_cells_to_changes",
    "to_fraction",
    "compute_credit_weights",
    "compute_fitness_signals",
    "update_cell_fitness",
    "append_fitness_log",
    "run_outcome_engine",
    "_get_changed_files",
    "_read_insight_cursor",
    "_run_verify",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.telemetry as _tel
    return getattr(_tel, name)


def main(*args, **kwargs) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return run_outcome_engine(mod=sys.modules[__name__])


if __name__ == "__main__":
    sys.exit(main())
