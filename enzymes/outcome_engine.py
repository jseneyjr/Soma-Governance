#!/usr/bin/env python3
"""Outcome Engine — Verifiable execution feedback for Soma cell fitness.

ACE-aligned reflector: captures REAL outcomes (test exit codes, build status,
git reverts) instead of proxy signals (file existence, commit messages).

Signal hierarchy (strongest → weakest):
  1. Test exit code (ground truth — did pytest/jest/go test PASS?)
  2. Build exit code (did `make build` or equivalent succeed?)
  3. Git reverts/force-pushes (verifiable failure signal)
  4. Rework detection (same file in consecutive commits)
  5. MCP-reported outcomes (agent self-report — weakest)

Reference: ACE (arXiv:2510.04618) — "ACE could adapt effectively without
labeled supervision and instead by leveraging natural execution feedback."
"""

import os
import sys
import subprocess
import json
import re
import glob
import fnmatch
from datetime import datetime


# ── Workspace Resolution ─────────────────────────────────────────────

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


# ── Signal Capture: Verifiable Outcomes ──────────────────────────────

# Timeout for test/build commands (seconds). Don't hang the session.
VERIFY_TIMEOUT = int(os.environ.get('SOMA_VERIFY_TIMEOUT', '60'))


def _run_verify(cmd, cwd, timeout=None):
    """Run a verification command, return (exit_code, stdout_snippet).

    Returns None if the command doesn't exist or times out.
    """
    if timeout is None:
        timeout = VERIFY_TIMEOUT
    try:
        result = subprocess.run(
            cmd, cwd=cwd, shell=True, timeout=timeout,
            capture_output=True, text=True
        )
        # Capture last 10 lines of output for debugging
        stdout_tail = '\n'.join(result.stdout.strip().split('\n')[-10:])
        stderr_tail = '\n'.join(result.stderr.strip().split('\n')[-5:])
        return {
            'exit_code': result.returncode,
            'passed': result.returncode == 0,
            'stdout_tail': stdout_tail[:500],
            'stderr_tail': stderr_tail[:300]
        }
    except subprocess.TimeoutExpired:
        return {'exit_code': -1, 'passed': None, 'error': 'timeout'}
    except FileNotFoundError:
        return None
    except Exception as e:
        return {'exit_code': -1, 'passed': None, 'error': str(e)[:200]}


def detect_test_runner(workspace):
    """Detect which test framework this project uses.

    Returns (command, framework_name) or (None, None).
    Verifies the runner is actually installed before returning.
    """
    checks = [
        # Python — verify pytest is importable
        ('pyproject.toml', 'pytest',
         'python3 -m pytest --tb=short -q --no-header 2>&1',
         'python3 -c "import pytest" 2>/dev/null'),
        ('setup.cfg', 'pytest',
         'python3 -m pytest --tb=short -q --no-header 2>&1',
         'python3 -c "import pytest" 2>/dev/null'),
        ('pytest.ini', 'pytest',
         'python3 -m pytest --tb=short -q --no-header 2>&1',
         'python3 -c "import pytest" 2>/dev/null'),

        # JavaScript/TypeScript — verify jest/vitest exists
        ('jest.config.js', 'jest',
         'npx jest --silent --no-coverage 2>&1',
         'npx jest --version 2>/dev/null'),
        ('jest.config.ts', 'jest',
         'npx jest --silent --no-coverage 2>&1',
         'npx jest --version 2>/dev/null'),
        ('vitest.config.ts', 'vitest',
         'npx vitest run --reporter=dot 2>&1',
         'npx vitest --version 2>/dev/null'),
        ('package.json', 'npm test',
         'npm test 2>&1',
         None),  # package.json always valid if it has a test script

        # Go
        ('go.mod', 'go test',
         'go test ./... -count=1 -short 2>&1',
         'go version 2>/dev/null'),

        # Rust
        ('Cargo.toml', 'cargo test',
         'cargo test --quiet 2>&1',
         'cargo --version 2>/dev/null'),

        # Generic Makefile test target
        ('Makefile', 'make test',
         'make test 2>&1',
         None),
    ]

    for entry in checks:
        marker_file, framework, cmd, verify_cmd = entry[0], entry[1], entry[2], entry[3]
        if not os.path.isfile(os.path.join(workspace, marker_file)):
            continue

        # For package.json, check if there's a "test" script
        if framework == 'npm test':
            try:
                with open(os.path.join(workspace, marker_file)) as f:
                    pkg = json.loads(f.read())
                if 'test' not in pkg.get('scripts', {}):
                    continue
                # Skip if test script is the default placeholder
                test_script = pkg['scripts']['test']
                if 'no test specified' in test_script:
                    continue
            except Exception:
                continue

        # For Makefile, verify 'test' target exists
        if framework == 'make test':
            try:
                targets = subprocess.check_output(
                    'make -qp 2>/dev/null | grep -E "^test:" || true',
                    shell=True, cwd=workspace, text=True
                )
                if 'test:' not in targets:
                    continue
            except Exception:
                continue

        # Verify the runner is actually installed
        if verify_cmd:
            try:
                result = subprocess.run(
                    verify_cmd, shell=True, cwd=workspace,
                    capture_output=True, timeout=10
                )
                if result.returncode != 0:
                    continue  # Runner not installed — skip
            except Exception:
                continue

        return cmd, framework

    return None, None


