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

    def test_local_path_applies_decay_before_scoring(self, tmp_path):
        """Verify the CLI 'soma promote --local' applies decay to stale cells.
        
        Instead of importing internal modules, we construct a stale cell and run 
        the CLI integration path to ensure the output matches decayed expectations.
        """
        import time
        import yaml

        cells_dir = tmp_path / ".soma" / "cells" / "vacuoles"
        cells_dir.mkdir(parents=True)

        # This cell would normally promote (triggers >= 20, score > 0.85)
        # But it's stale (decay epoch is 2 hours ago).
        cell_path = cells_dir / "stale-cell.md"
        meta = {
            'id': 'stale-cell',
            'type': 'vacuole',
            'target_paths': ['src/*.py'],
            'fitness': {
                'triggers': 21,
                'true_positives': 19,
                'false_positives': 2,
                'last_decay_epoch': int(time.time()) - 7200
            }
        }
        content = f"---\\n{yaml.dump(meta, default_flow_style=False)}---\\n# Stale Cell\\n"
        cell_path.write_text(content, encoding='utf-8')

        # Run the local promote enzyme which uses the --local flag
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO_ROOT, "enzymes", "cell_promote.py"), "--local"],
            cwd=str(tmp_path),
            capture_output=True,
            text=True
        )
        assert proc.returncode == 0
        
        # It should NOT be promoted because 21 triggers decayed to 19 (which is < 20 limit)
        assert "No candidates found for promotion." in proc.stdout
        assert "stale-cell" not in proc.stdout

    def test_tier_check_persists_decay(self, tmp_path):
        """Verify cell_promote.py --tier-check actually persists decayed triggers to disk."""
        import time
        import yaml

        cells_dir = tmp_path / ".soma" / "cells" / "vacuoles"
        cells_dir.mkdir(parents=True)

        cell_path = cells_dir / "decay-me.md"
        meta = {
            'id': 'decay-me',
            'type': 'vacuole',
            'enforcement': 'advisory',
            'fitness': {
                'triggers': 100,
                'true_positives': 90,
                'false_positives': 10,
                'last_decay_epoch': int(time.time()) - 7200
            }
        }
        content = f"---\\n{yaml.dump(meta, default_flow_style=False)}---\\n# Cell\\n"
        cell_path.write_text(content, encoding='utf-8')

        proc = subprocess.run(
            [sys.executable, os.path.join(REPO_ROOT, "enzymes", "cell_promote.py"), "--tier-check", "--execute"],
            cwd=str(tmp_path),
            capture_output=True,
            text=True
        )
        assert proc.returncode == 0
        
        # Read back the cell and verify decay was applied (triggers should be 95)
        new_content = cell_path.read_text(encoding='utf-8')
        parts = new_content.split('---')
        new_meta = yaml.safe_load(parts[1])
        assert new_meta['fitness']['triggers'] == 95

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
