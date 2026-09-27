#!/usr/bin/env python3
import os
import sys
import argparse
import glob
import json
import yaml
from datetime import datetime

def resolve_workspace():
    d = os.path.dirname(os.path.abspath(__file__))
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, "rules")) and os.path.isdir(os.path.join(d, "skills")):
            return d
        d = os.path.dirname(d)
    return os.getcwd()

def resolve_metrics_dir(workspace):
    metrics_repo = os.environ.get("METRICS_REPO")
    if not metrics_repo:
        conf_path = os.path.join(workspace, "steering.conf")
        if os.path.exists(conf_path):
            with open(conf_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("METRICS_REPO=") and not line.startswith("#"):
                        metrics_repo = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    if metrics_repo:
        return os.path.expanduser(metrics_repo)
    return os.path.join(workspace, "docs", "snapshots")

def main():
    parser = argparse.ArgumentParser(description="Promote cells to global rules.")
    parser.add_argument("--local", action="store_true", help="Single-repo mode: fitness > 0.85 and >=20 triggers")
    parser.add_argument("--execute", action="store_true", help="Create rule file (marked manual) instead of dry-run")
    args = parser.parse_args()
    
    dry_run = not args.execute
    workspace = resolve_workspace()
    metrics_dir = resolve_metrics_dir(workspace)
    fitness_log_path = os.path.join(metrics_dir, "fitness.jsonl")
    
    candidates = []
    
    if args.local:
        cells_dir = os.path.join(workspace, '.gemini', 'cells')
        cell_files = glob.glob(os.path.join(cells_dir, '**', '*.md'), recursive=True)
        for file_path in cell_files:
            if os.path.basename(file_path) == 'README.md': continue
            with open(file_path, 'r') as f: content = f.read()
            if not content.startswith('---'): continue
            end_idx = content.find('---', 3)
            if end_idx == -1: continue
            
            try:
                metadata = yaml.safe_load(content[3:end_idx].strip())
            except: continue
            
            fitness = metadata.get('fitness', {})
            triggers = fitness.get('triggers', 0)
            tp = fitness.get('true_positives', 0)
            impact = metadata.get('impact_weight', 1.0)
            if triggers == 0: continue
            score = (tp / triggers) * impact
            
            if score > 0.85 and triggers >= 20:
                candidates.append({
                    "cell_name": os.path.basename(file_path),
                    "repo": "local",
                    "score": score,
                    "hypothesis": metadata.get('hypothesis', ''),
                    "prediction": metadata.get('prediction', ''),
                    "triggers": triggers
                })
    else:
        snapshots = glob.glob(os.path.join(metrics_dir, '**', '*.json'), recursive=True)
        hypothesis_stats = {}
        for snap in snapshots:
            try:
                with open(snap, 'r') as f: data = json.load(f)
                if not isinstance(data, list): continue
                filename = os.path.basename(snap)
                inferred_repo = filename.split('-')[0] if '-' in filename else filename.split('.')[0]
                
                for item in data:
                    if 'hypothesis' in item and 'score' in item and item['score'] is not None:
                        hyp = item['hypothesis']
                        repo = item.get('repo', inferred_repo)
                        if hyp not in hypothesis_stats:
                            hypothesis_stats[hyp] = {
                                'repos': set(), 'scores': [], 'cell_name': item.get('cell', 'unknown.md'),
                                'prediction': item.get('prediction', '')
                            }
                        hypothesis_stats[hyp]['repos'].add(repo)
                        hypothesis_stats[hyp]['scores'].append(item['score'])
            except: continue
            
        for hyp, stats in hypothesis_stats.items():
            avg_score = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else 0
            if avg_score > 0.7 and len(stats['repos']) >= 3:
                candidates.append({
                    "cell_name": stats['cell_name'],
                    "repo": f"{len(stats['repos'])} repos",
                    "score": avg_score,
                    "hypothesis": hyp,
                    "prediction": stats['prediction'],
                    "triggers": 0
                })
                
    if not candidates:
        print("No candidates found for promotion.")
        return
        
    print(f"Found {len(candidates)} candidate(s) for promotion.\n")
    
    promotions = []
    
    for cand in candidates:
        safe_name = cand['cell_name'].replace('.md', '').replace('_', '-')
        rule_name = f"rule-{safe_name}.md"
        rule_path = os.path.join(workspace, "rules", rule_name)
        
        rule_content = f"""---
name: Promoted Rule - {safe_name}
description: Auto-promoted global rule
trigger: manual
# Promoted from cell: {cand['cell_name']}, repo: {cand['repo']}, fitness: {cand['score']:.2f}
---

# {cand['hypothesis']}

> **Enforcement**: {cand['prediction']}

## Details
This rule was promoted from local cell {cand['cell_name']} after demonstrating high fitness.
"""
        if dry_run:
            print(f"[DRY-RUN] Would create {rule_path}")
            print(f"  Hypothesis: {cand['hypothesis']}")
            print(f"  Score: {cand['score']:.2f}\n")
        else:
            with open(rule_path, 'w') as f:
                f.write(rule_content)
            print(f"Created {rule_path}")
            promotions.append({
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "type": "speciation",
                "original_cell": cand['cell_name'],
                "new_rule": rule_name,
                "score": cand['score']
            })
            
    if not dry_run and promotions:
        os.makedirs(os.path.dirname(fitness_log_path), exist_ok=True)
        with open(fitness_log_path, 'a') as f:
            for promo in promotions:
                f.write(json.dumps(promo) + "\n")
        print(f"Logged {len(promotions)} promotions to {fitness_log_path}")

if __name__ == "__main__":
    main()