def capture_test_outcome(workspace):
    """Run the actual test suite and capture the exit code.

    This is the ACE reflector's ground truth signal.
    Returns:
        {
            'verified': True/False,  # Did we actually run tests?
            'passed': True/False/None,
            'framework': str,
            'exit_code': int,
            'detail': str
        }
    """
    # Check if verification is disabled
    if os.environ.get('SOMA_SKIP_VERIFY', '').lower() in ('1', 'true', 'yes'):
        return {'verified': False, 'passed': None, 'reason': 'SOMA_SKIP_VERIFY set'}

    cmd, framework = detect_test_runner(workspace)
    if not cmd:
        return {'verified': False, 'passed': None, 'reason': 'no test runner detected'}

    result = _run_verify(cmd, workspace)
    if result is None:
        return {'verified': False, 'passed': None, 'reason': f'{framework} not installed'}

    return {
        'verified': True,
        'passed': result['passed'],
        'framework': framework,
        'exit_code': result['exit_code'],
        'detail': result.get('stdout_tail', '')[:200],
        'error': result.get('error', result.get('stderr_tail', ''))[:200]
    }


def capture_build_outcome(workspace):
    """Try to build the project if a build system is detected."""
    # Only try if there's a Makefile with a 'build' target
    if not os.path.isfile(os.path.join(workspace, 'Makefile')):
        return {'verified': False, 'passed': None}

    try:
        targets = subprocess.check_output(
            'make -qp 2>/dev/null | grep -E "^build:" || true',
            shell=True, cwd=workspace, text=True
        )
        if 'build:' not in targets:
            return {'verified': False, 'passed': None}
    except Exception:
        return {'verified': False, 'passed': None}

    result = _run_verify('make build 2>&1', workspace, timeout=120)
    if result is None:
        return {'verified': False, 'passed': None}

    return {
        'verified': True,
        'passed': result['passed'],
        'exit_code': result['exit_code']
    }


