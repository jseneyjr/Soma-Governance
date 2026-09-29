"""Tests for apply_decay integration in the --local promotion path.

Verifies that the --local promotion path also applies exponential decay
before evaluating candidates, consistent with the --tier-check path.
"""
import json
import os
import subprocess
import sys
import pytest

yaml = pytest.importorskip("yaml")

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

    def test_local_code_path_calls_apply_decay(self):
        """Verify that the --local code path in cell_promote.py actually
        calls apply_decay. This is an AST/source-level test to catch
        if someone removes the call."""
        import ast

        source_path = os.path.join(REPO_ROOT, "enzymes", "cell_promote.py")
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # Find the --local block (after "if args.local:")
        local_block_start = source.find("if args.local:")
        assert local_block_start != -1, "Could not find 'if args.local:' in cell_promote.py"

        # Find the end of the local block (next top-level else/elif at same indent)
        local_block_end = source.find("\n    else:", local_block_start)
        if local_block_end == -1:
            local_block_end = len(source)

        local_block = source[local_block_start:local_block_end]

        assert "apply_decay" in local_block, \
            "The --local promotion path does NOT call apply_decay(). " \
            "Decay must be applied before scoring to prevent stale count inflation."
