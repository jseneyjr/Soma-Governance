"""TDD Gate 1 tests for the cell lifecycle engine.

The lifecycle engine provides deterministic promotion/demotion decisions
based on JSONL evidence data (fitness.jsonl + outcomes.jsonl):

Lifecycle path: vacuole (hypothesis) → wall (proven gate) → genome (universal law)

Promotion criteria (deterministic):
  - triggers ≥ 20 AND tp_rate > 0.85 AND age > 30 days

Demotion criteria (deterministic):
  - fp_rate > 0.5 OR triggers == 0 for 90 days
"""
import json
import os
import sys
from datetime import datetime, timedelta

import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from tests.helpers_cell import make_cell, write_evidence


class TestLifecycleImport:
    """Lifecycle engine must be importable."""

    def test_evaluate_promotions_importable(self):
        from immune_system.verification.lifecycle import evaluate_promotions
        assert callable(evaluate_promotions)

    def test_evaluate_demotions_importable(self):
        from immune_system.verification.lifecycle import evaluate_demotions
        assert callable(evaluate_demotions)


class TestPromotionCriteria:
    """Deterministic promotion: triggers ≥ 20 AND tp_rate > 0.85 AND age > 30 days."""

    def test_promotes_qualifying_vacuole(self, tmp_path):
        """Vacuole with 25 triggers, 90% tp_rate, 45 days old → promote to wall."""
        from immune_system.verification.lifecycle import evaluate_promotions

        cells_dir = tmp_path / ".soma" / "cells" / "vacuoles"
        cells_dir.mkdir(parents=True)
        evidence_dir = tmp_path / ".soma" / "evidence"
        evidence_dir.mkdir(parents=True)

        make_cell(str(cells_dir), "proven-cell", cell_type="vacuole",
                  created_days_ago=45)
        write_evidence(str(evidence_dir), "proven-cell", triggers=25, tp=23, fp=2)

        candidates = evaluate_promotions(str(tmp_path))
        assert len(candidates) == 1
        assert candidates[0]["cell_id"] == "proven-cell"
        assert candidates[0]["from_type"] == "vacuole"
        assert candidates[0]["to_type"] == "wall"

    def test_rejects_too_few_triggers(self, tmp_path):
        """Only 10 triggers → not enough for promotion."""
        from immune_system.verification.lifecycle import evaluate_promotions

        cells_dir = tmp_path / ".soma" / "cells" / "vacuoles"
        cells_dir.mkdir(parents=True)
        evidence_dir = tmp_path / ".soma" / "evidence"
        evidence_dir.mkdir(parents=True)

        make_cell(str(cells_dir), "young-cell", cell_type="vacuole",
                  created_days_ago=45)
        write_evidence(str(evidence_dir), "young-cell", triggers=10, tp=9, fp=1)

        candidates = evaluate_promotions(str(tmp_path))
        assert len(candidates) == 0

    def test_rejects_low_tp_rate(self, tmp_path):
        """tp_rate = 0.60 → below 0.85 threshold."""
        from immune_system.verification.lifecycle import evaluate_promotions

        cells_dir = tmp_path / ".soma" / "cells" / "vacuoles"
        cells_dir.mkdir(parents=True)
        evidence_dir = tmp_path / ".soma" / "evidence"
        evidence_dir.mkdir(parents=True)

        make_cell(str(cells_dir), "noisy-cell", cell_type="vacuole",
                  created_days_ago=45)
        write_evidence(str(evidence_dir), "noisy-cell", triggers=25, tp=15, fp=10)

        candidates = evaluate_promotions(str(tmp_path))
        assert len(candidates) == 0

    def test_rejects_too_young(self, tmp_path):
        """Cell only 15 days old → must be > 30 days."""
        from immune_system.verification.lifecycle import evaluate_promotions

        cells_dir = tmp_path / ".soma" / "cells" / "vacuoles"
        cells_dir.mkdir(parents=True)
        evidence_dir = tmp_path / ".soma" / "evidence"
        evidence_dir.mkdir(parents=True)

        make_cell(str(cells_dir), "new-cell", cell_type="vacuole",
                  created_days_ago=15)
        write_evidence(str(evidence_dir), "new-cell", triggers=30, tp=28, fp=2)

        candidates = evaluate_promotions(str(tmp_path))
        assert len(candidates) == 0

    def test_wall_promotes_to_genome(self, tmp_path):
        """Wall with strong evidence → promote to genome."""
        from immune_system.verification.lifecycle import evaluate_promotions

        cells_dir = tmp_path / ".soma" / "cells" / "walls"
        cells_dir.mkdir(parents=True)
        evidence_dir = tmp_path / ".soma" / "evidence"
        evidence_dir.mkdir(parents=True)

        make_cell(str(cells_dir), "proven-wall", cell_type="wall",
                  created_days_ago=60)
        write_evidence(str(evidence_dir), "proven-wall", triggers=30, tp=28, fp=2)

        candidates = evaluate_promotions(str(tmp_path))
        assert len(candidates) == 1
        assert candidates[0]["to_type"] == "genome"

    def test_empty_workspace_returns_empty(self, tmp_path):
        """No cells → no promotion candidates."""
        from immune_system.verification.lifecycle import evaluate_promotions

        (tmp_path / ".soma" / "cells").mkdir(parents=True)
        (tmp_path / ".soma" / "evidence").mkdir(parents=True)

        candidates = evaluate_promotions(str(tmp_path))
        assert candidates == []


