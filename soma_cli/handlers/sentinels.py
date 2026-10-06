"""Soma CLI handlers for sentinel monitoring and sweeps."""
from __future__ import annotations

from typing import List, Optional

import soma_core.sync as _sync


def cli_liveness_sentinel(argv: Optional[List[str]] = None) -> int:
    """CLI handler for subagent liveness monitoring."""
    return _sync.cli_liveness_sentinel(argv)


def cli_escalation_sentinel(argv: Optional[List[str]] = None) -> int:
    """CLI handler for zero-token review protocol escalation."""
    return _sync.cli_escalation_sentinel(argv)


def cli_immune_sweep(argv: Optional[List[str]] = None) -> int:
    """CLI handler for governance sweeps across sessions."""
    return _sync.cli_immune_sweep(argv)
