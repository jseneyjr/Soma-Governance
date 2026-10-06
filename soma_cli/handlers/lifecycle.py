"""Soma CLI handlers for cell lifecycle operations."""
from __future__ import annotations

from typing import Optional

import soma_core.lifecycle as _lc


def cli_cell_create(argv: list[str] | None = None) -> int:
    """CLI handler for programmatic cell creation."""
    return _lc.cli_cell_create(argv)


def cli_cell_transfer(argv: list[str] | None = None) -> int:
    """CLI handler for transferring cells between projects."""
    return _lc.cli_cell_transfer(argv)


def cli_cell_promote(argv: list[str] | None = None, workspace: Optional[str] = None) -> int:
    """CLI handler for cell promotion evaluation and execution."""
    return _lc.cli_cell_promote(argv, workspace=workspace)


def cli_cell_demote(argv: list[str] | None = None) -> int:
    """CLI handler for cell demotion evaluation and execution."""
    return _lc.cli_cell_demote(argv)


def cli_cell_metamorphose(argv: list[str] | None = None) -> int:
    """CLI handler for cell metamorphosis."""
    return _lc.cli_cell_metamorphose(argv)


def cli_cell_adapt(argv: list[str] | None = None) -> int:
    """CLI handler for cell adaptation."""
    return _lc.cli_cell_adapt(argv)


def cli_cell_selection(argv: list[str] | None = None) -> int:
    """CLI handler for evolutionary cell selection."""
    return _lc.cli_cell_selection(argv)


def cli_cell_crossover(argv: list[str] | None = None) -> int:
    """CLI handler for cell crossover."""
    return _lc.cli_cell_crossover(argv)


def cli_cell_fitness(argv: list[str] | None = None, workspace: Optional[str] = None) -> int:
    """CLI handler for cell fitness calculation."""
    return _lc.cli_cell_fitness(argv, workspace=workspace)