class TestDemotionCriteria:
    """Deterministic demotion: fp_rate > 0.5 OR triggers == 0 for 90 days."""

    def test_demotes_noisy_cell(self, tmp_path):
        """fp_rate = 0.7 → demote."""
        from immune_system.verification.lifecycle import evaluate_demotions

        cells_dir = tmp_path / ".soma" / "cells" / "walls"
        cells_dir.mkdir(parents=True)
        evidence_dir = tmp_path / ".soma" / "evidence"
        evidence_dir.mkdir(parents=True)

        make_cell(str(cells_dir), "noisy-wall", cell_type="wall",
                  created_days_ago=60)
        write_evidence(str(evidence_dir), "noisy-wall", triggers=20, tp=6, fp=14)

        candidates = evaluate_demotions(str(tmp_path))
        assert len(candidates) == 1
        assert candidates[0]["cell_id"] == "noisy-wall"
        assert candidates[0]["reason"] == "high_fp_rate"

    def test_demotes_dormant_cell(self, tmp_path):
        """Zero triggers for 90+ days → demote."""
        from immune_system.verification.lifecycle import evaluate_demotions

        cells_dir = tmp_path / ".soma" / "cells" / "walls"
        cells_dir.mkdir(parents=True)
        evidence_dir = tmp_path / ".soma" / "evidence"
        evidence_dir.mkdir(parents=True)

        make_cell(str(cells_dir), "dormant-wall", cell_type="wall",
                  created_days_ago=120)
        # No evidence at all — zero triggers

        candidates = evaluate_demotions(str(tmp_path))
        assert len(candidates) == 1
        assert candidates[0]["cell_id"] == "dormant-wall"
        assert candidates[0]["reason"] == "dormant"

    def test_keeps_healthy_cell(self, tmp_path):
        """Cell with good metrics → no demotion."""
        from immune_system.verification.lifecycle import evaluate_demotions

        cells_dir = tmp_path / ".soma" / "cells" / "walls"
        cells_dir.mkdir(parents=True)
        evidence_dir = tmp_path / ".soma" / "evidence"
        evidence_dir.mkdir(parents=True)

        make_cell(str(cells_dir), "good-wall", cell_type="wall",
                  created_days_ago=60)
        write_evidence(str(evidence_dir), "good-wall", triggers=25, tp=23, fp=2)

        candidates = evaluate_demotions(str(tmp_path))
        assert len(candidates) == 0

    def test_wall_demotes_to_vacuole(self, tmp_path):
        """Demoted wall should become a vacuole."""
        from immune_system.verification.lifecycle import evaluate_demotions

        cells_dir = tmp_path / ".soma" / "cells" / "walls"
        cells_dir.mkdir(parents=True)
        evidence_dir = tmp_path / ".soma" / "evidence"
        evidence_dir.mkdir(parents=True)

        make_cell(str(cells_dir), "bad-wall", cell_type="wall",
                  created_days_ago=60)
        write_evidence(str(evidence_dir), "bad-wall", triggers=10, tp=3, fp=7)

        candidates = evaluate_demotions(str(tmp_path))
        assert len(candidates) == 1
        assert candidates[0]["from_type"] == "wall"
        assert candidates[0]["to_type"] == "vacuole"

    def test_empty_workspace_returns_empty(self, tmp_path):
        """No cells → no demotion candidates."""
        from immune_system.verification.lifecycle import evaluate_demotions

        (tmp_path / ".soma" / "cells").mkdir(parents=True)
        (tmp_path / ".soma" / "evidence").mkdir(parents=True)

        candidates = evaluate_demotions(str(tmp_path))
        assert candidates == []
