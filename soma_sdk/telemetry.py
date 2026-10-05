"""Unified telemetry signal writer for the Soma evidence pipeline (SDK facade).

Delegates all atomic evidence logging, process-level locking, idempotency,
and epoch generation tracking to the canonical single-authority implementation
in soma_core.telemetry.
"""
from __future__ import annotations

from soma_core.telemetry import (
    DEFAULT_GENERATION,
    EPOCH_FILENAME,
    LOCK_FILENAME,
    SIGNALS_FILENAME,
    VALID_SIGNAL_TYPES,
    VALID_SOURCES,
    EventConflictError,
    StaleGenerationError,
    append_signal,
    append_signals,
    compute_event_id,
    compute_payload_digest,
    current_generation,
    evidence_lock,
    increment_generation,
    read_generation,
    read_signals,
)

__all__ = [
    "VALID_SIGNAL_TYPES",
    "VALID_SOURCES",
    "SIGNALS_FILENAME",
    "LOCK_FILENAME",
    "EPOCH_FILENAME",
    "DEFAULT_GENERATION",
    "EventConflictError",
    "StaleGenerationError",
    "evidence_lock",
    "read_generation",
    "current_generation",
    "increment_generation",
    "compute_payload_digest",
    "compute_event_id",
    "append_signal",
    "append_signals",
    "read_signals",
]
