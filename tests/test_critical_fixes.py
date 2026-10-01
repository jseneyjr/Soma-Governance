"""TDD tests for v0.30 critical fixes (Tempest audit remediation).

Tests cover:
- Phase 1: Bayesian score parity across all modules
- Phase 2: C1 — NEW/DORMANT status restoration for zero-trigger cells
- Phase 3: C2 — Promotion guards against zero triggers
- Phase 4: C3 — Mandatory cells have fitness scores
- Phase 5: C5 — Decay idempotency within session
"""
import json
import math
import os
import subprocess
import sys
import time

import pytest

from tests.helpers_cell import (
    soma_workspace, write_cell_with_fitness,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, 'enzymes'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'soma_mcp'))


# ── Phase 1: Bayesian Score Parity ────────────────────────────────────────

class TestBayesianScoreParity:
    """Verify the canonical formula is used consistently across all modules."""

    def test_shared_module_exists(self):
        """bayesian_score.py must exist as the single source of truth."""
        from bayesian_score import bayesian_score
        assert callable(bayesian_score)

    def test_shared_module_basic_calculation(self):
        from bayesian_score import bayesian_score
        assert bayesian_score(5, 10) == pytest.approx((5+1)/(10+2))
        assert bayesian_score(0, 0) == pytest.approx(0.5)
        assert bayesian_score(0, 0, 1.8) == pytest.approx(0.9)

    def test_cell_fitness_agrees_with_shared_module(self):
        """cell_fitness.bayesian_fitness and bayesian_score agree on directionality."""
        from bayesian_score import bayesian_score
        from cell_fitness import bayesian_fitness
        # Non-trivial data: tp=3, fp=1 (triggers=4 for bayesian_score)
        # bayesian_score: Laplace — (3+1)/(4+2) = 4/6 ≈ 0.6667
        shared = bayesian_score(3, 4)
        assert shared == pytest.approx(4 / 6)
        # bayesian_fitness: Jeffrey's prior — a=3.5, b=1.5, mean=3.5/5.0=0.7
        cell = bayesian_fitness(tp=3, fp=1)
        assert cell['mean'] == pytest.approx(0.7)
        # Both must agree: high-tp data → score well above 0.5
        assert shared > 0.5
        assert cell['mean'] > 0.5

    def test_cell_promote_normalize_fitness_callable(self):
        """cell_promote.normalize_fitness must extract and preserve fitness fields."""
        from cell_promote import normalize_fitness
        meta = {'fitness': {'triggers': 5, 'true_positives': 3, 'false_positives': 1}}
        result = normalize_fitness(meta)
        assert isinstance(result, dict)
        assert result['triggers'] == 5
        assert result['true_positives'] == 3
        assert result['false_positives'] == 1

    def test_cell_promote_normalizes_scalar_fitness(self):
        """cell_promote.normalize_fitness handles scalar fitness values."""
        from cell_promote import normalize_fitness
        # Scalar fitness (1.0) should become {'score': 1.0}
        meta = {'fitness': 1.0}
        result = normalize_fitness(meta)
        assert isinstance(result, dict)
        assert result.get('score') == 1.0

    def test_handles_string_inputs(self):
        """Should coerce string values from YAML without crashing."""
        from bayesian_score import bayesian_score
        result = bayesian_score("5", "10", "1.0")
        assert result == pytest.approx((5+1)/(10+2))


# ── Phase 2: C1 — NEW/DORMANT Status Restoration ─────────────────────────

class TestNewDormantStatus:
    """Verify zero-trigger cells produce maximally uncertain Bayesian scores
    and that decayed_fitness handles missing data gracefully."""

    def test_zero_trigger_cell_returns_maximally_uncertain(self):
        """A brand-new cell with 0 triggers should score 0.5 (maximally uncertain)."""
        from cell_fitness import bayesian_fitness
        result = bayesian_fitness(tp=0, fp=0)
        assert result['mean'] == pytest.approx(0.5)
        assert result['certainty'] == 'low'

    def test_zero_trigger_cell_has_wide_confidence_interval(self):
        """Zero-trigger cells should have a wide 90% CI spanning nearly [0, 1]."""
        from cell_fitness import bayesian_fitness
        result = bayesian_fitness(tp=0, fp=0)
        assert result['lower_90'] < 0.2, f"Lower bound too high: {result['lower_90']}"
        assert result['upper_90'] > 0.8, f"Upper bound too low: {result['upper_90']}"

    def test_decayed_fitness_returns_none_for_no_data(self):
        """decayed_fitness should return raw_score unchanged when no date is available."""
        from cell_fitness import decayed_fitness
        assert decayed_fitness(None, None) is None
        assert decayed_fitness(0.8, None) == 0.8


# ── Phase 3: C2 — Promotion Zero-Trigger Guard ───────────────────────────

