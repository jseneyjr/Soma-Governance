#!/usr/bin/env python3
"""Outcome Engine — Automated execution feedback for Soma cell fitness.

Captures test results, git signals, and rework patterns to update
cell fitness scores without requiring user interaction.
"""
import os, sys, subprocess, json, re, glob, fnmatch
from datetime import datetime

def resolve_workspace():
    """Find the project root containing .soma/cells/."""
    soma_root = os.environ.get("SOMA_ROOT")
    if soma_root and os.path.isdir(os.path.join(soma_root, ".soma", "cells")):
        return os.path.abspath(soma_root)

    cwd = os.getcwd()
    if os.path.isdir(os.path.join(cwd, ".soma", "cells")):
        return cwd

    d = cwd
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, ".soma", "cells")):
            return d
        d = os.path.dirname(d)
        
    return cwd

def capture_test_signals(workspace):
    """Check if tests passed/failed in this session."""
    signals = {'detected': False, 'passed': None, 'framework': None}
    try:
        # Check for pytest results, jest results, go test, etc.
        if os.path.exists(os.path.join(workspace, '.pytest_cache')) or os.path.exists(os.path.join(workspace, 'pytest.xml')):
            signals['detected'] = True
            signals['framework'] = 'pytest'
            # Naive passed check: if tests failed, git log might have "fix: test"
        
        log_out = subprocess.check_output(['git', 'log', '-1', '--format=%s'], cwd=workspace, text=True).lower()
        if 'test' in log_out or 'fix' in log_out:
            signals['detected'] = True
            signals['passed'] = True
    except Exception:
        pass
    return signals

def capture_git_signals(workspace):
    """Check for reverts, rework, force-pushes."""
    signals = {'reverts': 0, 'fixups': 0, 'rework_files': [], 'force_pushes': 0}
    try:
        log_out = subprocess.check_output(['git', 'log', '--oneline', '-5'], cwd=workspace, text=True).lower()
        signals['reverts'] = log_out.count('revert')
        signals['fixups'] = log_out.count('fixup') + log_out.count('wip')
    except Exception:
        pass
    return signals

def capture_rework_signals(workspace):
    """Detect files touched multiple times in recent commits."""
    signals = {'rework_count': 0, 'rework_files': []}
    try:
        log_out = subprocess.check_output(['git', 'log', '--name-only', '--format=', '-5'], cwd=workspace, text=True)
        files = log_out.splitlines()
        from collections import Counter
        counts = Counter([f for f in files if f])
        rework_files = [f for f, c in counts.items() if c > 1]
        signals['rework_files'] = rework_files
        signals['rework_count'] = len(rework_files)
    except Exception:
        pass
    return signals

def capture_mcp_outcomes(workspace):
    """Read any soma_report_outcome calls."""
    outcomes_file = os.path.join(workspace, '.soma', 'outcomes.jsonl')
    outcomes = []
    if not os.path.isfile(outcomes_file):
        return outcomes
    try:
        with open(outcomes_file, 'r') as f:
            for line in f:
                if line.strip():
                    outcomes.append(json.loads(line))
    except Exception:
        pass
    return outcomes

def _parse_frontmatter_stdlib(content):
    """Parse YAML frontmatter using only stdlib (no pyyaml required)."""
    if not content.startswith('---'):
        return {}
    end = content.find('---', 3)
    if end == -1:
        return {}
    fm_text = content[3:end].strip()
    result = {}
    current_key = None
    current_list = None
    for line in fm_text.split('\n'):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if stripped.startswith('- ') and current_key and current_list is not None:
            val = stripped[2:].strip().strip('"').strip("'")
            current_list.append(val)
            result[current_key] = current_list
            continue
        match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.*)', stripped)
        if match:
            key = match.group(1)
            val = match.group(2).strip()
            if val == '' or val == '|' or val == '>':
                current_key = key
                current_list = []
                result[key] = val
            elif val.startswith('[') and val.endswith(']'):
                items = [v.strip().strip('"').strip("'") for v in val[1:-1].split(',') if v.strip()]
                result[key] = items
                current_key = key
                current_list = None
            else:
                result[key] = val.strip('"').strip("'")
                current_key = key
                current_list = None
        else:
            current_list = None
    return result

def _get_changed_files(workspace):
    """Get changed files using git."""
    try:
        out1 = subprocess.check_output(['git', 'diff', '--name-only'], cwd=workspace, text=True)
        out2 = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD~5', 'HEAD'], cwd=workspace, text=True)
        files = set(out1.splitlines() + out2.splitlines())
        return [f for f in files if f]
    except Exception:
        return []

