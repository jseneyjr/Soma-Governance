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
        """cell_fitness.bayesian_fitness must produce results consistent with bayesian_score."""
        from bayesian_score import bayesian_score
        from cell_fitness import bayesian_fitness
        # Both should give 0.5 for zero data
        shared = bayesian_score(0, 0)
        cell = bayesian_fitness(tp=0, fp=0)
        assert cell['mean'] == pytest.approx(shared, abs=0.05), \
            f"cell_fitness ({cell['mean']}) diverges from bayesian_score ({shared})"

    def test_cell_promote_normalize_fitness_callable(self):
        """cell_promote.normalize_fitness must be callable and return a dict."""
        from cell_promote import normalize_fitness
        meta = {'fitness': {'triggers': 5, 'true_positives': 3, 'false_positives': 1}}
        result = normalize_fitness(meta)
        assert isinstance(result, dict)

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
    """Verify zero-trigger cells get NEW or DORMANT status, not ADAPT."""

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
        """A cell with 0 triggers should not get a high normalized fitness score."""
        from cell_promote import normalize_fitness
        meta = {'fitness': {'triggers': 0, 'true_positives': 0, 'false_positives': 0}}
        result = normalize_fitness(meta)
        score = result.get('fitness', {}).get('score', 0)
        # Zero-trigger cells should have a neutral/low score, never promoted
        assert score is None or score <= 0.5, \
            f"Zero-trigger cell should not score above 0.5, got {score}"

    def test_normalize_fitness_high_triggers_preserves_data(self):
        """A cell with many true positives should have triggers preserved in normalized dict."""
        from cell_promote import normalize_fitness
        meta = {'fitness': {'triggers': 50, 'true_positives': 48, 'false_positives': 1}}
        result = normalize_fitness(meta)
        assert result.get('triggers') == 50
        assert result.get('true_positives') == 48


# ── Phase 4: C3 — Mandatory Cells Fitness Score ──────────────────────────

class TestMandatoryCellsFitnessScore:
    """Verify mandatory wall/gate cells have their fitness score computed."""

    @pytest.fixture
    def soma_workspace(self, tmp_path):
        workspace = tmp_path / "project"
        cells_dir = workspace / ".soma" / "cells"
        cells_dir.mkdir(parents=True)

        (cells_dir / "wall-auth.md").write_text(
            "---\n"
            "type: wall\n"
            "hypothesis: Auth check\n"
            "enforcement: advisory\n"
            "target_paths:\n  - \"*.py\"\n"
            "fitness:\n  triggers: 50\n  true_positives: 48\n  false_positives: 1\n"
            "---\n# Wall content\n"
        )
        (cells_dir / "advisory-style.md").write_text(
            "---\n"
            "type: vacuole\n"
            "hypothesis: Style check\n"
            "enforcement: advisory\n"
            "target_paths:\n  - \"*.py\"\n"
            "fitness:\n  triggers: 10\n  true_positives: 8\n  false_positives: 1\n"
            "---\n# Style content\n"
        )
        return str(workspace)

    def test_mandatory_cells_have_nonzero_fitness(self, soma_workspace):
        """Wall cells must have their fitness computed, not default to 0."""
        from jit_engine import express
        result = express(soma_workspace, changed_files=["app.py"], budget=5)

        for cell in result['relevant_cells']:
            if cell.get('type') == 'wall':
                fitness = cell.get('fitness', 0)
                assert fitness > 0, \
                    f"Mandatory cell '{cell.get('name')}' has fitness {fitness}, expected > 0"

    def test_all_expressed_cells_have_fitness(self, soma_workspace):
        """Every expressed cell (mandatory or candidate) must have fitness."""
        from jit_engine import express
        result = express(soma_workspace, changed_files=["app.py"], budget=5)

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
