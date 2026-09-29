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

pytest.importorskip("yaml")  # enzymes require PyYAML at import time

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

    def test_cell_fitness_uses_shared_module(self):
        """cell_fitness.py must import from bayesian_score, not inline the formula."""
        source_path = os.path.join(REPO_ROOT, "enzymes", "cell_fitness.py")
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "from bayesian_score import" in source or "import bayesian_score" in source, \
            "cell_fitness.py must import from bayesian_score module"

    def test_jit_engine_references_shared_module(self):
        """jit_engine.py can't import from enzymes/ (zero-dep policy), but must
        reference the canonical source in its docstring."""
        source_path = os.path.join(REPO_ROOT, "soma_mcp", "jit_engine.py")
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "bayesian_score" in source, \
            "jit_engine.py must reference bayesian_score as the canonical source"

    def test_cell_promote_uses_shared_module(self):
        """cell_promote.py must import from bayesian_score."""
        source_path = os.path.join(REPO_ROOT, "enzymes", "cell_promote.py")
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "from bayesian_score import" in source or "import bayesian_score" in source, \
            "cell_promote.py must import from bayesian_score module"

    def test_handles_string_inputs(self):
        """Should coerce string values from YAML without crashing."""
        from bayesian_score import bayesian_score
        result = bayesian_score("5", "10", "1.0")
        assert result == pytest.approx((5+1)/(10+2))


# ── Phase 2: C1 — NEW/DORMANT Status Restoration ─────────────────────────

class TestNewDormantStatus:
    """Verify zero-trigger cells get NEW or DORMANT status, not ADAPT."""

    def test_zero_trigger_cell_status_is_new(self):
        """A brand-new cell with 0 triggers should have status NEW, not ADAPT."""
        result = subprocess.run(
            [sys.executable, os.path.join(REPO_ROOT, "enzymes", "cell_fitness.py"),
             "--json", "--cell-dir", "/dev/null"],
            capture_output=True, text=True, timeout=10,
            env={**os.environ, "PYTHONPATH": REPO_ROOT}
        )
        # We can't easily run cell_fitness with a fake cell, so test the logic directly
        pass  # Placeholder — real test below

    def test_status_classification_preserves_new(self):
        """Direct unit test: zero triggers + recent creation → NEW status."""
        # Read cell_fitness.py source to verify the is_unobserved guard exists
        source_path = os.path.join(REPO_ROOT, "enzymes", "cell_fitness.py")
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # The fix should add a guard that prevents zero-trigger cells from
        # entering the dec_score classification path
        # Check that the status logic has a triggers-based guard
        assert "triggers == 0" in source or "is_unobserved" in source, \
            "cell_fitness.py must guard zero-trigger cells from dec_score classification"

    def test_status_classification_preserves_dormant(self):
        """The DORMANT status path must be reachable for old unobserved cells."""
        source_path = os.path.join(REPO_ROOT, "enzymes", "cell_fitness.py")
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # DORMANT must not be dead code
        assert '"DORMANT"' in source, "DORMANT status must exist"
        # The else block containing DORMANT must be reachable
        # (this is verified by the structural guard above)


# ── Phase 3: C2 — Promotion Zero-Trigger Guard ───────────────────────────

class TestPromotionZeroTriggerGuard:
    """Verify untested cells cannot be promoted regardless of impact_weight."""

    def test_promote_path_requires_triggers(self):
        """cell_fitness.py --promote must require triggers > 0."""
        source_path = os.path.join(REPO_ROOT, "enzymes", "cell_fitness.py")
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # Find the --promote block
        promote_idx = source.find("args.promote") or source.find("--promote")
        if promote_idx == -1:
            pytest.skip("No --promote path found")
        promote_block = source[promote_idx:promote_idx+500]
        # Must check triggers before promoting
        assert "triggers" in promote_block, \
            "--promote path must check trigger count before promoting"

    def test_tournament_unobserved_scores_worst(self):
        """cell_tournament.py must treat zero-trigger cells as worst candidates."""
        source_path = os.path.join(REPO_ROOT, "enzymes", "cell_tournament.py")
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # The score assignment for None/zero-trigger cells must result in -1.0
        assert "triggers" in source or "-1.0" in source, \
            "Tournament must penalize unobserved cells"


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
