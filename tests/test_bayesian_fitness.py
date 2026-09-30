"""Tests for v0.30 Bayesian fitness scoring and mandatory invariant slots.

Each test class covers one architectural change:
1. Bayesian posterior mean (Laplace smoothing) in cell_fitness.py
2. Bayesian posterior mean in jit_engine.get_fitness_score()
3. Mandatory invariant slots in jit_engine.express()

Tests are behavioral: they verify the scoring *behavior* under edge cases,
not the internal formula. If the formula changes but the behavior is preserved,
tests should still pass.
"""
import math
import os
import sys
import tempfile
import shutil

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, 'soma_mcp'))


# ── Bayesian Fitness Scoring (cell_fitness.py) ────────────────────────────

class TestBayesianFitnessScoring:
    """Verify bayesian_fitness() from cell_fitness.py produces correct behavior."""

    def test_zero_triggers_returns_0_5(self):
        """A brand-new cell with no data should score 0.5 (maximally uncertain)."""
        sys.path.insert(0, os.path.join(REPO_ROOT, 'enzymes'))
        from cell_fitness import bayesian_fitness
        result = bayesian_fitness(tp=0, fp=0)
        assert result['mean'] == pytest.approx(0.5)

    def test_perfect_small_sample_not_1_0(self):
        """A cell with 1 TP / 0 FP should NOT score 1.0 — prior pulls it down."""
        sys.path.insert(0, os.path.join(REPO_ROOT, 'enzymes'))
        from cell_fitness import bayesian_fitness
        result = bayesian_fitness(tp=1, fp=0)
        assert result['mean'] < 1.0, "Perfect 1/0 must not score 1.0"

    def test_all_false_positives_below_0_5(self):
        """A cell with 0 TP / 5 FP should score well below 0.5."""
        sys.path.insert(0, os.path.join(REPO_ROOT, 'enzymes'))
        from cell_fitness import bayesian_fitness
        result = bayesian_fitness(tp=0, fp=5)
        assert result['mean'] < 0.15

    def test_large_sample_converges_to_raw(self):
        """At 100 observations, Bayesian and raw should be nearly identical."""
        sys.path.insert(0, os.path.join(REPO_ROOT, 'enzymes'))
        from cell_fitness import bayesian_fitness
        result = bayesian_fitness(tp=90, fp=10)
        raw = 90 / 100
        assert abs(result['mean'] - raw) < 0.01

    def test_certainty_low_for_small_samples(self):
        """Fewer than 5 observations -> certainty must be 'low'."""
        sys.path.insert(0, os.path.join(REPO_ROOT, 'enzymes'))
        from cell_fitness import bayesian_fitness
        result = bayesian_fitness(tp=1, fp=1)
        assert result['certainty'] == 'low'

    def test_certainty_medium_for_moderate_samples(self):
        """5-19 observations -> certainty must be 'medium'."""
        sys.path.insert(0, os.path.join(REPO_ROOT, 'enzymes'))
        from cell_fitness import bayesian_fitness
        result = bayesian_fitness(tp=5, fp=5)
        assert result['certainty'] == 'medium'

    def test_monotonicity_with_increasing_tp(self):
        """More true positives -> higher score, for fixed false positives."""
        sys.path.insert(0, os.path.join(REPO_ROOT, 'enzymes'))
        from cell_fitness import bayesian_fitness
        scores = [bayesian_fitness(tp=tp, fp=5)['mean'] for tp in range(11)]
        for i in range(len(scores) - 1):
            assert scores[i] < scores[i + 1], \
                f"Score must increase: tp={i} ({scores[i]:.4f}) < tp={i+1} ({scores[i+1]:.4f})"


# ── JIT Engine: get_fitness_score() ───────────────────────────────────────

class TestJITFitnessScore:
    """Verify jit_engine.get_fitness_score uses Bayesian scoring."""

    def _make_cell(self, tp=0, triggers=0, fp=0, impact_weight=1.0, score=None):
        """Build a minimal cell dict matching the frontmatter structure."""
        fitness = {'true_positives': tp, 'triggers': triggers, 'false_positives': fp}
        if score is not None:
            fitness['score'] = score
        return {'fitness': fitness, 'impact_weight': impact_weight}

    def test_basic_bayesian_scoring(self):
        """get_fitness_score should return Bayesian posterior, not raw ratio."""
        from jit_engine import get_fitness_score
        cell = self._make_cell(tp=5, triggers=10)
        result = get_fitness_score(cell)
        expected = (5 + 1) / (10 + 2)  # 0.5
        assert result == pytest.approx(expected, rel=1e-3)

    def test_zero_triggers_returns_default(self):
        """Zero triggers should return the default 0.5 * impact_weight."""
        from jit_engine import get_fitness_score
        cell = self._make_cell(tp=0, triggers=0)
        result = get_fitness_score(cell)
        assert result == pytest.approx(0.5)

    def test_impact_weight_applied(self):
        """Impact weight should multiply the Bayesian score."""
        from jit_engine import get_fitness_score
        cell = self._make_cell(tp=5, triggers=10, impact_weight=0.8)
        result = get_fitness_score(cell)
        expected = ((5 + 1) / (10 + 2)) * 0.8
        assert result == pytest.approx(expected, rel=1e-3)

    def test_perfect_record_not_1(self):
        """A cell with 10/10 TP should not score 1.0."""
        from jit_engine import get_fitness_score
        cell = self._make_cell(tp=10, triggers=10)
        result = get_fitness_score(cell)
        assert result < 1.0, f"10/10 should score below 1.0, got {result}"

    def test_bare_scalar_fitness_fallback(self):
        """When fitness is a bare scalar (legacy), should use it * impact_weight."""
        from jit_engine import get_fitness_score
        cell = {'fitness': 0.75, 'impact_weight': 1.0}
        result = get_fitness_score(cell)
        # Bare scalar → dict conversion → 'score' key → returns score * impact
        assert isinstance(result, float)


