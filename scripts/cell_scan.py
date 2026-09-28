import sys, json, os, glob, subprocess
import fnmatch

def get_workspace():
    # Fallback if prism_resolve is missing
    return os.getcwd()

try:
    from prism_resolve import resolve_workspace
    workspace = resolve_workspace(__file__)
except ImportError:
    workspace = get_workspace()

def run_cmd(cmd, cwd):
    try:
        return subprocess.check_output(cmd, cwd=cwd, shell=True, text=True).strip().split('\n')
    except:
        return []

changed_files = run_cmd("git diff --name-only HEAD", workspace)
staged_files = run_cmd("git diff --name-only --cached", workspace)

all_changed = set(f for f in changed_files + staged_files if f)

cells_dir = os.path.join(workspace, '.prism', 'cells')
if not os.path.isdir(cells_dir):
    sys.exit(0)

cells = glob.glob(os.path.join(cells_dir, '**', '*.md'), recursive=True)
import yaml

triggered = []
for f in cells:
    if os.path.basename(f) == 'README.md': continue
    try:
        with open(f) as fh: content = fh.read()
        if not content.startswith('---'): continue
        fm = yaml.safe_load(content[3:content.find('---',3)])
        target_paths = fm.get('target_paths', [])
        hypothesis = fm.get('hypothesis', '')
        
        is_triggered = False
        for changed in all_changed:
            for tp in target_paths:
                if fnmatch.fnmatch(changed, tp) or fnmatch.fnmatch(changed, '*' + tp + '*'):
                    is_triggered = True
            
            if os.path.basename(changed) in hypothesis:
                is_triggered = True
                
        if is_triggered:
            triggered.append({
                'name': os.path.basename(f).replace('.md', ''),
                'type': fm.get('type', 'unknown'),
                'minimum_mode': fm.get('minimum_mode', ''),
                'hypothesis': hypothesis
            })
    except: pass

if '--json' in sys.argv:
    print(json.dumps(triggered))
else:
    for t in triggered:
        mode_str = f" [{t['minimum_mode']}]" if t['minimum_mode'] else ""
        print(f"Triggered: {t['name']} ({t['type']}){mode_str} - {t['hypothesis']}")

if '--signal' in sys.argv:
    for t in triggered:
        subprocess.run(["bash", os.path.join(workspace, "scripts", "cell_signal.sh"), t['name'], "tp"], cwd=workspace)
