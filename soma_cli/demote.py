"""soma demote — evaluate and display cell demotion candidates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def run_demote(args: argparse.Namespace) -> int:
    """Evaluate demotion candidates and display results.
    
    Returns 0 always (dry-run is advisory).
    """
    from immune_system.verification.lifecycle import evaluate_demotions

    project_root = getattr(args, "_project_root", Path.cwd())
    project_root = Path(project_root)
    use_json = getattr(args, "json", False)
    
    candidates = evaluate_demotions(str(project_root))
    
    if use_json:
        print(json.dumps({"candidates": candidates}, indent=2, default=str))
    else:
        if not candidates:
            print("  No demotion candidates found.")
        else:
            print(f"  ⚠️  Demotion Candidates ({len(candidates)}):")
            print()
            for c in candidates:
                print(f"    {c['cell_id']}: {c['from_type']} → {c['to_type']} ({c['reason']})")
                if c['triggers'] > 0:
                    print(f"      triggers={c['triggers']} fp_rate={c['fp_rate']:.0%}")
                else:
                    print(f"      dormant for {c['age_days']}d")
            print()
    
    return 0
