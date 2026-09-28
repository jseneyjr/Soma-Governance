#!/usr/bin/env python3
import os, sys, argparse, glob, yaml, json, subprocess
from fnmatch import fnmatch
from datetime import datetime
from prism_resolve import resolve_workspace

def main():
    parser = argparse.ArgumentParser(description='Governance replay: test cells against historical commits')
    parser.add_argument('--commits', type=int, default=20, help='Number of recent commits to replay (default: 20)')
    parser.add_argument('--json', action='store_true', help='JSON output')
    args = parser.parse_args()
    
    workspace = resolve_workspace(__file__)
    cells_dir = os.path.join(workspace, '.prism', 'cells')
    
    # Load all cells
    cells = []
    for cell_file in glob.glob(os.path.join(cells_dir, '**', '*.md'), recursive=True):
        if os.path.basename(cell_file) == 'README.md': continue
        try:
            with open(cell_file) as f: content = f.read()
            if not content.startswith('---'): continue
            fm = yaml.safe_load(content[3:content.find('---', 3)])
            cells.append({
                'name': os.path.splitext(os.path.basename(cell_file))[0],
                'type': fm.get('type', ''),
                'target_paths': fm.get('target_paths', []),
                'hypothesis': fm.get('hypothesis', ''),
                'minimum_mode': fm.get('minimum_mode', 'breeze')
            })
        except: pass
    
    # Get recent commits
    result = subprocess.run(
        ['git', 'log', f'--max-count={args.commits}', '--format=%H %s'],
        capture_output=True, text=True, cwd=workspace
    )
    commits = []
    for line in result.stdout.strip().split('\n'):
        if not line: continue
        sha, *msg = line.split(' ')
        commits.append({'sha': sha, 'message': ' '.join(msg)})
    
    replay_results = []
    for commit in commits:
        # Get files changed in this commit
        diff_result = subprocess.run(
            ['git', 'diff', '--name-only', f'{commit["sha"]}~1', commit['sha']],
            capture_output=True, text=True, cwd=workspace
        )
        changed_files = set(diff_result.stdout.strip().split('\n')) - {''}
        
        # Check which cells would have triggered
        would_trigger = []
        for cell in cells:
            for pattern in cell['target_paths']:
                if any(fnmatch(f, pattern) for f in changed_files):
                    would_trigger.append(cell['name'])
                    break
        
        replay_results.append({
            'sha': commit['sha'][:8],
            'message': commit['message'][:60],
            'files_changed': len(changed_files),
            'cells_would_trigger': len(would_trigger),
            'triggered': would_trigger
        })
    
    if args.json:
        print(json.dumps(replay_results, indent=2))
    else:
        print(f'\n🔄 Governance Replay: {len(commits)} commits × {len(cells)} cells\n')
        total_triggers = sum(r['cells_would_trigger'] for r in replay_results)
        covered = sum(1 for r in replay_results if r['cells_would_trigger'] > 0)
        print(f'Commits with coverage: {covered}/{len(replay_results)} ({covered/len(replay_results)*100:.0f}%)')
        print(f'Total retroactive triggers: {total_triggers}\n')
        for r in replay_results:
            indicator = '✅' if r['cells_would_trigger'] > 0 else '🔴'
            print(f'{indicator} {r["sha"]} ({r["files_changed"]} files, {r["cells_would_trigger"]} cells) {r["message"]}')
            if r['triggered']:
                print(f'   Cells: {", ".join(r["triggered"])}')

if __name__ == '__main__':
    main()
