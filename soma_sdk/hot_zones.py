"""Hot Zone Analysis — bug registry → cell fitness boost weights.

v0.85: Computes file heat and pattern heat from BUG_REGISTRY.json.
Pure functions, no I/O, no side effects. Easy to test, easy to disable.

The loop:
    Bugs → Registry → Hot zones + pattern clusters →
    Cell fitness boost → Better cell selection → Fewer bugs → ♻️
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BoostConfig:
    """Tunable parameters for hot zone scoring."""
    file_heat_threshold: int = 2
    pattern_heat_threshold: int = 3
    release_window: int = 10
    min_outcomes_for_boost: int = 3
    max_file_boost: float = 0.5
    max_pattern_boost: float = 0.3


@dataclass
class HotZoneReport:
    """Computed boost data from the bug registry."""
    file_heat: dict[str, int] = field(default_factory=dict)
    pattern_heat: dict[str, int] = field(default_factory=dict)
    active_file_zones: list[str] = field(default_factory=list)
    active_pattern_zones: list[str] = field(default_factory=list)
    config: BoostConfig = field(default_factory=BoostConfig)
    total_bugs_analyzed: int = 0


def load_config(registry: dict) -> BoostConfig:
    """Extract boost config from registry, falling back to defaults."""
    raw = registry.get('boost_config', {})
    return BoostConfig(
        file_heat_threshold=raw.get('file_heat_threshold', 2),
        pattern_heat_threshold=raw.get('pattern_heat_threshold', 3),
        release_window=raw.get('release_window', 10),
        min_outcomes_for_boost=raw.get('min_outcomes_for_boost', 3),
        max_file_boost=raw.get('max_file_boost', 0.5),
        max_pattern_boost=raw.get('max_pattern_boost', 0.3),
    )


def compute_hot_zones(registry: dict) -> HotZoneReport:
    """Pure function: registry dict → HotZoneReport.

    Computes file heat (which files appear in multiple bugs) and pattern heat
    (which root cause categories recur). Applies configurable thresholds.

    Args:
        registry: Parsed BUG_REGISTRY.json dict.

    Returns:
        HotZoneReport with heat maps and active zones above threshold.
    """
    config = load_config(registry)
    bugs = registry.get('bugs', [])

    # File heat: count how many bugs each file appears in
    file_heat: dict[str, int] = {}
    for bug in bugs:
        for f in bug.get('affected_files', []):
            file_heat[f] = file_heat.get(f, 0) + 1

    # Pattern heat: count root cause categories
    pattern_heat: dict[str, int] = {}
    for bug in bugs:
        cat = bug.get('root_cause', '')
        if cat:
            pattern_heat[cat] = pattern_heat.get(cat, 0) + 1

    # Active zones: above threshold
    active_files = sorted(
        [f for f, count in file_heat.items() if count >= config.file_heat_threshold],
        key=lambda f: -file_heat[f],
    )
    active_patterns = sorted(
        [p for p, count in pattern_heat.items() if count >= config.pattern_heat_threshold],
        key=lambda p: -pattern_heat[p],
    )

    return HotZoneReport(
        file_heat=file_heat,
        pattern_heat=pattern_heat,
        active_file_zones=active_files,
        active_pattern_zones=active_patterns,
        config=config,
        total_bugs_analyzed=len(bugs),
    )


def compute_cell_boost(
    cell: dict[str, Any],
    report: HotZoneReport,
    outcome_count: int = 0,
) -> float:
    """Compute the fitness boost multiplier for a single cell.

    Args:
        cell: Cell dict with '_name', 'target_paths', 'tags' fields.
        report: Pre-computed HotZoneReport.
        outcome_count: Number of outcome data points (tp + fp) for this cell.
            Cells below min_outcomes_for_boost get zero boost.

    Returns:
        Boost multiplier (0.0 to max_file_boost + max_pattern_boost).
        Apply as: effective_score = outcome_score * (1 + boost)
    """
    if outcome_count < report.config.min_outcomes_for_boost:
        return 0.0

    file_boost = 0.0
    pattern_boost = 0.0

    # File heat boost: check if cell's target_paths overlap with hot zone files
    target_paths = cell.get('target_paths', [])
    if target_paths and report.active_file_zones:
        import fnmatch
        for hot_file in report.active_file_zones:
            for pattern in target_paths:
                if fnmatch.fnmatch(hot_file, pattern):
                    heat = report.file_heat.get(hot_file, 0)
                    file_boost += heat * 0.1
                    break  # Don't double-count same file

    # Pattern heat boost: check if cell's tags match hot patterns
    cell_tags = set(cell.get('tags', []))
    # Map root cause categories to related tag names
    tag_to_category = {
        'data_path': 'path_error',
        'path': 'path_error',
        'schema': 'schema_drift',
        'data_model': 'schema_drift',
        'silent': 'silent_failure',
        'error_handling': 'silent_failure',
        'mapping': 'mapping_error',
        'type_coercion': 'mapping_error',
        'dead_code': 'dead_code',
        'unused': 'dead_code',
    }
    for tag in cell_tags:
        category = tag_to_category.get(tag, tag)
        if category in report.active_pattern_zones:
            heat = report.pattern_heat.get(category, 0)
            pattern_boost += heat * 0.1

    # Cap at configured maximums
    file_boost = min(file_boost, report.config.max_file_boost)
    pattern_boost = min(pattern_boost, report.config.max_pattern_boost)

    return file_boost + pattern_boost


def load_report_from_workspace(workspace: str) -> HotZoneReport | None:
    """Convenience: load registry from disk and compute report.

    Returns None if registry doesn't exist (graceful degradation).
    """
    path = os.path.join(workspace, 'docs', 'project', 'BUG_REGISTRY.json')
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            registry = json.load(f)
        return compute_hot_zones(registry)
    except (json.JSONDecodeError, OSError):
        return None
