#!/usr/bin/env bash
set -euo pipefail

EXECUTE=false
if [[ "${1:-}" == "--execute" ]]; then
  EXECUTE="--execute"
fi

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/cell_fitness.py"

# Wraps cell_fitness.py. If it doesn't exist yet, we parse it ourselves.
python3 - "$EXECUTE" "$SCRIPT_DIR" << 'PYEOF'
import os, sys, re, json, datetime, shutil

execute_mode = len(sys.argv) > 1 and sys.argv[1] == '--execute'
script_dir = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()

# Walk up from CWD to find project root with .prism/cells/
def resolve_workspace():
    if os.environ.get("PRISM_ROOT") and os.path.isdir(os.environ.get("PRISM_ROOT")):
        return os.environ.get("PRISM_ROOT")
    d = os.getcwd()
    while d != os.path.dirname(d):
        if "/vendor/" in d or d.endswith("/vendor"):
            d = os.path.dirname(d)
            continue
        if os.path.isdir(os.path.join(d, ".prism", "cells")):
            return d
        d = os.path.dirname(d)
    return os.getcwd()

repo_root = resolve_workspace()

cells_dir = os.path.join(repo_root, ".prism", "cells")
archive_dir = os.path.join(cells_dir, ".archive")
fitness_log = os.path.join(cells_dir, "fitness.jsonl")

if not os.path.exists(cells_dir):
    print("No cells directory found.")
    sys.exit(0)

print(f"Running cell selection (execute={execute_mode})...")

if execute_mode:
    os.makedirs(archive_dir, exist_ok=True)

for root, dirs, files in os.walk(cells_dir):
    if ".archive" in root: continue
    for f in files:
        if not f.endswith(".md") or f == "README.md": continue
        fpath = os.path.join(root, f)
        
        with open(fpath, 'r') as file:
            content = file.read()
            
        fm_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not fm_match: continue
        fm = fm_match.group(1)
        
        def get_val(key, default=0):
            m = re.search(fr'{key}:\s*(\S+)', fm)
            if m and m.group(1) != 'null': return float(m.group(1))
            return default
            
        triggers = get_val('triggers', 0)
        tp = get_val('true_positives', 0)
        dormant = ('dormant_since' in fm)
        
        if triggers == 0:
            category = "DORMANT"
            score = 0.0
        else:
            score = tp / triggers
            if score > 0.7: category = "SURVIVE"
            elif score >= 0.3: category = "ADAPT"
            else: category = "EXTINCT"
            
        print(f"[{category}] {f} (Score: {score:.2f})")
        
        if execute_mode:
            action = None
            if category == "EXTINCT":
                dest = os.path.join(archive_dir, f)
                shutil.move(fpath, dest)
                action = "moved_to_archive"
            elif category == "DORMANT" and not dormant:
                timestamp = datetime.datetime.utcnow().isoformat() + "Z"
                new_content = content.replace("fitness:", f"dormant_since: {timestamp}\nfitness:")
                with open(fpath, 'w') as file:
                    file.write(new_content)
                action = "marked_dormant"
                
            if action:
                with open(fitness_log, 'a') as log:
                    log.write(json.dumps({"timestamp": datetime.datetime.utcnow().isoformat() + "Z", "cell": f, "action": action}) + "\n")
PYEOF
