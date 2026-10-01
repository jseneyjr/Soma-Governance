"""Shared Bayesian scoring utility for Soma v0.30.

Single source of truth for the Laplace-smoothed posterior mean.
All enzymes and the JIT engine should import from here instead of
re-implementing the formula inline.
"""
from __future__ import annotations


def bayesian_score(tp: int, triggers: int, impact_weight: float = 1.0) -> float:
    """Laplace-smoothed Bayesian posterior mean: Beta(tp+1, fp+1).

    Returns (tp + 1) / (triggers + 2) * impact_weight.

    Properties:
    - Zero triggers → 0.5 * impact_weight (maximally uncertain)
    - Converges to raw tp/triggers as sample size grows
    - Always in [0, impact_weight] when tp <= triggers
    """
    return ((int(tp) + 1) / (int(triggers) + 2)) * float(impact_weight)
