"""Backward-compatible forwarding shim for enzymes.evidence_collector.

Delegates down to soma_core.evidence_collector.
"""
from soma_core.evidence_collector import (
    READ_TOOLS,
    WRITE_TOOLS,
    aggregate_evidence,
    build_observation,
    check_compliance,
)

__all__ = [
    "READ_TOOLS",
    "WRITE_TOOLS",
    "aggregate_evidence",
    "build_observation",
    "check_compliance",
]
