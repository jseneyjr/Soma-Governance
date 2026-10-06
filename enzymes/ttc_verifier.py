#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.ttc_verifier.

Delegates canonical verification and arbitration logic to soma_core.arbitration.
Preserves explicit symbol re-exports and CLI execution contract.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from soma_core.arbitration import (
    ESCALATING_PROTOCOLS,
    ESCALATION_PROTOCOLS,
    ORACLE_FAIL_OPEN_MARKERS,
    ORACLE_NO_RULES_MARKER,
    PROTOCOL_UNKNOWN,
    SENTINEL_TIMEOUT,
    TTCVerifier,
    VERDICT_APPROVED,
    VERDICT_BLOCKED,
    VERDICT_ESCALATE,
    VERDICT_REJECTED,
    get_escalation_protocol,
    self_test_verifier as _self_test,
    soma_propose_change,
)
from soma_core.workspace import (
    confine_path as _contain_path,
    resolve_workspace,
)

__all__ = [
    "ESCALATION_PROTOCOLS",
    "ESCALATING_PROTOCOLS",
    "PROTOCOL_UNKNOWN",
    "SENTINEL_TIMEOUT",
    "ORACLE_FAIL_OPEN_MARKERS",
    "ORACLE_NO_RULES_MARKER",
    "VERDICT_APPROVED",
    "VERDICT_REJECTED",
    "VERDICT_BLOCKED",
    "VERDICT_ESCALATE",
    "TTCVerifier",
    "soma_propose_change",
    "resolve_workspace",
    "get_escalation_protocol",
    "_contain_path",
    "_self_test",
    "main",
]


def __getattr__(name: str):
    """Fallback delegation for dynamically queried attributes."""
    import soma_core.arbitration as _arb
    if hasattr(_arb, name):
        return getattr(_arb, name)
    import soma_core.workspace as _ws
    return getattr(_ws, name)


def main(argv: list[str] | None = None) -> int:
    """Run non-destructive self test."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    return _self_test()


if __name__ == "__main__":
    sys.exit(main())
