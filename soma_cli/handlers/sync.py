"""Soma CLI handlers for synchronization, ribosome, and session hooks."""
from __future__ import annotations

from typing import List, Optional

import soma_core.sync as _sync


def cli_team_sync(argv: Optional[List[str]] = None) -> int:
    """CLI handler for team rule synchronization."""
    return _sync.cli_team_sync(argv)


def cli_hgt_ribosome(argv: Optional[List[str]] = None) -> int:
    """CLI handler for horizontal gene transfer ribosome execution."""
    return _sync.cli_hgt_ribosome(argv)


def cli_post_session_hook(argv: Optional[List[str]] = None) -> int:
    """CLI handler for post-session governance processing."""
    return _sync.cli_post_session_hook(argv)
