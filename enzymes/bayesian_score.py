"""Shared Bayesian scoring utility for Soma.

DEPRECATED: This module now delegates to soma_sdk.scoring.
All new code should import directly from soma_sdk.scoring.

Kept as a thin wrapper for backward compatibility with enzymes
that import `from bayesian_score import bayesian_score`.
"""
from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from soma_sdk.scoring import bayesian_score, bayesian_posterior, laplace_score, wilson_lower_bound  # noqa: F401, E402
