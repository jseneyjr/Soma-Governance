"""Tests for apply_decay integration in the --local promotion path.

Verifies that the --local promotion path also applies exponential decay
before evaluating candidates, consistent with the --tier-check path.
"""
import json
import os
import subprocess
import sys
import pytest
from soma_core.frontmatter import dump_frontmatter, parse_frontmatter

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, 'enzymes'))


@pytest.mark.skipif(
    not os.path.exists(os.path.join(REPO_ROOT, "enzymes", "cell_promote.py")),
    reason="enzymes directory purged in v0.97.0",
)
class TestLocalPromotionDecay:
    """Verify decay is applied during --local promotion evaluation."""

    def test_local_path_applies_decay_before_scoring(self, tmp_path):
        """Verify the CLI 'soma promote --local' applies decay to stale cells.
        
        Instead of importing internal modules, we construct a stale cell and run 
        the CLI integration path to ensure the output matches decayed expectations.
        """
        import time

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
        content = dump_frontmatter(meta, body="# Stale Cell\n")
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
        content = dump_frontmatter(meta, body="# Cell\n")
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
        new_meta = parse_frontmatter(new_content)
        assert new_meta['fitness']['triggers'] == 95

# ── Phase 3: C2 — Promotion Zero-Trigger Guard ───────────────────────────

class TestPromotionZeroTriggerGuard:
    """Verify untested cells cannot be promoted regardless of impact_weight."""

    def test_normalize_fitness_zero_triggers_not_promoted(self, tmp_path):
        """A cell with 0 triggers must not be promotable via lifecycle evaluation."""
        from immune_system.verification.lifecycle import evaluate_promotions
        from tests.helpers_cell import make_cell

        cells_dir = tmp_path / ".soma" / "cells" / "vacuoles"
        cells_dir.mkdir(parents=True)
        evidence_dir = tmp_path / ".soma" / "evidence"
        evidence_dir.mkdir(parents=True)

        make_cell(str(cells_dir), "zero-cell", cell_type="vacuole", created_days_ago=60)
        # 0 triggers in evidence
        candidates = evaluate_promotions(str(tmp_path))
        assert not any(c["cell_id"] == "zero-cell" for c in candidates), \
            "Zero-trigger cell must not appear in promotion candidates"

    def test_normalize_fitness_high_triggers_preserves_data(self, tmp_path):
        """A high-quality cell with 50 triggers (48 TP, 1 FP) must be promoted."""
        from immune_system.verification.lifecycle import evaluate_promotions
        from tests.helpers_cell import make_cell, write_evidence

        cells_dir = tmp_path / ".soma" / "cells" / "vacuoles"
        cells_dir.mkdir(parents=True)
        evidence_dir = tmp_path / ".soma" / "evidence"
        evidence_dir.mkdir(parents=True)

        make_cell(str(cells_dir), "high-cell", cell_type="vacuole", created_days_ago=60)
        write_evidence(str(evidence_dir), "high-cell", triggers=50, tp=48, fp=1)

        candidates = evaluate_promotions(str(tmp_path))
        promoted_ids = [c["cell_id"] for c in candidates]
        assert "high-cell" in promoted_ids, \
            f"High-quality cell should be promoted, got candidates {candidates}"
