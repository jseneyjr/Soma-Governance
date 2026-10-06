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
from soma_cli.handlers.sync import (
    cli_hgt_ribosome,
    cli_post_session_hook,
    cli_team_sync,
)
from soma_cli.handlers.telemetry import (
    cli_cell_coverage,
    cli_cell_quorum,
    cli_fitness_updater,
    cli_immune_grade,
    cli_metrics_snapshot,
    cli_outcome_engine,
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
    "cli_outcome_engine",
    "cli_fitness_updater",
    "cli_metrics_snapshot",
    "cli_cell_quorum",
    "cli_cell_coverage",
    "cli_immune_grade",
    "cli_team_sync",
    "cli_hgt_ribosome",
    "cli_post_session_hook",
]
