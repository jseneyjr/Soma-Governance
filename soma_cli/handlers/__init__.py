"""Soma CLI handlers for lifecycle, sentinels, telemetry, and synchronization."""
from soma_cli.handlers.lifecycle import (
    cli_cell_adapt,
    cli_cell_create,
    cli_cell_crossover,
    cli_cell_demote,
    cli_cell_fitness,
    cli_cell_metamorphose,
    cli_cell_promote,
    cli_cell_selection,
    cli_cell_transfer,
)
from soma_cli.handlers.sentinels import (
    cli_escalation_sentinel,
    cli_immune_sweep,
    cli_liveness_sentinel,
)

__all__ = [
    "cli_cell_create",
    "cli_cell_transfer",
    "cli_cell_promote",
    "cli_cell_demote",
    "cli_cell_metamorphose",
    "cli_cell_adapt",
    "cli_cell_selection",
    "cli_cell_crossover",
    "cli_cell_fitness",
    "cli_liveness_sentinel",
    "cli_escalation_sentinel",
    "cli_immune_sweep",
]
