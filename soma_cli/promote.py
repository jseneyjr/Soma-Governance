"""soma promote — evaluate and display cell promotion candidates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def run_promote(args: argparse.Namespace) -> int:
    """Evaluate promotion candidates and display results.
    
    Returns 0 always (dry-run is advisory).
    """
    from immune_system.verification.lifecycle import evaluate_promotions

    project_root = getattr(args, "_project_root", Path.cwd())
    project_root = Path(project_root)
    use_json = getattr(args, "json", False)
    
    candidates = evaluate_promotions(str(project_root))
    
    if use_json:
        print(json.dumps({"candidates": candidates}, indent=2, default=str))
    else:
        if not candidates:
            print("  No promotion candidates found.")
        else:
            print(f"  🧬 Promotion Candidates ({len(candidates)}):")
            print()
            for c in candidates:
                print(f"    {c['cell_id']}: {c['from_type']} → {c['to_type']}")
                print(f"      triggers={c['triggers']} tp_rate={c['tp_rate']:.0%} age={c['age_days']}d")
            print()
    
    return 0
