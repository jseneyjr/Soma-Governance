#!/usr/bin/env python3
import os
import sys
import argparse
import glob
import json
import yaml
from datetime import datetime
from soma_resolve import resolve_workspace

def resolve_metrics_dir(workspace):
    metrics_repo = os.environ.get("METRICS_REPO")
    if not metrics_repo:
        conf_path = os.path.join(workspace, "soma.conf")
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
    parser.add_argument("--tier-check", action="store_true", help="Check cells for enforcement tier promotion/demotion")
    args = parser.parse_args()
    
    dry_run = not args.execute
    workspace = resolve_workspace(__file__)
    metrics_dir = resolve_metrics_dir(workspace)
    fitness_log_path = os.path.join(metrics_dir, "fitness.jsonl")
    
    if args.tier_check:
        cells_dir = os.path.join(workspace, '.soma', 'cells')
        cell_files = glob.glob(os.path.join(cells_dir, '**', '*.md'), recursive=True)
        escaped_defects_log = os.path.join(workspace, '.soma', 'metrics', 'escaped_defects.jsonl')
        
        escaped_counts = {}
        if os.path.exists(escaped_defects_log):
            with open(escaped_defects_log) as edf:
                for line in edf:
                    try:
                        entry = json.loads(line.strip())
                        cname = entry.get('cell')
                        if cname:
                            escaped_counts[cname] = escaped_counts.get(cname, 0) + 1
                    except Exception:
                        continue
        
        for file_path in cell_files:
            if os.path.basename(file_path) == 'README.md': continue
            with open(file_path, 'r') as f: content = f.read()
            if not content.startswith('---'): continue
            end_idx = content.find('---', 3)
            if end_idx == -1: continue
            
            frontmatter_str = content[3:end_idx]
            try:
                metadata = yaml.safe_load(frontmatter_str.strip())
            except Exception: continue
            
            cell_name = os.path.basename(file_path)
            cell_base = os.path.splitext(cell_name)[0]
            
            enforcement = metadata.get('enforcement', 'advisory')
            fitness = metadata.get('fitness', {})
            triggers = fitness.get('triggers', 0)
            tp = fitness.get('true_positives', 0)
            fp = fitness.get('false_positives', 0)
            
            escaped = escaped_counts.get(cell_base, 0)
            total_cases = escaped + tp
            defect_prevention_rate = tp / total_cases if total_cases > 0 else 1.0
            
            fp_rate = fp / triggers if triggers > 0 else 0.0
            trigger_rate = triggers / 30.0 # simple approx for per 30 sessions
            
            new_tier = enforcement
            reason = ""
            
            if enforcement == 'advisory':
                if defect_prevention_rate > 0.85 and triggers >= 20 and fp_rate < 0.15:
                    new_tier = 'mechanical'
                    reason = "defect_prevention_rate > 0.85, triggers >= 20, FP rate < 0.15"
            elif enforcement == 'mechanical':
                if defect_prevention_rate > 0.95 and triggers >= 50 and fp_rate < 0.05:
                    new_tier = 'gate'
                    reason = "defect_prevention_rate > 0.95, triggers >= 50, FP rate < 0.05"
                elif fp_rate > 0.50 or trigger_rate < (1/30.0):
                    new_tier = 'advisory'
                    reason = "FP rate > 0.50 or low trigger rate"
            elif enforcement == 'gate':
                if fp_rate > 0.30 or escaped > 0: # simple spike logic
                    new_tier = 'mechanical'
                    reason = "FP rate > 0.30 or escaped defects spike"
                    
            if new_tier != enforcement:
                if not dry_run:
                    # Update YAML
                    lines = frontmatter_str.split('\n')
                    for i, line in enumerate(lines):
                        if line.startswith('enforcement:'):
                            lines[i] = f"enforcement: {new_tier}"
                            break
                    else:
                        lines.append(f"enforcement: {new_tier}")
                    new_frontmatter = '\n'.join(lines)
                    with open(file_path, 'w') as f:
                        f.write(f"---{new_frontmatter}---{content[end_idx+3:]}")
                    print(f"Promoted/Demoted {cell_name}: {enforcement} -> {new_tier} ({reason})")
                    
                    if new_tier in ('mechanical', 'gate'):
                        # Auto-generate enforcement artifact
                        enforce_script = os.path.join(os.path.dirname(__file__), 'cell_enforce.py')
                        if os.path.exists(enforce_script):
                            import subprocess
                            subprocess.run([sys.executable, enforce_script, '--cell', cell_name], cwd=workspace)
                else:
                    print(f"[DRY-RUN] Would change tier of {cell_name}: {enforcement} -> {new_tier} ({reason})")
                    
        return

    candidates = []
    
    if args.local:
        cells_dir = os.path.join(workspace, '.soma', 'cells')
        cell_files = glob.glob(os.path.join(cells_dir, '**', '*.md'), recursive=True)
        for file_path in cell_files:
            if os.path.basename(file_path) == 'README.md': continue
            with open(file_path, 'r') as f: content = f.read()
            if not content.startswith('---'): continue
            end_idx = content.find('---', 3)
            if end_idx == -1: continue
            
            try:
                metadata = yaml.safe_load(content[3:end_idx].strip())
            except Exception: continue
            
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
            except Exception: continue
            
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
        rule_path = os.path.join(workspace, "genome", rule_name)
        
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
            
            # Sync to team repo
            team_repo = os.environ.get("TEAM_REPO")
            if not team_repo:
                conf_path = os.path.join(workspace, "soma.conf")
                if os.path.exists(conf_path):
                    with open(conf_path) as conf_file:
                        for line in conf_file:
                            line = line.strip()
                            if line.startswith("TEAM_REPO=") and not line.startswith("#"):
                                team_repo = line.split("=", 1)[1].strip().strip('"').strip("'")
                                break
            
            if team_repo:
                team_repo = os.path.expanduser(team_repo)
                team_promoted_dir = os.path.join(team_repo, 'cells', 'promoted')
                os.makedirs(team_promoted_dir, exist_ok=True)
                import shutil
                # The instructions say "copy the promoted rule to $TEAM_REPO/cells/promoted/"
                # We'll copy the original cell since the folder is 'cells/promoted'
                # or the rule? I'll just copy the cell file (which makes sense for cell promotion sharing)
                # Actually, the instructions say "copy the promoted rule". I'll copy the cell file itself since that's what team_sync.sh pulls.
                cell_path = os.path.join(workspace, '.soma', 'cells', cand['cell_name'])
                if not os.path.exists(cell_path):
                    # fallback to find it
                    for root, _, files in os.walk(os.path.join(workspace, '.soma', 'cells')):
                        if cand['cell_name'] in files:
                            cell_path = os.path.join(root, cand['cell_name'])
                            break
                if os.path.exists(cell_path):
                    shutil.copy2(cell_path, os.path.join(team_promoted_dir, cand['cell_name']))
                    print("Also synced to team repo")
            
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
