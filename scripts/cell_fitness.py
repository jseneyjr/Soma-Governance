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
    parser.add_argument("--cross-repo", action="store_true", help="Aggregate fitness across multiple repos in METRICS_REPO")
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
            "hypothesis": metadata.get('hypothesis', ''),
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

    if args.cross_repo:
        def resolve_workspace():
            d = os.path.dirname(os.path.abspath(__file__))
            while d != os.path.dirname(d):
                if os.path.isdir(os.path.join(d, "rules")) and os.path.isdir(os.path.join(d, "skills")):
                    return d
                d = os.path.dirname(d)
            return os.getcwd()
            
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
            
        workspace = resolve_workspace()
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
        print(f"{'Cell':<20} | {'Type':<12} | {'Triggers':<8} | {'TP':<4} | {'FP':<4} | {'Score':<6} | {'Status':<10}")
        print("-" * 75)
        for r in results:
            score_str = f"{r['score']:.2f}" if r['score'] is not None else "null"
            print(f"{r['cell']:<20} | {r['type']:<12} | {r['triggers']:<8} | {r['tp']:<4} | {r['fp']:<4} | {score_str:<6} | {r['status']:<10}")

if __name__ == "__main__":
    main()