def capture_git_signals(workspace):
    """Check for reverts and force-pushes — verifiable failure signals."""
    signals = {
        'reverts': 0,
        'fixups': 0,
        'rework_files': [],
        'force_pushes': 0,
        'verified': True  # Git signals are always verifiable
    }

    try:
        # Check last 5 commits for reverts
        log_out = subprocess.check_output(
            ['git', 'log', '--oneline', '-5'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        ).lower()
        signals['reverts'] = log_out.count('revert')
        signals['fixups'] = log_out.count('fixup') + log_out.count('wip')
    except Exception:
        signals['verified'] = False

    try:
        # Check reflog for force-pushes
        reflog = subprocess.check_output(
            ['git', 'reflog', '-5', '--format=%gs'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        ).lower()
        signals['force_pushes'] = reflog.count('push (force')
    except Exception:
        pass

    try:
        # Rework detection: files touched in 2+ of the last 5 commits
        log_out = subprocess.check_output(
            ['git', 'log', '--name-only', '--format=', '-5'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        )
        from collections import Counter
        files = [f for f in log_out.splitlines() if f.strip()]
        counts = Counter(files)
        signals['rework_files'] = [f for f, c in counts.items() if c > 1]
    except Exception:
        pass

    return signals


def capture_mcp_outcomes(workspace):
    """Read any soma_report_outcome calls from this session."""
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


# ── Frontmatter Parser (stdlib only) ─────────────────────────────────

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
                items = [v.strip().strip('"').strip("'")
                         for v in val[1:-1].split(',') if v.strip()]
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


# ── Cell Matching ────────────────────────────────────────────────────

def _get_changed_files(workspace):
    """Get changed files using git."""
    files = set()
    for cmd in ['git diff --name-only', 'git diff --name-only HEAD~5 HEAD']:
        try:
            out = subprocess.check_output(
                cmd, shell=True, cwd=workspace, text=True,
                stderr=subprocess.DEVNULL
            )
            files.update(f for f in out.splitlines() if f.strip())
        except Exception:
            pass
    return list(files)


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
                    if fnmatch.fnmatch(fpath, tp) or fnmatch.fnmatch(os.path.basename(fpath), tp):
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


# ── Fitness Signal Computation (ACE Reflector) ───────────────────────

def compute_fitness_signals(triggered_cells, outcomes):
    """ACE-aligned reflector: score cells based on VERIFIABLE outcomes.

    Signal weights:
      Test exit code:   ±1.0 (ground truth — strongest signal)
      Build exit code:  ±0.7 (strong signal)
      Git reverts:      -1.0 (verifiable failure)
      Rework detection: -0.3 (weak but verifiable)
      MCP self-report:  ±0.2 (weakest — agent grading itself)

    A cell gets NO signal (0.0) if we can't verify the outcome.
    This is intentional: uncertain signals are worse than no signal.
    """
    results = []
    test_outcome = outcomes.get('tests', {})
    build_outcome = outcomes.get('build', {})
    git = outcomes.get('git', {})
    mcp = outcomes.get('mcp', [])

    for cell in triggered_cells:
        signal = 0.0
        reasons = []

        # 1. Test exit code — GROUND TRUTH
        if test_outcome.get('verified') and test_outcome.get('passed') is not None:
            if test_outcome['passed']:
                signal += 1.0
                reasons.append(f"tests passed ({test_outcome.get('framework', '?')})")
            else:
                signal -= 1.0
                reasons.append(f"tests FAILED ({test_outcome.get('framework', '?')})")

        # 2. Build exit code — STRONG SIGNAL
        elif build_outcome.get('verified') and build_outcome.get('passed') is not None:
            if build_outcome['passed']:
                signal += 0.7
                reasons.append("build passed")
            else:
                signal -= 0.7
                reasons.append("build FAILED")

        # 3. Git reverts — VERIFIABLE FAILURE
        if git.get('reverts', 0) > 0:
            signal -= 1.0
            reasons.append(f"{git['reverts']} revert(s) detected")

        # 4. Rework on cell's target files — WEAK BUT VERIFIABLE
        rework_files = git.get('rework_files', [])
        cell_targets = cell.get('target_paths', [])
        if isinstance(cell_targets, str):
            cell_targets = [cell_targets]

        rework_hit = False
        for rf in rework_files:
            for tp in cell_targets:
                if fnmatch.fnmatch(rf, tp):
                    rework_hit = True
                    break
            if rework_hit:
                break
        if rework_hit:
            signal -= 0.3
            reasons.append("rework detected on target files")

        # 5. MCP self-report — WEAKEST (agent grading itself)
        for mcp_entry in mcp:
            cells_used = mcp_entry.get('cells_used', [])
            if cell['_name'] in cells_used:
                outcome = mcp_entry.get('outcome', '')
                if outcome == 'success':
                    signal += 0.2
                    reasons.append("agent reported success")
                elif outcome == 'failure':
                    signal -= 0.2
                    reasons.append("agent reported failure")

        # Clamp to [-2, 2] range
        signal = max(-2.0, min(2.0, signal))

        results.append({
            'cell': cell['_name'],
            '_path': cell['_path'],
            'signal': round(signal, 2),
            'reasons': reasons,
            'verified': test_outcome.get('verified', False) or build_outcome.get('verified', False)
        })

    return results


# ── Cell Fitness Update ──────────────────────────────────────────────

def update_cell_fitness(workspace, fitness_signals):
    """Update cell frontmatter with fitness signals."""
    for sig in fitness_signals:
        fpath = sig['_path']
        signal = sig['signal']
        try:
            with open(fpath, 'r') as f:
                content = f.read()

            def inc(m):
                return f"{m.group(1)}{int(m.group(2)) + 1}"

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
    """Append to .soma/cells/fitness.jsonl with full provenance."""
    log_path = os.path.join(workspace, '.soma', 'cells', 'fitness.jsonl')
    timestamp = datetime.now(tz=__import__('datetime').timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    try:
        with open(log_path, 'a') as f:
            for sig in fitness_signals:
                entry = {
                    'timestamp': timestamp,
                    'cell': sig['cell'],
                    'signal': sig['signal'],
                    'verified': sig.get('verified', False),
                    'reasons': sig.get('reasons', []),
                    'outcomes': {
                        'tests': {
                            'verified': outcomes.get('tests', {}).get('verified', False),
                            'passed': outcomes.get('tests', {}).get('passed'),
                            'framework': outcomes.get('tests', {}).get('framework'),
                        },
                        'build': {
                            'verified': outcomes.get('build', {}).get('verified', False),
                            'passed': outcomes.get('build', {}).get('passed'),
                        },
                        'git': {
                            'reverts': outcomes.get('git', {}).get('reverts', 0),
                            'rework_count': len(outcomes.get('git', {}).get('rework_files', []))
                        }
                    }
                }
                f.write(json.dumps(entry) + '\n')
    except Exception:
        pass


# ── Main ─────────────────────────────────────────────────────────────

def main():
    workspace = resolve_workspace()
    cells_dir = os.path.join(workspace, '.soma', 'cells')
    if not os.path.isdir(cells_dir):
        return  # Graceful no-op

    print("  Running outcome engine (ACE reflector)...")

    # 1. Capture verifiable outcomes
    outcomes = {}

    # Ground truth: run the actual test suite
    print("    Detecting test runner...", end=' ')
    outcomes['tests'] = capture_test_outcome(workspace)
    test_result = outcomes['tests']
    if test_result.get('verified'):
        status = '✅ PASSED' if test_result['passed'] else '❌ FAILED'
        print(f"{test_result.get('framework', '?')} → {status}")
    else:
        print(f"skipped ({test_result.get('reason', 'unknown')})")

    # Build signal
    outcomes['build'] = capture_build_outcome(workspace)

    # Git signals (always verifiable)
    outcomes['git'] = capture_git_signals(workspace)

    # MCP self-reports (weakest signal)
    mcp = capture_mcp_outcomes(workspace)
    if mcp:
        outcomes['mcp'] = mcp

    # 2. Match cells to changed files
    changed_files = _get_changed_files(workspace)
    triggered = match_cells_to_changes(workspace, changed_files)

    if not triggered:
        print("    No cells matched changed files.")
        return

    # 3. Compute fitness signals (ACE reflector step)
    signals = compute_fitness_signals(triggered, outcomes)

    # 4. Update cells and log with full provenance
    update_cell_fitness(workspace, signals)
    append_fitness_log(workspace, signals, outcomes)

    # 5. Print summary
    verified_count = sum(1 for s in signals if s.get('verified'))
    print(f"    {len(signals)} cells evaluated ({verified_count} with verified outcomes)")
    for s in signals:
        indicator = '↑' if s['signal'] > 0 else '↓' if s['signal'] < 0 else '→'
        v = '✓' if s.get('verified') else '?'
        reasons_str = ', '.join(s.get('reasons', [])) or 'no signal'
        print(f"      {indicator} [{v}] {s['cell']}: {s['signal']:+.1f} ({reasons_str})")


if __name__ == '__main__':
    main()
