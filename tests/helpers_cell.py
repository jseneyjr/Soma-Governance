"""Shared test helpers for cell lifecycle tests.

Provides factory functions for creating cell files and JSONL evidence
used by test_cli_promote.py, test_cli_demote.py, test_cli_oracle.py,
test_lifecycle.py, and test_oracle_checkpoint.py.
"""
import json
import os
from datetime import datetime, timedelta

import yaml


def make_cell(cells_dir, name, cell_type="vacuole", created_days_ago=10,
              expiry_days=365, expiry_sessions=100):
    """Create a minimal cell markdown file with YAML frontmatter.

    Args:
        cells_dir: Directory to write the cell file into.
        name: Cell ID and filename stem.
        cell_type: One of vacuole, wall, genome.
        created_days_ago: How old the cell should appear.
        expiry_days: Days until cell expires.
        expiry_sessions: Sessions until cell expires.

    Returns:
        Path to the created cell file.
    """
    created = (datetime.now() - timedelta(days=created_days_ago)).strftime("%Y-%m-%d")
    fm = {
        'id': name,
        'type': cell_type,
        'enforcement': 'advisory',
        'hypothesis': f'Test cell {name}',
        'prediction': 'test',
        'falsification': 'test',
        'target_paths': ['*.py'],
        'expiry_sessions': expiry_sessions,
        'expiry_days': expiry_days,
        'created': created,
    }
    cell_file = os.path.join(str(cells_dir), f"{name}.md")
    with open(cell_file, 'w') as f:
        f.write("---\n")
        f.write(yaml.dump(fm, default_flow_style=False))
        f.write("---\n")
        f.write(f"# {name}\nTest cell.\n")
    return cell_file


def write_evidence(evidence_dir, cell_id, triggers=0, tp=0, fp=0):
    """Write trigger events and outcome records to JSONL evidence files.

    Args:
        evidence_dir: Path to .soma/evidence/ directory.
        cell_id: The cell ID to write evidence for.
        triggers: Number of trigger events to write to fitness.jsonl.
        tp: Number of true positive outcomes to write to outcomes.jsonl.
        fp: Number of false positive outcomes to write to outcomes.jsonl.
    """
    evidence_dir = str(evidence_dir)
    fitness_file = os.path.join(evidence_dir, "fitness.jsonl")
    outcomes_file = os.path.join(evidence_dir, "outcomes.jsonl")

    with open(fitness_file, "a") as f:
        for _ in range(triggers):
            f.write(json.dumps({
                "cell_id": cell_id,
                "triggered_at": datetime.now().isoformat(),
                "matched_files": ["test.py"],
            }) + "\n")

    with open(outcomes_file, "a") as f:
        for _ in range(tp):
            f.write(json.dumps({"cell_id": cell_id, "outcome": "tp"}) + "\n")
        for _ in range(fp):
            f.write(json.dumps({"cell_id": cell_id, "outcome": "fp"}) + "\n")
