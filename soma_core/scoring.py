"""Unified scoring module for soma-governance (Layer 0 Core).

Single source of truth for all fitness scoring math, Wilson intervals,
Laplace smoothing, and Bayesian posteriors.
Strictly zero-dependency: uses only Python standard library.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple, Union


def _wilson_interval(tp: int | float, total: int | float, z: float = 1.645) -> Tuple[float, float]:
    """Wilson score interval — correct for small n, no scipy needed.

    Args:
        tp: Number of successes (true positives).
        total: Total number of observations (tp + fp).
        z: Z-score for confidence level (1.645=90%, 1.96=95%, 2.576=99%).

    Returns:
        Tuple of (lower_bound, upper_bound).
    """
    total_num = max(0.0, _to_num(total))
    if total_num == 0.0:
        return 0.0, 1.0
    tp_num = max(0.0, min(_to_num(tp), total_num))
    p = tp_num / total_num
    denom = 1 + z ** 2 / total_num
    center = (p + z ** 2 / (2 * total_num)) / denom
    inside = (p * (1 - p) + z ** 2 / (4 * total_num)) / total_num
    spread = z * math.sqrt(max(0.0, inside)) / denom
    return max(0.0, center - spread), min(1.0, center + spread)


def _to_num(val: Any, default: float = 0.0) -> float:
    """Robustly convert arbitrary input to a finite non-negative float."""
    if val is None or isinstance(val, bool):
        return default
    if isinstance(val, (int, float)):
        return max(0.0, float(val)) if math.isfinite(val) else default
    if isinstance(val, str):
        val = val.strip()
        if '/' in val:
            try:
                from fractions import Fraction
                f = float(Fraction(val))
                return max(0.0, f) if math.isfinite(f) else default
            except Exception:
                return default
        try:
            f = float(val)
            return max(0.0, f) if math.isfinite(f) else default
        except Exception:
            return default
    return default


def bayesian_posterior(
    tp: int | float,
    fp: int | float,
    confidence: float = 0.90,
) -> Dict[str, Union[float, str, int]]:
    """Wilson-bounded fitness scoring with Jeffrey's prior.

    Uses the Wilson score interval for lower/upper bounds (correct for small n)
    and Jeffrey's Beta(0.5, 0.5) prior for the posterior mean.

    Args:
        tp: True positives.
        fp: False positives.
        confidence: Confidence level (0.90, 0.95, or 0.99).

    Returns:
        Dict with keys: mean, lower, lower_90, upper, upper_90, certainty, n.
    """
    tp_num = _to_num(tp)
    fp_num = _to_num(fp)
    a = tp_num + 0.5
    b = fp_num + 0.5
    mean = a / (a + b)
    z = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}.get(confidence, 1.645)
    total = tp_num + fp_num
    lower, upper = _wilson_interval(tp_num, total, z)
    lower = round(lower, 4)
    upper = round(upper, 4)
    return {
        'mean': round(mean, 4),
        'lower': lower,
        'lower_90': lower,    # Backward compat alias
        'upper': upper,
        'upper_90': upper,    # Backward compat alias
        'certainty': 'low' if total < 5 else 'medium' if total < 20 else 'high',
        'n': total if float(total).is_integer() else round(total, 2),
    }


def wilson_lower_bound(
    tp: int | float,
    triggers: int | float,
    z: float = 1.645,
) -> float:
    """Wilson score lower bound for success rate with confidence z.

    Args:
        tp: Number of successes (true positives).
        triggers: Total number of observations.
        z: Z-score for confidence level (default 1.645 for 90%).

    Returns:
        Lower bound strictly in [0.0, 1.0].
    """
    lower, _ = _wilson_interval(tp, triggers, z=z)
    return max(0.0, min(1.0, lower))


def laplace_score(
    tp: int | float,
    triggers: int | float,
    impact_weight: float = 1.0,
) -> float:
    """Laplace-smoothed point estimate: (tp+1)/(triggers+2) × impact.

    Args:
        tp: True positives.
        triggers: Total trigger count.
        impact_weight: Multiplicative weight for impact scoring.

    Returns:
        Smoothed score in [0, 1] × impact_weight.
    """
    weight = float(_to_num(impact_weight, default=1.0))
    tp_num = _to_num(tp)
    triggers_num = max(_to_num(triggers), tp_num)
    score = ((tp_num + 1.0) / (triggers_num + 2.0)) * weight
    return max(0.0, min(1.0 * weight, score)) if weight > 0 else 0.0


def bayesian_score(
    tp: int | float,
    triggers: int | float,
    impact_weight: float = 1.0,
) -> float:
    """DEPRECATED: Use bayesian_posterior() for new code.

    Legacy Laplace-smoothed point estimate.
    """
    return laplace_score(tp, triggers, impact_weight)


def compute_cell_fitness(cell: Dict[str, Any]) -> float:
    """Extract and compute fitness score from a cell dict.

    Canonical replacement for duplicate scoring across JIT engine and enzymes.
    """
    fitness = cell.get('fitness', '')
    impact_weight = cell.get('impact_weight', 1.0)
    try:
        impact_weight = float(impact_weight)
    except (ValueError, TypeError):
        impact_weight = 1.0

    if isinstance(fitness, dict):
        score = fitness.get('score')
        tp = fitness.get('true_positives', 0)
        triggers = fitness.get('triggers', 0)
        try:
            tp_f, trig_f = float(tp), float(triggers)
            if trig_f > 0:
                return laplace_score(tp_f, trig_f, impact_weight)
        except (ValueError, TypeError):
            pass
        if score is not None:
            try:
                return float(score) * impact_weight
            except (ValueError, TypeError):
                pass

    triggers = cell.get('triggers', '0')
    tp = cell.get('true_positives', '0')
    try:
        tp_f = float(tp)
        trig_f = float(triggers)
        if trig_f > 0:
            return laplace_score(tp_f, trig_f, impact_weight)
    except (ValueError, TypeError):
        pass

    try:
        return float(fitness) * impact_weight
    except (ValueError, TypeError):
        return 0.5 * impact_weight


__all__ = [
    "_wilson_interval",
    "_to_num",
    "bayesian_posterior",
    "wilson_lower_bound",
    "laplace_score",
    "bayesian_score",
    "compute_cell_fitness",
]
