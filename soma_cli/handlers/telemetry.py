"""Soma CLI handlers for telemetry, metrics, and scoring operations."""
from __future__ import annotations

from typing import Any, List, Optional

import soma_core.telemetry as _telemetry


def cli_outcome_engine(argv: Optional[List[str]] = None, mod: Any = None) -> int:
    """CLI handler for recording session outcomes."""
    return _telemetry.cli_outcome_engine(argv, mod=mod)


def cli_fitness_updater(argv: Optional[List[str]] = None) -> int:
    """CLI handler for updating cell fitness scores."""
    return _telemetry.cli_fitness_updater(argv)


def cli_metrics_snapshot(argv: Optional[List[str]] = None) -> int:
    """CLI handler for creating metrics snapshots."""
    return _telemetry.cli_metrics_snapshot(argv)


def cli_cell_quorum(argv: Optional[List[str]] = None) -> int:
    """CLI handler for evaluating quorum on cell fitness."""
    return _telemetry.cli_cell_quorum(argv)


def cli_cell_coverage(argv: Optional[List[str]] = None, workspace: Optional[str] = None) -> int:
    """CLI handler for checking cell rule coverage."""
    return _telemetry.cli_cell_coverage(argv, workspace=workspace)


def cli_immune_grade(argv: Optional[List[str]] = None, workspace: Optional[str] = None) -> int:
    """CLI handler for computing immune health grades."""
    return _telemetry.cli_immune_grade(argv, workspace=workspace)
