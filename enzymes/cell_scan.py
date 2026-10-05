import sys, json, os, glob, subprocess
import fnmatch
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from soma_sdk.cells import parse_cell_file

def get_workspace():
    # Fallback if soma_resolve is missing
    return os.getcwd()

try:
    from soma_core.workspace import resolve_workspace
    workspace = resolve_workspace()
except ImportError:
    workspace = get_workspace()

def run_cmd(cmd, cwd):
    try:
        return subprocess.check_output(cmd, cwd=cwd, shell=True, text=True).strip().split('\n')
    except Exception:
        return []

changed_files = run_cmd("git diff --name-only HEAD", workspace)
staged_files = run_cmd("git diff --name-only --cached", workspace)

all_changed = set(f for f in changed_files + staged_files if f)

cells_dir = os.path.join(workspace, '.soma', 'cells')
if not os.path.isdir(cells_dir):
    sys.exit(0)

cells = glob.glob(os.path.join(cells_dir, '**', '*.md'), recursive=True)


triggered = []
for f in cells:
    if os.path.basename(f) == 'README.md': continue
    try:
        fm, _body = parse_cell_file(f)
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
    except Exception as exc:
        sys.stderr.write(f"Warning: Failed to parse cell {f}: {exc}\n")

# Check dormant spores for reactivation
spores_file = os.path.join(workspace, '.soma', 'cells', '.spores.jsonl')
if os.path.exists(spores_file):
    with open(spores_file, encoding="utf-8") as f:
        for line in f:
            try:
                spore = json.loads(line.strip())
                for pattern in spore.get('reactivation_patterns', spore.get('target_paths', [])):
                    if any(fnmatch.fnmatch(cf, pattern) for cf in all_changed):
                        print(f"🧬 SPORE REACTIVATION: Extinct cell '{spore['name']}' matches current changes")
                        print(f"   Hypothesis: {spore['hypothesis'][:80]}")
                        print(f"   Peak fitness: {spore.get('peak_fitness', 'unknown')}")
                        break
            except Exception:
                pass

if '--json' in sys.argv:
    print(json.dumps(triggered))
else:
    for t in triggered:
        mode_str = f" [{t['minimum_mode']}]" if t['minimum_mode'] else ""
        print(f"Triggered: {t['name']} ({t['type']}){mode_str} - {t['hypothesis']}")

if '--signal' in sys.argv:
    for t in triggered:
        subprocess.run(["bash", os.path.join(workspace, "enzymes", "cell_signal.sh"), t['name'], "tp"], cwd=workspace)
