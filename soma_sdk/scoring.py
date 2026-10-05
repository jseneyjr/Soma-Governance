"""Unified scoring module for soma-governance (SDK facade).

DEPRECATED: Canonical scoring logic now resides in soma_core.scoring.
This module re-exports all scoring functions for backward compatibility.
"""
from __future__ import annotations

from soma_core.scoring import (
    _to_num,
    _wilson_interval,
    bayesian_posterior,
    bayesian_score,
    compute_cell_fitness,
    laplace_score,
    wilson_lower_bound,
)

__all__ = [
    "_wilson_interval",
    "_to_num",
    "bayesian_posterior",
    "wilson_lower_bound",
    "laplace_score",
    "bayesian_score",
    "compute_cell_fitness",
]