def match_cells_to_changes(workspace, changed_files):
    """Match cells to changed files using target_paths."""
    triggered = []
    cells_dir = os.path.join(workspace, '.soma', 'cells')
    if not os.path.isdir(cells_dir):
        return triggered
        
    for cell_file in glob.glob(os.path.join(cells_dir, '**', '*.md'), recursive=True):
        if os.path.basename(cell_file) == 'README.md':
            continue
        try:
            with open(cell_file, 'r') as f:
                content = f.read()
            fm = _parse_frontmatter_stdlib(content)
            target_paths = fm.get('target_paths', [])
            if isinstance(target_paths, str):
                target_paths = [target_paths]
                
            matched = False
            for fpath in changed_files:
                for tp in target_paths:
                    if fnmatch.fnmatch(fpath, tp):
                        matched = True
                        break
                if matched:
                    break
            
            if matched:
                fm['_name'] = os.path.splitext(os.path.basename(cell_file))[0]
                fm['_path'] = cell_file
                triggered.append(fm)
        except Exception:
            pass
    return triggered

def compute_fitness_signals(triggered_cells, outcomes):
    """Compute tp/fp signals for each triggered cell."""
    results = []
    for cell in triggered_cells:
        signal = 0  # -1 = false positive, 0 = no signal, +1 = true positive
        
        # If tests passed and cell was triggered → weak positive
        if outcomes.get('tests', {}).get('passed'):
            signal += 0.5
        
        # If rework detected on cell's target files → negative signal
        rework_files = outcomes.get('git', {}).get('rework_files', [])
        cell_targets = cell.get('target_paths', [])
        if isinstance(cell_targets, str):
            cell_targets = [cell_targets]
            
        for rf in rework_files:
            for tp in cell_targets:
                if fnmatch.fnmatch(rf, tp):
                    signal -= 0.5
        
        # If revert detected → strong negative
        if outcomes.get('git', {}).get('reverts', 0) > 0:
            signal -= 1.0
            
        # Ensure bounds
        signal = max(-1.0, min(1.0, signal))
        results.append({'cell': cell['_name'], '_path': cell['_path'], 'signal': signal})
    return results

def update_cell_fitness(workspace, fitness_signals):
    """Update cell frontmatter with fitness signals."""
    for sig in fitness_signals:
        fpath = sig['_path']
        signal = sig['signal']
        try:
            with open(fpath, 'r') as f:
                content = f.read()
            
            def inc(m): return f"{m.group(1)}{int(m.group(2)) + 1}"
            
            content = re.sub(r'(triggers:\s*)(\d+)', inc, content)
            if signal > 0:
                content = re.sub(r'(true_positives:\s*)(\d+)', inc, content)
            elif signal < 0:
                content = re.sub(r'(false_positives:\s*)(\d+)', inc, content)
                
            with open(fpath, 'w') as f:
                f.write(content)
        except Exception:
            pass

def append_fitness_log(workspace, fitness_signals, outcomes):
    """Append to .soma/cells/fitness.jsonl"""
    log_path = os.path.join(workspace, '.soma', 'cells', 'fitness.jsonl')
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    try:
        with open(log_path, 'a') as f:
            for sig in fitness_signals:
                entry = {
                    'timestamp': timestamp,
                    'cell': sig['cell'],
                    'signal': sig['signal'],
                    'outcomes': {
                        'tests_passed': outcomes.get('tests', {}).get('passed'),
                        'reverts': outcomes.get('git', {}).get('reverts', 0),
                        'rework_count': outcomes.get('rework', {}).get('rework_count', 0)
                    }
                }
                f.write(json.dumps(entry) + '\n')
    except Exception:
        pass

def main():
    workspace = resolve_workspace()
    cells_dir = os.path.join(workspace, '.soma', 'cells')
    if not os.path.isdir(cells_dir):
        return  # Graceful no-op
    
    # Capture all signals
    outcomes = {
        'tests': capture_test_signals(workspace),
        'git': capture_git_signals(workspace),
        'rework': capture_rework_signals(workspace)
    }
    
    # Also read MCP-reported outcomes
    mcp_outcomes = capture_mcp_outcomes(workspace)
    if mcp_outcomes:
        outcomes['mcp'] = mcp_outcomes
    
    # Get changed files
    changed_files = _get_changed_files(workspace)
    
    # Match cells to changes
    triggered = match_cells_to_changes(workspace, changed_files)
    
    if not triggered:
        return  # No cells matched
    
    # Compute fitness signals
    signals = compute_fitness_signals(triggered, outcomes)
    
    # Update cells and log
    update_cell_fitness(workspace, signals)
    append_fitness_log(workspace, signals, outcomes)
    
    # Print summary
    print(f'  Outcome engine: {len(signals)} cells evaluated')
    for s in signals:
        indicator = '↑' if s['signal'] > 0 else '↓' if s['signal'] < 0 else '→'
        print(f'    {indicator} {s["cell"]}: signal={s["signal"]:.1f}')

if __name__ == '__main__':
    main()
