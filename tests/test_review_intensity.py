"""TDD tests for review intensity level documentation consistency.

Verifies that the review intensity hierarchy is consistently documented
across README.md and the adaptive-reviewer SKILL.md.

Tests verify:
1. All intensity levels exist in both README and SKILL.md
2. Supercell is documented as the highest intensity
3. Escalation table includes all levels
"""
import os
import re
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


# Expected intensity levels in order (lowest to highest)
INTENSITY_LEVELS = ["Breeze", "Gale", "Trident", "Maelstrom", "Tempest", "Supercell"]


class TestReviewIntensityDocs:
    """Review intensity documentation consistency."""

    def test_readme_contains_all_intensity_levels(self):
        """README.md must document every intensity level."""
        readme = _read(os.path.join(REPO_ROOT, "README.md"))
        for level in INTENSITY_LEVELS:
            assert level in readme, f"Missing intensity level '{level}' in README.md"

    def test_readme_intensity_table_has_supercell(self):
        """README intensity table must include Supercell row."""
        readme = _read(os.path.join(REPO_ROOT, "README.md"))
        # The table format: | 🌪️ Supercell | ...
        assert "Supercell" in readme
        # Must be in the intensity table section
        table_section = _extract_section(readme, "Review Intensity Levels")
        assert table_section is not None, "Review Intensity Levels section not found"
        assert "Supercell" in table_section

    def test_readme_architecture_diagram_has_supercell(self):
        """Architecture diagram must show Supercell in the intensity progression."""
        readme = _read(os.path.join(REPO_ROOT, "README.md"))
        # Pattern: Breeze → ... → Tempest → Supercell
        assert "Tempest → Supercell" in readme or "Tempest→Supercell" in readme

    def test_skill_escalation_table_has_supercell(self):
        """Adaptive reviewer SKILL.md must include Supercell escalation."""
        skill_path = os.path.join(REPO_ROOT, "organs", "adaptive-reviewer", "SKILL.md")
        if not os.path.isfile(skill_path):
            pytest.skip("adaptive-reviewer SKILL.md not found")
        skill = _read(skill_path)
        assert "Supercell" in skill, "Missing Supercell in adaptive-reviewer SKILL.md"

    def test_skill_escalation_table_has_all_levels(self):
        """Adaptive reviewer escalation table must reference all levels."""
        skill_path = os.path.join(REPO_ROOT, "organs", "adaptive-reviewer", "SKILL.md")
        if not os.path.isfile(skill_path):
            pytest.skip("adaptive-reviewer SKILL.md not found")
        skill = _read(skill_path)
        for level in INTENSITY_LEVELS:
            assert level in skill, (
                f"Missing intensity level '{level}' in adaptive-reviewer SKILL.md"
            )

    def test_intensity_hierarchy_order_in_readme(self):
        """Intensity levels must appear in ascending order in the README table."""
        readme = _read(os.path.join(REPO_ROOT, "README.md"))
        table_section = _extract_section(readme, "Review Intensity Levels")
        assert table_section is not None
        positions = []
        for level in INTENSITY_LEVELS:
            pos = table_section.find(level)
            assert pos >= 0, f"{level} not in Review Intensity Levels section"
            positions.append(pos)
        # Each level should appear after the previous one
        for i in range(1, len(positions)):
            assert positions[i] > positions[i - 1], (
                f"{INTENSITY_LEVELS[i]} appears before {INTENSITY_LEVELS[i-1]} in table"
            )


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _extract_section(text, heading):
    """Extract content from a markdown heading to the next heading of same or higher level."""
    pattern = rf"^(#{{1,3}})\s+{re.escape(heading)}\s*$"
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return None
    start = match.end()
    level = len(match.group(1))
    # Find next heading of same or higher level
    next_heading = re.search(rf"^#{{1,{level}}}\s+", text[start:], re.MULTILINE)
    if next_heading:
        return text[start:start + next_heading.start()]
    return text[start:]
