#!/usr/bin/env python3
import os
import sys
import argparse
import glob
import json
import yaml
from datetime import datetime
from prism_resolve import resolve_workspace

def decayed_fitness(raw_score, last_trigger_date, half_life_days=30):
    if last_trigger_date is None or raw_score is None:
        return raw_score
    days_since = (datetime.now() - last_trigger_date).days
    decay_factor = 0.5 ** (days_since / half_life_days)
    return round(raw_score * decay_factor, 4)

def main():
    parser = argparse.ArgumentParser(description="Compute fitness of governance cells")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--prune", action="store_true", help="List cells recommended for removal")
    parser.add_argument("--promote", action="store_true", help="List cells ready for cross-repo promotion")
    parser.add_argument("--cross-repo", action="store_true", help="Aggregate fitness across multiple repos in METRICS_REPO")
    args = parser.parse_args()

    workspace = resolve_workspace(__file__)
    cells_dir = os.path.join(workspace, '.prism', 'cells')
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
            
        last_trigger_date_str = fitness.get('last_trigger_date')
        last_trigger_date = None
        if last_trigger_date_str:
            try:
                # Handle ISO format strings
                last_trigger_date = datetime.fromisoformat(last_trigger_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
            except Exception:
                pass
                
        type_upper = cell_type.upper()
        hl_val = os.environ.get(f'CELL_HALF_LIFE_{type_upper}')
        if hl_val is None:
            hl_val = os.environ.get('CELL_HALF_LIFE_DAYS', '30')
            
        if hl_val == 'null':
            dec_score = score
        else:
            half_life_days = int(hl_val)
            dec_score = decayed_fitness(score, last_trigger_date, half_life_days)
            
        expiry_days = metadata.get('expiry_days')
        created_str = metadata.get('created')
        status = "NEW"
        
        # Apoptosis: immediate eviction if false positives dominate
        if fp > 0 and tp > 0 and fp > 2 * tp:
            status = "APOPTOSIS"
        elif dec_score is not None:
            if dec_score > 0.7:
                status = "SURVIVE"
            elif 0.3 <= dec_score <= 0.7:
                status = "ADAPT"
            else:
                status = "EXTINCT"
        else:
            if expiry_days and created_str:
                try:
                    fmt = "%Y-%m-%dT%H:%M:%SZ" if 'T' in created_str else "%Y-%m-%d"
                    created_date = datetime.strptime(created_str, fmt)
                    current_date = datetime.now()
                    days_since_created = (current_date - created_date).days
                    if days_since_created > expiry_days:
                        status = "DORMANT"
                    else:
                        status = "NEW"
                except Exception:
                    status = "NEW"

        decay_to = metadata.get('decay_to')
        if status in ("EXTINCT", "DORMANT") and decay_to:
            new_type = decay_to.get('type', 'membrane')
            metadata['type'] = new_type
            metadata['impact_weight'] = decay_to.get('impact_weight', 1.0)
            metadata['minimum_mode'] = decay_to.get('minimum_mode', 'trident')
            if 'response_type' in decay_to:
                metadata['response_type'] = decay_to['response_type']
            if 'activation' in decay_to:
                metadata['activation'] = decay_to['activation']
            del metadata['decay_to']
            
            if 'fitness' not in metadata:
                metadata['fitness'] = {}
            metadata['fitness']['score'] = 0.5
            metadata['fitness']['triggers'] = 0
            metadata['fitness']['true_positives'] = 0
            metadata['fitness']['false_positives'] = 0
            
            gen = metadata.get('lineage', {}).get('generation', 0) if isinstance(metadata.get('lineage'), dict) else 0
            metadata['lineage'] = {
                'parent_id': cell_name,
                'created_by': "decay",
                'generation': gen + 1,
                'siblings': []
            }
            
            target_plural = new_type + "s" if new_type != "plasmodesmata" else "plasmodesmata"
            target_dir = os.path.join(workspace, '.prism', 'cells', target_plural)
            os.makedirs(target_dir, exist_ok=True)
            new_path = os.path.join(target_dir, cell_name)
            
            end_idx = content.find('---', 3)
            body_str = content[end_idx+3:]
            
            with open(new_path, 'w') as out_f:
                out_f.write("---\n")
                yaml.dump(metadata, out_f, default_flow_style=False, sort_keys=False)
                out_f.write("---\n")
                if body_str.startswith('\n'):
                    out_f.write(body_str[1:])
                else:
                    out_f.write(body_str)
                    
            if os.path.abspath(new_path) != os.path.abspath(file_path):
                os.remove(file_path)
                
            status = "TRANSFORMED"
            
            metrics_dir = os.path.join(workspace, '.prism', 'metrics')
            os.makedirs(metrics_dir, exist_ok=True)
            with open(os.path.join(metrics_dir, 'decay_transitions.jsonl'), 'a') as mf:
                mf.write(json.dumps({
                    'timestamp': datetime.utcnow().isoformat() + "Z",
                    'cell_id': cell_name,
                    'from_type': cell_type,
                    'to_type': new_type
                }) + '\n')

        results.append({
            "cell": cell_name,
            "type": cell_type,
            "hypothesis": metadata.get('hypothesis', ''),
            "triggers": triggers,
            "tp": tp,
            "fp": fp,
            "score": score,
            "decayed_score": dec_score,
            "status": status
        })

    if args.prune:
        results = [r for r in results if r['status'] in ("EXTINCT", "DORMANT")]
    elif args.promote:
        results = [r for r in results if r['score'] is not None and r['score'] > 0.7]

    if args.cross_repo:
        def resolve_metrics_dir(workspace):
            team_repo = os.environ.get("TEAM_REPO")
            team_member = os.environ.get("TEAM_MEMBER_ID", "local_user")
            metrics_repo = os.environ.get("METRICS_REPO")
            if not team_repo or not metrics_repo:
                conf_path = os.path.join(workspace, "steering.conf")
                if os.path.exists(conf_path):
                    with open(conf_path) as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("TEAM_REPO=") and not line.startswith("#"):
                                team_repo = line.split("=", 1)[1].strip().strip('"').strip("'")
                            elif line.startswith("TEAM_MEMBER_ID=") and not line.startswith("#"):
                                team_member = line.split("=", 1)[1].strip().strip('"').strip("'")
                            elif line.startswith("METRICS_REPO=") and not line.startswith("#"):
                                metrics_repo = line.split("=", 1)[1].strip().strip('"').strip("'")
            if team_repo:
                # We return the root of snapshots so we can scan */*
                path = os.path.join(os.path.expanduser(team_repo), "snapshots")
                return path
            if metrics_repo:
                return os.path.expanduser(metrics_repo)
            return os.path.join(workspace, "docs", "snapshots")
            
        workspace = resolve_workspace(__file__)
        metrics_dir = resolve_metrics_dir(workspace)
        
        # Look for JSON files in metrics_dir that might be cell fitness snapshots
        # A cell fitness snapshot is assumed to contain a list of objects with 'hypothesis', 'score', and 'repo'
        # or we infer repo from filename if 'repo' is missing.
        snapshots = glob.glob(os.path.join(metrics_dir, '**', '*.json'), recursive=True)
        
        # Group by hypothesis
        hypothesis_stats = {}
        for snap in snapshots:
            try:
                with open(snap, 'r') as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    continue
                    
                # Infer repo from filename if not in data: e.g. "repoA-fitness.json"
                filename = os.path.basename(snap)
                inferred_repo = filename.split('-')[0] if '-' in filename else filename.split('.')[0]
                
                for item in data:
                    if 'hypothesis' in item and 'score' in item and item['score'] is not None:
                        hyp = item['hypothesis']
                        repo = item.get('repo', inferred_repo)
                        if hyp not in hypothesis_stats:
                            hypothesis_stats[hyp] = {'repos': set(), 'scores': []}
                        hypothesis_stats[hyp]['repos'].add(repo)
                        hypothesis_stats[hyp]['scores'].append(item['score'])
            except Exception:
                continue
                
        cross_repo_results = []
        for hyp, stats in hypothesis_stats.items():
            avg_score = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else 0
            repos_count = len(stats['repos'])
            candidate = "Yes" if avg_score > 0.7 and repos_count >= 3 else "No"
            cross_repo_results.append({
                "hypothesis": hyp,
                "repos": repos_count,
                "avg_fitness": avg_score,
                "candidate": candidate
            })
            
        if args.json:
            print(json.dumps(cross_repo_results, indent=2))
        else:
            print(f"{'Cell Hypothesis':<50} | {'Repos':<5} | {'Avg Fitness':<11} | {'Candidate?':<10}")
            print("-" * 85)
            for r in cross_repo_results:
                hyp = r['hypothesis']
                if len(hyp) > 47:
                    hyp = hyp[:44] + "..."
                print(f"{hyp:<50} | {r['repos']:<5} | {r['avg_fitness']:<11.2f} | {r['candidate']:<10}")
        return

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"{'Cell':<20} | {'Type':<12} | {'Triggers':<8} | {'TP':<4} | {'FP':<4} | {'Raw':<6} | {'Decayed':<7} | {'Status':<10}")
        print("-" * 85)
        for r in results:
            score_str = f"{r['score']:.2f}" if r['score'] is not None else "null"
            dec_score_str = f"{r['decayed_score']:.2f}" if r['decayed_score'] is not None else "null"
            print(f"{r['cell']:<20} | {r['type']:<12} | {r['triggers']:<8} | {r['tp']:<4} | {r['fp']:<4} | {score_str:<6} | {dec_score_str:<7} | {r['status']:<10}")

if __name__ == "__main__":
    main()
