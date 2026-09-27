#!/usr/bin/env python3
import os
import sys
import argparse
import glob
import json
import yaml
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description="Compute fitness of governance cells")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--prune", action="store_true", help="List cells recommended for removal")
    parser.add_argument("--promote", action="store_true", help="List cells ready for cross-repo promotion")
    args = parser.parse_args()

    cells_dir = os.path.join(os.path.dirname(__file__), '..', '.gemini', 'cells')
    cell_files = glob.glob(os.path.join(cells_dir, '**', '*.md'), recursive=True)

    results = []

    for file_path in cell_files:
        if os.path.basename(file_path) == 'README.md':
            continue
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        if not content.startswith('---'):
            continue
        
        end_idx = content.find('---', 3)
        if end_idx == -1:
            continue
        
        frontmatter = content[3:end_idx].strip()
        try:
            metadata = yaml.safe_load(frontmatter)
        except Exception:
            continue
        
        cell_name = os.path.basename(file_path)
        cell_type = metadata.get('type', 'unknown')
        fitness = metadata.get('fitness', {})
        triggers = fitness.get('triggers', 0)
        tp = fitness.get('true_positives', 0)
        fp = fitness.get('false_positives', 0)
        impact_weight = metadata.get('impact_weight', 1.0)
        
        if triggers == 0:
            score = None
        else:
            score = (tp / triggers) * impact_weight
            
        expiry_days = metadata.get('expiry_days')
        created_str = metadata.get('created')
        status = "NEW"
        
        if score is not None:
            if score > 0.7:
                status = "SURVIVE"
            elif 0.3 <= score <= 0.7:
                status = "ADAPT"
            else:
                status = "EXTINCT"
        else:
            if expiry_days and created_str:
                try:
                    created_date = datetime.strptime(created_str, "%Y-%m-%d")
                    current_date = datetime.now()
                    days_since_created = (current_date - created_date).days
                    if days_since_created > expiry_days:
                        status = "DORMANT"
                    else:
                        status = "NEW"
                except Exception:
                    status = "NEW"

        results.append({
            "cell": cell_name,
            "type": cell_type,
            "triggers": triggers,
            "tp": tp,
            "fp": fp,
            "score": score,
            "status": status
        })

    if args.prune:
        results = [r for r in results if r['status'] in ("EXTINCT", "DORMANT")]
    elif args.promote:
        results = [r for r in results if r['score'] is not None and r['score'] > 0.7]

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"{'Cell':<20} | {'Type':<12} | {'Triggers':<8} | {'TP':<4} | {'FP':<4} | {'Score':<6} | {'Status':<10}")
        print("-" * 75)
        for r in results:
            score_str = f"{r['score']:.2f}" if r['score'] is not None else "null"
            print(f"{r['cell']:<20} | {r['type']:<12} | {r['triggers']:<8} | {r['tp']:<4} | {r['fp']:<4} | {score_str:<6} | {r['status']:<10}")

if __name__ == "__main__":
    main()