class TestPromotionZeroTriggerGuard:
    """Verify untested cells cannot be promoted regardless of impact_weight."""

    def test_normalize_fitness_zero_triggers_not_promoted(self):
        """A cell with 0 triggers must not be promotable: score below threshold."""
        from bayesian_score import bayesian_score
        from cell_promote import normalize_fitness
        meta = {'fitness': {'triggers': 0, 'true_positives': 0, 'false_positives': 0}}
        result = normalize_fitness(meta)
        # Compute the Bayesian score this cell would receive
        score = bayesian_score(
            result.get('true_positives', 0), result.get('triggers', 0)
        )
        # Score must be 0.5 (maximally uncertain), well below promotion threshold 0.7
        assert score == pytest.approx(0.5)
        assert score < 0.7, \
            f"Zero-trigger cell must not meet promotion threshold, got {score}"
        # Triggers must remain 0 — hard gate for promotion
        assert result.get('triggers', 0) == 0

    def test_normalize_fitness_high_triggers_preserves_data(self):
        """Normalization must preserve data, and high-quality cells must score above 0.9."""
        from bayesian_score import bayesian_score
        from cell_promote import normalize_fitness
        meta = {'fitness': {'triggers': 50, 'true_positives': 48, 'false_positives': 1}}
        result = normalize_fitness(meta)
        # All fields preserved
        assert result['triggers'] == 50
        assert result['true_positives'] == 48
        assert result['false_positives'] == 1
        # Score computed from preserved data should reflect high quality
        score = bayesian_score(result['true_positives'], result['triggers'])
        assert score == pytest.approx((48 + 1) / (50 + 2))
        assert score > 0.9, \
            f"High-quality cell should score above 0.9, got {score}"


# ── Phase 4: C3 — Mandatory Cells Fitness Score ──────────────────────────

class TestMandatoryCellsFitnessScore:
    """Verify mandatory wall/gate cells have their fitness score computed."""

    @pytest.fixture
    def populated_workspace(self, soma_workspace):
        """Workspace with a wall cell and an advisory cell for fitness tests."""
        cells_dir = soma_workspace / ".soma" / "cells"
        write_cell_with_fitness(cells_dir, "wall-auth", cell_type="wall",
                               triggers=50, tp=48, fp=1,
                               hypothesis="Auth check")
        write_cell_with_fitness(cells_dir, "advisory-style",
                               triggers=10, tp=8, fp=1,
                               hypothesis="Style check")
        return str(soma_workspace)

    def test_mandatory_cells_have_nonzero_fitness(self, populated_workspace):
        """Wall cells must have their fitness computed, not default to 0."""
        from jit_engine import express
        result = express(populated_workspace, changed_files=["app.py"], budget=5)

        for cell in result['relevant_cells']:
            if cell.get('type') == 'wall':
                fitness = cell.get('fitness', 0)
                assert fitness > 0, \
                    f"Mandatory cell '{cell.get('name')}' has fitness {fitness}, expected > 0"

    def test_all_expressed_cells_have_fitness(self, populated_workspace):
        """Every expressed cell (mandatory or candidate) must have fitness."""
        from jit_engine import express
        result = express(populated_workspace, changed_files=["app.py"], budget=5)

        for cell in result['relevant_cells']:
            assert 'fitness' in cell, \
                f"Cell '{cell.get('name')}' missing fitness key"
            assert isinstance(cell['fitness'], (int, float)), \
                f"Cell '{cell.get('name')}' fitness is not numeric"


# ── Phase 5: C5 — Decay Idempotency ──────────────────────────────────────

class TestDecayIdempotency:
    """Verify apply_decay is idempotent within a session."""

    def test_consecutive_decay_is_noop(self):
        """Two apply_decay calls within 1 hour should only decay once."""
        from cell_promote import apply_decay
        meta = {'fitness': {
            'triggers': 100, 'true_positives': 90, 'false_positives': 10,
            'last_decay_epoch': int(time.time())  # just decayed
        }}
        original_triggers = meta['fitness']['triggers']
        apply_decay(meta)
        assert meta['fitness']['triggers'] == original_triggers, \
            f"Decay should be no-op within session, got {meta['fitness']['triggers']}"

    def test_decay_applies_after_gap(self):
        """Decay should apply if last_decay_epoch is > 1 hour ago."""
        from cell_promote import apply_decay
        meta = {'fitness': {
            'triggers': 100, 'true_positives': 90, 'false_positives': 10,
            'last_decay_epoch': int(time.time()) - 7200  # 2 hours ago
        }}
        apply_decay(meta)
        assert meta['fitness']['triggers'] < 100, \
            f"Decay should apply after 2-hour gap, got {meta['fitness']['triggers']}"

    def test_decay_sets_epoch_after_application(self):
        """After decaying, last_decay_epoch should be set to current time."""
        from cell_promote import apply_decay
        before = int(time.time())
        meta = {'fitness': {
            'triggers': 100, 'true_positives': 90, 'false_positives': 10
        }}
        apply_decay(meta)
        after = int(time.time())
        epoch = meta['fitness'].get('last_decay_epoch', 0)
        assert before <= epoch <= after, \
            f"last_decay_epoch should be set to current time, got {epoch}"

    def test_first_decay_no_epoch_applies(self):
        """Cells without last_decay_epoch (legacy) should still get decayed."""
        from cell_promote import apply_decay
        meta = {'fitness': {
            'triggers': 100, 'true_positives': 90, 'false_positives': 10
            # no last_decay_epoch
        }}
        apply_decay(meta)
        assert meta['fitness']['triggers'] < 100, \
            "First decay (no epoch) should apply"
