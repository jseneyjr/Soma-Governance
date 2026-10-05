#!/usr/bin/env python3
"""Backward-compatible forwarding shim for enzymes.sweep_session.

Delegates down to soma_core.sweep_session.
"""
from soma_core.sweep_session import (
    REWORK_INDICATORS,
    WASTE_SIGNALS,
    main,
    scan_transcript,
    to_session_metrics,
)

__all__ = [
    "REWORK_INDICATORS",
    "WASTE_SIGNALS",
    "main",
    "scan_transcript",
    "to_session_metrics",
]

if __name__ == "__main__":
    main()
