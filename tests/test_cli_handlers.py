"""Tests for soma_cli.handlers lifecycle, sentinels, telemetry, and sync modules."""
import io
from contextlib import redirect_stdout, redirect_stderr
import pytest

from soma_cli.handlers.lifecycle import (
    cli_cell_create,
    cli_cell_transfer,
    cli_cell_promote,
    cli_cell_demote,
    cli_cell_metamorphose,
    cli_cell_adapt,
    cli_cell_selection,
    cli_cell_crossover,
    cli_cell_fitness,
)
from soma_cli.handlers.sentinels import (
    cli_liveness_sentinel,
    cli_escalation_sentinel,
    cli_immune_sweep,
)
from soma_cli.handlers.telemetry import (
    cli_outcome_engine,
    cli_fitness_updater,
    cli_metrics_snapshot,
    cli_cell_quorum,
    cli_cell_coverage,
    cli_immune_grade,
)
from soma_cli.handlers.sync import (
    cli_team_sync,
    cli_hgt_ribosome,
    cli_post_session_hook,
)
import soma_cli.handlers as handlers


def _run_help(fn, *args, **kwargs) -> bool:
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        try:
            ret = fn(*args, **kwargs)
            return ret == 0
        except SystemExit as exc:
            return exc.code == 0


def test_handlers_package_exports():
    """Verify all lifecycle, sentinels, telemetry, and sync handlers are exported."""
    expected = [
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
    for name in expected:
        assert hasattr(handlers, name), f"Missing export: {name}"
        assert callable(getattr(handlers, name))


def test_lifecycle_handlers_help_invocations():
    """Verify lifecycle CLI handlers run cleanly on --help."""
    assert _run_help(cli_cell_create, ["--help"])
    assert _run_help(cli_cell_transfer, ["--help"])
    assert _run_help(cli_cell_promote, ["--help"])
    assert _run_help(cli_cell_demote, ["--help"])
    assert _run_help(cli_cell_metamorphose, ["--help"])
    assert _run_help(cli_cell_adapt, ["--help"])
    assert _run_help(cli_cell_selection, ["--help"])
    assert _run_help(cli_cell_crossover, ["--help"])
    assert _run_help(cli_cell_fitness, ["--help"])


def test_sentinels_handlers_invocations():
    """Verify sentinels CLI handlers run cleanly."""
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        assert cli_liveness_sentinel([]) == 0
        assert cli_escalation_sentinel(["README.md"]) == 0
        assert cli_immune_sweep(["--active-only"]) == 0


def test_telemetry_handlers_help_invocations():
    """Verify telemetry CLI handlers run cleanly on --help."""
    assert _run_help(cli_outcome_engine, ["--help"])
    assert _run_help(cli_fitness_updater, ["--help"])
    assert _run_help(cli_metrics_snapshot, ["--help"])
    assert _run_help(cli_cell_quorum, ["--help"])
    assert _run_help(cli_cell_coverage, ["--help"])
    assert _run_help(cli_immune_grade, ["--help"])


def test_sync_handlers_help_invocations():
    """Verify sync CLI handlers run cleanly on --help."""
    assert _run_help(cli_team_sync, ["--help"])
    assert _run_help(cli_hgt_ribosome, ["--help"])
    assert _run_help(cli_post_session_hook, ["--help"])
