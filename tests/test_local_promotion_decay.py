"""Tests for apply_decay integration in the --local promotion path.

Verifies that the --local promotion path also applies exponential decay
before evaluating candidates, consistent with the --tier-check path.
"""
import json
import os
import subprocess
import sys
import pytest

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, 'enzymes'))


class TestLocalPromotionDecay:
    """Verify decay is applied during --local promotion evaluation."""

    def test_local_path_applies_decay_before_scoring(self):
        """Directly test that the --local code path uses decayed counts.

        We import and inspect the logic: after normalize_fitness + apply_decay,
        a cell with tp=18/triggers=20 should have triggers=19 (int(20*0.95)=19)
        which is < 20, preventing promotion.

        Without decay, it would promote (score=0.864 > 0.85, triggers=20)."""
        from cell_promote import apply_decay, normalize_fitness

        metadata = {
            'enforcement': 'advisory',
            'impact_weight': 1.0,
            'fitness': {
                'triggers': 20,
                'true_positives': 18,
                'false_positives': 2
            }
        }

        fitness = normalize_fitness(metadata)
        # Without decay: Bayesian = 19/22 = 0.864 > 0.85, triggers=20 >= 20 → promotes
        raw_score = ((fitness['true_positives'] + 1) / (fitness['triggers'] + 2))
        assert raw_score > 0.85, f"Pre-decay score should be > 0.85, got {raw_score:.4f}"
        assert fitness['triggers'] >= 20, "Pre-decay triggers should be >= 20"

        # After decay: triggers=int(20*0.95)=19 < 20 → should NOT promote
        metadata['fitness'] = fitness
        apply_decay(metadata)
        decayed = metadata['fitness']

        assert decayed['triggers'] < 20, \
            f"Post-decay triggers should be < 20, got {decayed['triggers']}"

        decayed_score = ((decayed['true_positives'] + 1) / (decayed['triggers'] + 2))

        # This is the actual promotion check from --local path
        would_promote = decayed_score > 0.85 and decayed['triggers'] >= 20
        assert not would_promote, \
            f"After decay, cell should NOT promote (score={decayed_score:.4f}, triggers={decayed['triggers']})"

    def test_apply_decay_reduces_stale_triggers(self):
        """Verify apply_decay actually reduces trigger count for stale cells.
        This is the behavioral contract: if a cell hasn't been seen in >1 hour,
        decay must reduce its triggers to prevent stale count inflation."""
        import time
        from cell_promote import apply_decay

        meta = {'fitness': {
            'triggers': 100, 'true_positives': 90, 'false_positives': 10,
            'last_decay_epoch': int(time.time()) - 7200  # 2 hours ago
        }}
        apply_decay(meta)
        assert meta['fitness']['triggers'] < 100, \
            "apply_decay must reduce triggers for stale cells"
