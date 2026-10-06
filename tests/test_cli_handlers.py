"""Tests for soma_cli.handlers lifecycle and sentinels modules."""
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
    """Verify all lifecycle and sentinels handlers are exported from soma_cli.handlers."""
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
        # Empty payload shows usage and returns 0
        assert cli_liveness_sentinel([]) == 0
        assert cli_escalation_sentinel(["README.md"]) == 0
        assert cli_immune_sweep(["--active-only"]) == 0