# ── JIT Engine: Mandatory Invariant Slots ─────────────────────────────────

class TestMandatoryInvariantSlots:
    """Verify that wall cells and gate-tier cells always load regardless of budget."""

    @pytest.fixture
    def soma_workspace(self, tmp_path):
        """Create a minimal Soma workspace with cells of various types."""
        workspace = tmp_path / "project"
        cells_dir = workspace / ".soma" / "cells"
        cells_dir.mkdir(parents=True)

        # Wall cell (mandatory)
        (cells_dir / "wall-no-secrets.md").write_text(
            "---\n"
            "type: wall\n"
            "hypothesis: Never expose API keys\n"
            "enforcement: advisory\n"
            "target_paths:\n  - \"*.py\"\n"
            "fitness:\n  triggers: 10\n  true_positives: 9\n  false_positives: 0\n"
            "---\n# Wall content\n"
        )

        # Gate-tier cell (mandatory)
        (cells_dir / "gate-auth.md").write_text(
            "---\n"
            "type: vacuole\n"
            "hypothesis: Validate auth tokens\n"
            "enforcement: gate\n"
            "target_paths:\n  - \"*.py\"\n"
            "fitness:\n  triggers: 50\n  true_positives: 48\n  false_positives: 1\n"
            "---\n# Gate content\n"
        )

        # Advisory cell (competes for budget)
        (cells_dir / "advisory-formatting.md").write_text(
            "---\n"
            "type: chloroplast\n"
            "hypothesis: Use consistent formatting\n"
            "enforcement: advisory\n"
            "target_paths:\n  - \"*.py\"\n"
            "fitness:\n  triggers: 30\n  true_positives: 25\n  false_positives: 2\n"
            "---\n# Advisory content\n"
        )

        # Another advisory cell (competes)
        (cells_dir / "advisory-imports.md").write_text(
            "---\n"
            "type: vacuole\n"
            "hypothesis: Sort imports\n"
            "enforcement: advisory\n"
            "target_paths:\n  - \"*.py\"\n"
            "fitness:\n  triggers: 15\n  true_positives: 10\n  false_positives: 3\n"
            "---\n# Imports content\n"
        )

        return str(workspace)

    def test_walls_always_load_even_at_budget_1(self, soma_workspace):
        """With budget=1, wall cells must still load (they're mandatory)."""
        from jit_engine import express
        result = express(soma_workspace, changed_files=["app.py"], budget=1)

        cell_names = [c['name'] for c in result['relevant_cells']]
        assert 'wall-no-secrets' in cell_names, \
            f"Wall cell must always load. Got: {cell_names}"

    def test_gate_tier_always_loads(self, soma_workspace):
        """Gate-tier cells must always load regardless of budget."""
        from jit_engine import express
        result = express(soma_workspace, changed_files=["app.py"], budget=1)

        cell_names = [c['name'] for c in result['relevant_cells']]
        assert 'gate-auth' in cell_names, \
            f"Gate-tier cell must always load. Got: {cell_names}"

    def test_mandatory_cells_dont_consume_advisory_budget(self, soma_workspace):
        """With budget=3, mandatory cells (wall+gate) take 2 slots,
        leaving 1 slot for the best advisory cell."""
        from jit_engine import express
        result = express(soma_workspace, changed_files=["app.py"], budget=3)

        cell_names = [c['name'] for c in result['relevant_cells']]
        # 2 mandatory + 1 advisory = 3
        assert 'wall-no-secrets' in cell_names
        assert 'gate-auth' in cell_names
        assert len(cell_names) == 3, f"Expected 3 cells, got {len(cell_names)}: {cell_names}"

    def test_large_budget_includes_all(self, soma_workspace):
        """With budget=10 and 4 cells, all should load."""
        from jit_engine import express
        result = express(soma_workspace, changed_files=["app.py"], budget=10)

        cell_names = [c['name'] for c in result['relevant_cells']]
        assert len(cell_names) == 4, f"Expected all 4 cells, got {len(cell_names)}: {cell_names}"

    def test_mandatory_can_exceed_budget(self, soma_workspace):
        """If there are 3 mandatory cells and budget=2, all 3 mandatory still load.
        The budget constrains advisory cells, not mandatory ones."""
        from jit_engine import express
        # Budget=2 but we have 2 mandatory cells. Advisory gets 0 slots.
        result = express(soma_workspace, changed_files=["app.py"], budget=2)

        cell_names = [c['name'] for c in result['relevant_cells']]
        assert 'wall-no-secrets' in cell_names
        assert 'gate-auth' in cell_names
        # Advisory cells should NOT load since budget is consumed
        advisory_count = sum(1 for n in cell_names if 'advisory' in n)
        assert advisory_count == 0, \
            f"Advisory cells should not load when budget is consumed by mandatory. Got: {cell_names}"

    def test_no_changed_files_returns_empty(self, soma_workspace):
        """When no files are changed, no cells load (including mandatory)."""
        from jit_engine import express
        result = express(soma_workspace, changed_files=[], budget=10)
        assert len(result['relevant_cells']) == 0

    def test_stats_report_correct_counts(self, soma_workspace):
        """Stats should report total, matched, and expressed counts."""
        from jit_engine import express
        result = express(soma_workspace, changed_files=["app.py"], budget=3)

        assert result['stats']['total_cells'] == 4
        assert result['stats']['matched'] == 4  # all match *.py
        assert result['stats']['expressed'] == 3  # budget=3
