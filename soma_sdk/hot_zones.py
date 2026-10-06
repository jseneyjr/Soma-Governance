"""Hot Zone Analysis — backward-compatible facade delegating to soma_core.defects.

The loop:
    Bugs → Registry → Hot zones + pattern clusters →
    Cell fitness boost → Better cell selection → Fewer bugs → ♻️
"""
from __future__ import annotations

from soma_core.defects import (
    BoostConfig,
    HotZoneReport,
    compute_cell_boost,
    compute_hot_zones,
    load_config,
    load_report_from_workspace,
)

__all__ = [
    "BoostConfig",
    "HotZoneReport",
    "load_config",
    "compute_hot_zones",
    "compute_cell_boost",
    "load_report_from_workspace",
]
