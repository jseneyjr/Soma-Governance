"""soma_core.outcomes — Verifiable outcome reflection and credit assignment.

Consolidates:
- Signal reflection: test outcomes, build outcomes, git signals, MCP self-reports, human insights.
- Credit assignment & fitness signals: per-file scope narrowing, overconfidence penalty.
- Markdown cell fitness updater and fitness log appending.
- ACE reflector loop (outcome engine).
- Transcript fitness updater and platform detection.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import fnmatch
from fractions import Fraction
import glob
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
from typing import Any, Optional

from soma_core.workspace import Workspace, as_workspace, resolve_workspace
from soma_core.frontmatter import parse_frontmatter, parse_yaml_subset, _get_body, dump_frontmatter
from soma_core.cell_inventory import find_matching_cells


VERIFY_TIMEOUT = int(os.environ.get('SOMA_VERIFY_TIMEOUT', '60'))


def _run_verify(cmd: str, cwd: str, timeout: Optional[int] = None) -> Optional[dict]:
    """Run a verification command, return (exit_code, stdout_snippet)."""
    if timeout is None:
        timeout = VERIFY_TIMEOUT
    try:
        result = subprocess.run(
            cmd, cwd=cwd, shell=True, timeout=timeout,
            capture_output=True, text=True
        )
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


def detect_test_runner(workspace: str) -> tuple[Optional[str], Optional[str]]:
    """Detect which test framework this project uses. Returns (command, framework_name)."""
    checks = [
        ('pyproject.toml', 'pytest', 'python3 -m pytest --tb=short -q --no-header 2>&1', 'python3 -c "import pytest" 2>/dev/null'),
        ('setup.cfg', 'pytest', 'python3 -m pytest --tb=short -q --no-header 2>&1', 'python3 -c "import pytest" 2>/dev/null'),
        ('pytest.ini', 'pytest', 'python3 -m pytest --tb=short -q --no-header 2>&1', 'python3 -c "import pytest" 2>/dev/null'),
        ('jest.config.js', 'jest', 'npx jest --silent --no-coverage 2>&1', 'npx jest --version 2>/dev/null'),
        ('jest.config.ts', 'jest', 'npx jest --silent --no-coverage 2>&1', 'npx jest --version 2>/dev/null'),
        ('vitest.config.ts', 'vitest', 'npx vitest run --reporter=dot 2>&1', 'npx vitest --version 2>/dev/null'),
        ('package.json', 'npm test', 'npm test 2>&1', None),
        ('go.mod', 'go test', 'go test ./... -count=1 -short 2>&1', 'go version 2>/dev/null'),
        ('Cargo.toml', 'cargo test', 'cargo test --quiet 2>&1', 'cargo --version 2>/dev/null'),
    ]

    for config_file, name, test_cmd, check_cmd in checks:
        if os.path.exists(os.path.join(workspace, config_file)):
            if check_cmd is None or subprocess.run(check_cmd, shell=True, cwd=workspace, capture_output=True).returncode == 0:
                return test_cmd, name

    # Fallback to Makefile test target
    makefile = os.path.join(workspace, 'Makefile')
    if os.path.exists(makefile):
        try:
            with open(makefile, 'r', encoding='utf-8') as f:
                if re.search(r'^test\s*:', f.read(), re.MULTILINE):
                    return 'make test', 'Makefile'
        except Exception:
            pass

    return None, None


def capture_test_outcome(workspace: str) -> dict:
    """Ground truth: run tests and capture exit code."""
    test_cmd, framework = detect_test_runner(workspace)
    if not test_cmd:
        return {'verified': False, 'reason': 'no test runner detected', 'passed': None}

    outcome = _run_verify(test_cmd, cwd=workspace)
    if not outcome or outcome.get('passed') is None:
        return {'verified': False, 'reason': outcome.get('error', 'test execution failed') if outcome else 'failed to run', 'passed': None, 'framework': framework}

    return {
        'verified': True,
        'passed': outcome['passed'],
        'exit_code': outcome['exit_code'],
        'framework': framework,
        'snippet': outcome['stdout_tail'] if not outcome['passed'] else ''
    }


def capture_build_outcome(workspace: str) -> dict:
    """Strong signal: did the build succeed?"""
    build_checks = [
        ('Cargo.toml', 'cargo check --quiet 2>&1'),
        ('package.json', 'npm run build --if-present 2>&1'),
        ('go.mod', 'go vet ./... 2>&1'),
    ]
    for config_file, cmd in build_checks:
        if os.path.exists(os.path.join(workspace, config_file)):
            outcome = _run_verify(cmd, cwd=workspace)
            if outcome and outcome.get('passed') is not None:
                return {
                    'verified': True,
                    'passed': outcome['passed'],
                    'exit_code': outcome['exit_code'],
                    'command': cmd.split()[0]
                }
    return {'verified': False, 'reason': 'no build system detected', 'passed': None}


def capture_git_signals(workspace: str) -> dict:
    """Always verifiable: reverts and rework from git log."""
    signals = {'reverts': 0, 'rework_files': []}
    try:
        log_out = subprocess.check_output(
            ['git', 'log', '--oneline', '-5'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        )
        revert_count = sum(1 for line in log_out.splitlines() if 'revert' in line.lower())
        signals['reverts'] = revert_count
    except Exception:
        pass

    try:
        log_out = subprocess.check_output(
            ['git', 'log', '--name-only', '--format=', '-5'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        )
        files = [f for f in log_out.splitlines() if f.strip()]
        counts = Counter(files)
        signals['rework_files'] = [f for f, c in counts.items() if c > 1]
    except Exception:
        pass

    return signals


def capture_mcp_outcomes(workspace: Workspace | Path | str) -> list[dict]:
    """Read any soma_report_outcome calls from this session from .soma/evidence/signals.jsonl."""
    ws = workspace if isinstance(workspace, Workspace) else (
        Workspace(root=Path(workspace).resolve()) if workspace else Workspace.resolve()
    )
    signals_file = str(ws.signals_file)
    outcomes = []
    if not os.path.isfile(signals_file):
        return outcomes
    try:
        with open(signals_file, 'r', encoding='utf-8') as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    record = json.loads(line_str)
                except Exception:
                    continue

                sig_type = record.get('signal_type') or record.get('signal') or record.get('outcome')
                if not sig_type:
                    continue

                outcome = record.get('outcome')
                if not outcome:
                    if sig_type in ('tp', 'success'):
                        outcome = 'success'
                    elif sig_type in ('fp', 'failure'):
                        outcome = 'failure'
                    elif sig_type in ('trigger', 'partial'):
                        outcome = 'partial'
                    else:
                        outcome = str(sig_type)
                record['outcome'] = outcome

                cell_id = record.get('cell_id') or record.get('cell_name') or record.get('cell')
                if cell_id and 'cell_id' not in record:
                    record['cell_id'] = cell_id
                if cell_id and 'cells_used' not in record:
                    record['cells_used'] = [cell_id]

                outcomes.append(record)
    except Exception as exc:
        print(f"    ! failed to read signals file: {exc}", file=sys.stderr)
    return outcomes


def _insight_cursor_path(workspace: Workspace | Path | str) -> str:
    ws = as_workspace(workspace)
    return str(ws.soma_dir / 'insight_cursor')


def _read_insight_cursor(workspace: Workspace | Path | str) -> int:
    """Return the committed byte offset into human_insights.jsonl (0 if none/invalid)."""
    try:
        with open(_insight_cursor_path(workspace), 'r', encoding='utf-8') as cf:
            value = int(cf.read().strip())
    except (OSError, ValueError):
        return 0
    return value if value >= 0 else 0


def commit_insight_cursor(workspace: Workspace | Path | str, offset: Optional[int]) -> bool:
    """Atomically persist the insight cursor (temp file + os.replace)."""
    if offset is None:
        return True
    cursor_file = _insight_cursor_path(workspace)
    if os.path.isfile(cursor_file) and _read_insight_cursor(workspace) == offset:
        return True
    cursor_dir = os.path.dirname(cursor_file)
    tmp_path = None
    try:
        os.makedirs(cursor_dir, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=cursor_dir, prefix='.insight_cursor.', suffix='.tmp')
        with os.fdopen(fd, 'w', encoding='utf-8') as cf:
            cf.write(str(int(offset)))
            cf.flush()
            os.fsync(cf.fileno())
        os.replace(tmp_path, cursor_file)
        return True
    except (OSError, ValueError, TypeError) as e:
        print(f"    ! failed to commit insight cursor: {e}", file=sys.stderr)
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return False


def capture_human_insight_signals(workspace: Workspace | Path | str) -> list[dict]:
    """Backward-compatible wrapper: read NEW insights and commit the cursor."""
    signals, new_offset = read_human_insight_signals(workspace)
    commit_insight_cursor(workspace, new_offset)
    return signals


def read_human_insight_signals(workspace: Workspace | Path | str) -> tuple[list[dict], int]:
    """Read NEW human insight annotations and produce fitness signals."""
    ws = as_workspace(workspace)
    insights_file = str(ws.soma_dir / 'human_insights.jsonl')
    cursor_offset = _read_insight_cursor(ws)
    if not os.path.isfile(insights_file):
        return [], cursor_offset

    file_size = os.path.getsize(insights_file)
    if cursor_offset > file_size:
        cursor_offset = 0

    weight = 0.5
    config_path = str(ws.soma_dir / 'config.yaml')
    if os.path.isfile(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                config = parse_frontmatter(content) if content.startswith("---") else parse_yaml_subset(content)
                config = config or {}
            weight = float(config.get('insight_signal_weight', 0.5))
        except Exception:
            pass

    cell_paths = {}
    cells_dir = ws.cells_dir
    if cells_dir.is_dir():
        for cell_file in glob.glob(os.path.join(str(cells_dir), '**', '*.md'), recursive=True):
            name = os.path.splitext(os.path.basename(cell_file))[0]
            cell_paths[name] = cell_file

    try:
        with open(insights_file, 'rb') as f:
            f.seek(cursor_offset)
            data = f.read()
    except OSError:
        return [], cursor_offset

    last_newline = data.rfind(b'\n')
    if last_newline == -1:
        return [], cursor_offset

    complete = data[:last_newline + 1]
    new_offset = cursor_offset + len(complete)

    signals = []
    line_offset = cursor_offset
    for raw_line in complete.split(b'\n'):
        this_offset = line_offset
        line_offset += len(raw_line) + 1
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line.decode('utf-8', errors='surrogatepass'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(record, dict):
            continue

        insight_id = f"{this_offset}:{hashlib.sha256(raw_line).hexdigest()}"

        if record.get('was_covered'):
            for cell_name in record.get('covering_cells', []):
                cell_path = cell_paths.get(cell_name)
                if cell_path:
                    signals.append({
                        'cell': cell_name,
                        '_path': cell_path,
                        'signal': weight,
                        'reasons': [f"human insight: {record.get('insight', '')[:80]}"],
                        'verified': True,
                        'signal_type': 'human_insight',
                        'insight_id': insight_id,
                        'weight': weight,
                        'files': record.get('context_files', []),
                    })
        else:
            signals.append({
                'cell': None,
                '_path': None,
                'signal': 0.0,
                'reasons': [f"blind spot: {record.get('insight', '')[:80]}"],
                'verified': True,
                'signal_type': 'blind_spot',
                'weight': weight,
                'files': record.get('context_files', []),
            })

    return signals, new_offset


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _get_changed_files(workspace: str) -> list[str]:
    try:
        out = subprocess.check_output(
            ['git', 'diff', '--name-only', 'HEAD~1'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        )
        files = [f.strip() for f in out.splitlines() if f.strip()]
        if files:
            return files
    except Exception:
        pass

    try:
        out = subprocess.check_output(
            ['git', 'status', '--porcelain'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        )
        files = []
        for line in out.splitlines():
            line = line.strip()
            if len(line) > 3:
                files.append(line[3:].strip())
        return files
    except Exception:
        return []


def _parse_frontmatter(content: str, filepath: Optional[str] = None) -> dict:
    """Parse YAML frontmatter robustly using parse_cell_file or parse_frontmatter."""
    if filepath is not None:
        try:
            from soma_core.frontmatter import parse_cell_frontmatter
            fm, _body = parse_cell_frontmatter(str(filepath))
            return fm if isinstance(fm, dict) else {}
        except Exception:
            return {}
    if not content:
        return {}
    res = parse_frontmatter(content)
    return res if isinstance(res, dict) else {}


def match_cells_to_changes(workspace: Workspace | Path | str, changed_files: list[str]) -> list[dict]:
    ws = as_workspace(workspace)
    cells_dir = ws.cells_dir
    matches = find_matching_cells(str(cells_dir), changed_files, allow_basename_match=True)
    triggered = []
    for m in matches:
        cell_dict = dict(m.frontmatter)
        cell_dict['_name'] = m.cell_id
        cell_dict['_path'] = m.cell_path
        triggered.append(cell_dict)
    return triggered


def to_fraction(credit: Any) -> str:
    """Convert credit float to a string Fraction (e.g., '1/3') for deterministic storage."""
    if isinstance(credit, str) and '/' in credit:
        return credit
    try:
        val = max(0.0, min(1.0, float(credit)))
    except (ValueError, TypeError):
        val = 0.0
    f = Fraction(val).limit_denominator(1000)
    return f"{f.numerator}/{f.denominator}"


def compute_credit_weights(triggered_cells: list[dict], changed_files: list[str]) -> dict[str, float]:
    """Compute per-cell credit weights using per-file scope narrowing."""
    if not changed_files or not triggered_cells:
        return {c.get('_name', c.get('id', '')): 1.0 for c in triggered_cells}

    file_to_cells: dict[str, list[str]] = {}
    for fpath in changed_files:
        matching = []
        for cell in triggered_cells:
            cell_name = cell.get('_name', cell.get('id', ''))
            target_paths = cell.get('target_paths', [])
            if isinstance(target_paths, str):
                target_paths = [target_paths]
            for tp in target_paths:
                if fnmatch.fnmatch(fpath, tp) or fnmatch.fnmatch(os.path.basename(fpath), tp):
                    matching.append(cell_name)
                    break
        if matching:
            file_to_cells[fpath] = matching

    credit = {c.get('_name', c.get('id', '')): 0.0 for c in triggered_cells}
    for fpath, cell_names in file_to_cells.items():
        per_cell = 1.0 / len(cell_names)
        for cn in cell_names:
            credit[cn] += per_cell

    return credit


def compute_fitness_signals(triggered_cells: list[dict], outcomes: dict, changed_files: Optional[list[str]] = None) -> list[dict]:
    """ACE-aligned reflector: score cells based on VERIFIABLE outcomes."""
    credit_weights = compute_credit_weights(triggered_cells, changed_files or [])
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

        # 5. MCP self-report — WEAKEST
        cell_name = cell.get('_name', cell.get('id', ''))
        for mcp_entry in mcp:
            cells_used = list(mcp_entry.get('cells_used', []))
            cell_id = mcp_entry.get('cell_id') or mcp_entry.get('cell_name') or mcp_entry.get('cell')
            if cell_id and cell_id not in cells_used:
                cells_used.append(cell_id)

            if cell_name in cells_used:
                outcome = mcp_entry.get('outcome', '')
                if outcome in ('success', 'tp'):
                    if test_outcome.get('verified') and test_outcome.get('passed') is False:
                        signal -= 2.0
                        reasons.append("agent claimed success but tests FAILED (overconfidence penalty)")
                    elif not test_outcome.get('verified') and not build_outcome.get('verified') and git.get('reverts', 0) == 0:
                        signal -= 1.0
                        reasons.append("agent claimed success with zero verifiable evidence (overconfidence penalty)")
                    else:
                        signal += 0.2
                        reasons.append("agent reported success")
                elif outcome in ('failure', 'fp'):
                    signal -= 0.2
                    reasons.append("agent reported failure")

        signal = max(-2.0, min(2.0, signal))

        results.append({
            'cell': cell_name,
            '_path': cell.get('_path'),
            'signal': round(signal, 2),
            'reasons': reasons,
            'verified': bool(test_outcome.get('verified', False) or build_outcome.get('verified', False)),
            'credit_weight': credit_weights.get(cell_name, 1.0),
            'signal_method': 'credit_weighted',
        })

    return results


def update_cell_fitness(workspace: str, fitness_signals: list[dict]) -> None:
    """Update cell frontmatter with fitness signals using YAML / dump_frontmatter."""
    for sig in fitness_signals:
        fpath = sig.get('_path')
        if not fpath or not os.path.isfile(fpath):
            continue
        signal = sig.get('signal', 0.0)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            end = content.find('---', 3)
            if end == -1:
                continue

            fm = parse_frontmatter(content) or {}
            body = _get_body(content)

            fitness = fm.get('fitness')
            if fitness is None or isinstance(fitness, bool):
                fitness = {'score': None, 'impact_weight': 1.0}
            elif isinstance(fitness, (int, float)):
                fitness = {'score': float(fitness), 'impact_weight': 1.0}
            elif isinstance(fitness, str):
                try:
                    fitness = {'score': float(fitness), 'impact_weight': 1.0}
                except ValueError:
                    fitness = {'score': None, 'impact_weight': 1.0}
            elif not isinstance(fitness, dict):
                fitness = {'score': None, 'impact_weight': 1.0}

            fitness['triggers'] = _as_int(fitness.get('triggers', 0)) + 1
            fitness.setdefault('true_positives', 0)
            fitness.setdefault('false_positives', 0)

            credit_weight = sig.get('credit_weight', 1.0)
            frac_str = to_fraction(credit_weight)

            if signal > 0:
                raw_tp = str(fitness['true_positives']).strip()
                try:
                    current = Fraction(raw_tp)
                except Exception:
                    current = Fraction(0)
                new_val = current + Fraction(frac_str)
                r = round(float(new_val), 4)
                fitness['true_positives'] = int(r) if r.is_integer() else r
            elif signal < 0:
                raw_fp = str(fitness['false_positives']).strip()
                try:
                    current = Fraction(raw_fp)
                except Exception:
                    current = Fraction(0)
                new_val = current + Fraction(frac_str)
                r = round(float(new_val), 4)
                fitness['false_positives'] = int(r) if r.is_integer() else r

            fitness['last_trigger_date'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            fm['fitness'] = fitness

            new_fm = dump_frontmatter(fm)

            new_content = f"---\n{new_fm.strip()}\n---\n\n{body}\n" if body else f"---\n{new_fm.strip()}\n---\n"

            tmp_fpath = f"{fpath}.tmp.{os.getpid()}"
            with open(tmp_fpath, 'w', encoding='utf-8') as f:
                f.write(new_content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_fpath, fpath)
        except Exception as e:
            print(f"    ! failed to update fitness for {fpath}: {e}", file=sys.stderr)


INSIGHT_PRINCIPAL = 'outcome_engine'
INSIGHT_SCOPE = 'human_insight'


def append_fitness_log(
    workspace: str,
    fitness_signals: list[dict],
    outcomes: dict,
    expected_generation: Optional[int] = None,
    idempotency_prefix: Optional[str] = None,
) -> bool:
    """Atomically append one outcome-engine batch to canonical evidence."""
    if not fitness_signals:
        return True

    from soma_core.telemetry import append_signals

    if idempotency_prefix is None:
        idempotency_prefix = secrets.token_hex(16)

    events = []
    for sig in fitness_signals:
        signal_val = sig.get('signal', 0)
        if signal_val > 0:
            signal_type = 'tp'
        elif signal_val < 0:
            signal_type = 'fp'
        else:
            signal_type = 'trigger'

        metadata = {
            'raw_signal': sig.get('signal'),
            'verified': sig.get('verified', False),
            'credit_weight': sig.get('credit_weight', 1.0),
            'signal_method': sig.get('signal_method', 'legacy'),
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
                    'rework_count': len(outcomes.get('git', {}).get('rework_files', [])),
                },
            },
        }

        insight_id = sig.get('insight_id')
        if insight_id:
            metadata['insight_id'] = insight_id
            principal = INSIGHT_PRINCIPAL
            scope = INSIGHT_SCOPE
            key = insight_id
        else:
            principal = 'outcome_engine'
            scope = 'run'
            key = idempotency_prefix

        events.append({
            'cell_name': sig['cell'],
            'signal_type': signal_type,
            'source': 'session',
            'metadata': metadata,
            'principal': principal,
            'idempotency_scope': scope,
            'idempotency_key': key,
        })

    try:
        append_signals(workspace, events, expected_generation=expected_generation)
    except Exception as exc:
        print(f"    ! failed to log fitness signal batch: {exc}", file=sys.stderr)
        return False
    return True


def record_verification_telemetry(
    workspace: str,
    target_files: list[str],
    passed: bool,
    verdict: Any = None,
    layer1_evidence: Any = None,
    source: str = "session",
    run_id: Optional[str] = None,
) -> bool:
    """Record ambient verification evidence (triggers and outcomes) for matched cells."""
    if not workspace or not target_files:
        return False

    ws = workspace if isinstance(workspace, Workspace) else (
        Workspace(root=Path(workspace).resolve()) if workspace else Workspace.resolve()
    )
    cells_dir = ws.cells_dir
    if not cells_dir.is_dir():
        return False

    matched = match_cells_to_changes(ws, target_files)
    if not matched:
        return False

    from soma_core.telemetry import append_signals

    if run_id is None:
        run_id = secrets.token_hex(16)

    credit_weights = compute_credit_weights(matched, target_files)
    events = []
    fitness_signals = []
    sig_type = "tp" if passed else "fp"
    signal_val = 1.0 if passed else -1.0

    for cell in matched:
        cell_id = cell.get("_name") or cell.get("id")
        if not cell_id:
            continue
        weight = float(credit_weights.get(cell_id, 1.0))
        weight = max(0.0, min(1.0, weight))

        # 1. Trigger event
        events.append({
            "cell_name": cell_id,
            "signal_type": "trigger",
            "source": source,
            "metadata": {
                "credit_weight": 1.0,
                "verdict": str(verdict) if verdict is not None else ("PASS" if passed else "FAIL"),
                "target_files": target_files[:20],
            },
            "principal": "verification",
            "idempotency_scope": "run",
            "idempotency_key": f"{run_id}:trig:{cell_id}",
        })

        # 2. Outcome event
        events.append({
            "cell_name": cell_id,
            "signal_type": sig_type,
            "source": source,
            "metadata": {
                "credit_weight": weight,
                "verdict": str(verdict) if verdict is not None else ("PASS" if passed else "FAIL"),
                "passed": passed,
                "evidence_checks": len(layer1_evidence) if layer1_evidence else 0,
            },
            "principal": "verification",
            "idempotency_scope": "run",
            "idempotency_key": f"{run_id}:out:{cell_id}",
        })

        fitness_signals.append({
            "cell": cell_id,
            "_path": cell.get("_path"),
            "signal": signal_val,
            "credit_weight": weight,
        })

    try:
        append_signals(workspace, events)
        if fitness_signals:
            update_cell_fitness(workspace, fitness_signals)
        return True
    except Exception as exc:
        print(f"    ! failed to record ambient verification telemetry: {exc}", file=sys.stderr)
        return False


def harvest_git_history(workspace: Workspace | Path | str, limit: int = 30, dry_run: bool = False) -> dict:
    """Inspect recent git commit diffs, match touched files to cells, and seed baseline fitness evidence."""
    ws = workspace if isinstance(workspace, Workspace) else (
        Workspace(root=Path(workspace).resolve()) if workspace else Workspace.resolve()
    )
    cells_dir = ws.cells_dir
    if not cells_dir.is_dir():
        return {"commits_inspected": 0, "cells_matched": 0, "signals_minted": 0}

    try:
        cmd = ["git", "log", f"-n{max(1, limit)}", "--name-only", "--format=commit:%H:%cI"]
        res = subprocess.run(cmd, cwd=str(ws.root), capture_output=True, text=True, timeout=15)
        if res.returncode != 0:
            return {"commits_inspected": 0, "cells_matched": 0, "signals_minted": 0, "error": res.stderr}
    except Exception as exc:
        return {"commits_inspected": 0, "cells_matched": 0, "signals_minted": 0, "error": str(exc)}

    commits = []
    current_commit = None
    current_date = None
    current_files = []

    for line in res.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("commit:"):
            if current_commit:
                commits.append((current_commit, current_date, current_files))
            parts = line.split(":", 2)
            current_commit = parts[1]
            current_date = parts[2] if len(parts) > 2 else datetime.now(timezone.utc).isoformat()
            current_files = []
        else:
            current_files.append(line)

    if current_commit:
        commits.append((current_commit, current_date, current_files))

    all_events = []
    fitness_updates_by_cell = {}
    matched_cell_ids = set()

    for commit_hash, commit_date, files in commits:
        if not files:
            continue
        matched = match_cells_to_changes(ws, files)
        if not matched:
            continue

        credit_weights = compute_credit_weights(matched, files)
        for cell in matched:
            cell_id = cell.get("_name") or cell.get("id")
            if not cell_id:
                continue
            matched_cell_ids.add(cell_id)
            weight = float(credit_weights.get(cell_id, 1.0))
            weight = max(0.0, min(1.0, weight))

            all_events.append({
                "cell_name": cell_id,
                "signal_type": "trigger",
                "source": "ci",
                "metadata": {
                    "credit_weight": 1.0,
                    "commit": commit_hash[:10],
                    "commit_date": commit_date,
                },
                "principal": "git_harvest",
                "idempotency_scope": "commit",
                "idempotency_key": f"{commit_hash[:12]}:trig:{cell_id}",
            })
            all_events.append({
                "cell_name": cell_id,
                "signal_type": "tp",
                "source": "ci",
                "metadata": {
                    "credit_weight": weight,
                    "commit": commit_hash[:10],
                    "commit_date": commit_date,
                },
                "principal": "git_harvest",
                "idempotency_scope": "commit",
                "idempotency_key": f"{commit_hash[:12]}:tp:{cell_id}",
            })

            if cell_id not in fitness_updates_by_cell:
                fitness_updates_by_cell[cell_id] = {
                    "cell": cell_id,
                    "_path": cell.get("_path"),
                    "signal": 1.0,
                    "credit_weight": weight,
                }

    if not dry_run and all_events:
        from soma_core.telemetry import append_signals
        append_signals(ws, all_events)
        if fitness_updates_by_cell:
            update_cell_fitness(ws, list(fitness_updates_by_cell.values()))

    return {
        "commits_inspected": len(commits),
        "cells_matched": len(matched_cell_ids),
        "signals_minted": len(all_events),
    }


def run_outcome_engine(workspace: Optional[Workspace | Path | str] = None, mod: Any = None) -> int:
    """Canonical ACE reflector loop."""
    m = mod if mod is not None else sys.modules.get('soma_core.telemetry') or sys.modules[__name__]
    resolve_ws = getattr(m, 'resolve_workspace', resolve_workspace)
    raw_ws = workspace if workspace is not None else resolve_ws()
    ws = as_workspace(raw_ws)
    cells_dir = ws.cells_dir
    if not cells_dir.is_dir():
        return 0

    print("  Running outcome engine (ACE reflector)...")
    from soma_core.telemetry import read_generation
    read_gen = getattr(m, 'read_generation', read_generation)
    generation = read_gen(ws)

    cap_test = getattr(m, 'capture_test_outcome', capture_test_outcome)
    cap_build = getattr(m, 'capture_build_outcome', capture_build_outcome)
    cap_git = getattr(m, 'capture_git_signals', capture_git_signals)
    cap_mcp = getattr(m, 'capture_mcp_outcomes', capture_mcp_outcomes)
    read_insights = getattr(m, 'read_human_insight_signals', read_human_insight_signals)
    commit_cursor = getattr(m, 'commit_insight_cursor', commit_insight_cursor)
    get_changed = getattr(m, '_get_changed_files', _get_changed_files)
    match_cells = getattr(m, 'match_cells_to_changes', match_cells_to_changes)
    comp_signals = getattr(m, 'compute_fitness_signals', compute_fitness_signals)
    append_log = getattr(m, 'append_fitness_log', append_fitness_log)
    update_fitness = getattr(m, 'update_cell_fitness', update_cell_fitness)

    outcomes = {}
    print("    Detecting test runner...", end=' ')
    outcomes['tests'] = cap_test(ws)
    test_result = outcomes['tests']
    if test_result.get('verified'):
        status = '✅ PASSED' if test_result['passed'] else '❌ FAILED'
        print(f"{test_result.get('framework', '?')} → {status}")
    else:
        print(f"skipped ({test_result.get('reason', 'unknown')})")

    outcomes['build'] = cap_build(ws)
    outcomes['git'] = cap_git(ws)
    mcp = cap_mcp(ws)
    if mcp:
        outcomes['mcp'] = mcp

    insight_signals, insight_offset = read_insights(ws)
    blind_spots = [s for s in insight_signals if s.get('signal_type') == 'blind_spot']
    cell_boosts = [s for s in insight_signals if s.get('_path') is not None]

    if blind_spots:
        print(f"    {len(blind_spots)} governance blind spot(s) detected from human insights")

    changed_files = get_changed(ws)
    triggered = match_cells(ws, changed_files)

    if not triggered and not cell_boosts:
        print("    No cells matched changed files.")
        commit_cursor(ws, insight_offset)
        return 0

    signals = comp_signals(triggered, outcomes, changed_files=changed_files) if triggered else []

    existing_paths = {s['_path'] for s in signals if '_path' in s}
    for boost in cell_boosts:
        if boost['_path'] not in existing_paths:
            signals.append(boost)
            existing_paths.add(boost['_path'])

    if signals:
        run_idempotency_prefix = secrets.token_hex(16)
        if append_log(
            ws, signals, outcomes,
            expected_generation=generation,
            idempotency_prefix=run_idempotency_prefix
        ):
            commit_cursor(ws, insight_offset)
            update_fitness(ws, signals)
        else:
            print("    ! evidence log incomplete; cells and insight cursor left unchanged (will retry)", file=sys.stderr)
    else:
        commit_cursor(ws, insight_offset)

    verified_count = sum(1 for s in signals if s.get('verified'))
    print(f"    {len(signals)} cells evaluated ({verified_count} with verified outcomes)")
    for s in signals:
        indicator = '↑' if s['signal'] > 0 else '↓' if s['signal'] < 0 else '→'
        v = '✓' if s.get('verified') else '?'
        reasons_str = ', '.join(s.get('reasons', [])) or 'no signal'
        print(f"      {indicator} [{v}] {s['cell']}: {s['signal']:+.1f} ({reasons_str})")
    return 0


def main(*args, **kwargs) -> int:
    """Outcome engine main entrypoint."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    ws = kwargs.get("workspace")
    if ws is not None:
        return run_outcome_engine(ws)
    return run_outcome_engine()


# ── Fitness Updater ────────────────────────────────────────────────────────

PLATFORMS = {
    "antigravity": {
        "write_tools": {"write_to_file", "replace_file_content", "multi_replace_file_content"},
        "target_file_keys": ["TargetFile"],
        "args_keys": ["arguments", "args"],
        "id_skip_dirs": {"logs", ".system_generated"},
    },
    "claude": {
        "write_tools": {"write_to_file", "edit_file", "create_file"},
        "target_file_keys": ["path", "file_path", "TargetFile"],
        "args_keys": ["arguments", "args", "input"],
        "id_skip_dirs": {"logs"},
    },
}

PLATFORMS["generic"] = {
    "write_tools": PLATFORMS["antigravity"]["write_tools"] | PLATFORMS["claude"]["write_tools"],
    "target_file_keys": list(set(PLATFORMS["antigravity"]["target_file_keys"] + PLATFORMS["claude"]["target_file_keys"])),
    "args_keys": list(set(PLATFORMS["antigravity"]["args_keys"] + PLATFORMS["claude"]["args_keys"])),
    "id_skip_dirs": PLATFORMS["antigravity"]["id_skip_dirs"] | PLATFORMS["claude"]["id_skip_dirs"],
}

DEFAULT_PLATFORM = "antigravity"


def _get_platform_config(platform: Optional[str] = None) -> dict:
    name = platform or DEFAULT_PLATFORM
    if name not in PLATFORMS:
        print(f"Warning: unknown platform '{name}', using generic config", file=sys.stderr)
        return PLATFORMS["generic"]
    return PLATFORMS[name]


def detect_platform(transcript_path: Path | str) -> str:
    transcript_path = Path(transcript_path)
    if not transcript_path.exists():
        return DEFAULT_PLATFORM

    tool_to_platform = {}
    for name, config in PLATFORMS.items():
        if name == "generic":
            continue
        for tool in config["write_tools"]:
            if tool not in tool_to_platform:
                tool_to_platform[tool] = name

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    step = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                for tc in step.get("tool_calls", []):
                    tool_name = tc.get("name", "")
                    if tool_name in tool_to_platform:
                        return tool_to_platform[tool_name]
    except Exception:
        pass

    return DEFAULT_PLATFORM


def resolve_transcript_id(transcript_path: Path | str, platform: Optional[str] = None) -> str:
    config = _get_platform_config(platform)
    candidate = Path(transcript_path).resolve().parent
    while candidate.name in config["id_skip_dirs"]:
        candidate = candidate.parent
    return candidate.name


def extract_modified_files(transcript_path: Path | str, platform: Optional[str] = None) -> set[str]:
    transcript_path = Path(transcript_path)
    if not transcript_path.exists():
        return set()

    config = _get_platform_config(platform)
    write_tools = config["write_tools"]
    args_keys = config["args_keys"]
    target_file_keys = config["target_file_keys"]

    modified = set()
    try:
        text = transcript_path.read_text(encoding="utf-8")
    except Exception:
        return set()

    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            step = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue

        for tc in step.get("tool_calls", []):
            tool_name = tc.get("name", "")
            if tool_name not in write_tools:
                continue
            args = {}
            for key in args_keys:
                args = tc.get(key) or args
                if args:
                    break
            if not isinstance(args, dict):
                continue
            for tf_key in target_file_keys:
                target = args.get(tf_key, "")
                if isinstance(target, str):
                    target = target.strip('"').strip("'")
                if target:
                    modified.add(target)

    return modified


def match_cells(modified_files: set[str], cells_dir: Path | str, repo_root: str = "") -> list[dict]:
    cells_path = Path(cells_dir)
    matches = find_matching_cells(cells_path, modified_files, repo_root=repo_root, allow_basename_match=False)
    results = []
    for m in matches:
        try:
            rel_cell = str(Path(m.cell_path).relative_to(cells_path.resolve())).replace("\\", "/")
        except ValueError:
            rel_cell = Path(m.cell_path).name
        results.append({
            "cell_id": m.cell_id,
            "cell_path": rel_cell,
            "matched_files": sorted(list(m.matched_files)),
        })
    return results


def update_fitness(triggered_cells: list[dict], transcript_id: str, evidence_dir: Path | str) -> list[dict]:
    """Atomically record every cell triggered by one transcript."""
    if not triggered_cells:
        return []

    from soma_core.telemetry import append_signals, read_generation

    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    workspace = str(evidence_dir.parent.parent)

    generation = read_generation(workspace)
    events = [
        {
            'cell_name': cell['cell_id'],
            'signal_type': 'trigger',
            'source': 'session',
            'metadata': {
                'transcript_id': transcript_id,
                'matched_files': cell.get('matched_files', []),
            },
            'principal': 'fitness_updater',
            'idempotency_scope': 'transcript',
            'idempotency_key': f"{transcript_id}:{cell['cell_id']}",
        }
        for cell in triggered_cells
    ]
    return append_signals(workspace, events, expected_generation=generation)


__all__ = [
    "VERIFY_TIMEOUT",
    "_run_verify",
    "detect_test_runner",
    "capture_test_outcome",
    "capture_build_outcome",
    "capture_git_signals",
    "capture_mcp_outcomes",
    "_insight_cursor_path",
    "_read_insight_cursor",
    "commit_insight_cursor",
    "capture_human_insight_signals",
    "read_human_insight_signals",
    "_as_int",
    "_get_changed_files",
    "_parse_frontmatter",
    "match_cells_to_changes",
    "to_fraction",
    "compute_credit_weights",
    "compute_fitness_signals",
    "update_cell_fitness",
    "INSIGHT_PRINCIPAL",
    "INSIGHT_SCOPE",
    "append_fitness_log",
    "run_outcome_engine",
    "main",
    "PLATFORMS",
    "DEFAULT_PLATFORM",
    "detect_platform",
    "resolve_transcript_id",
    "extract_modified_files",
    "match_cells",
    "update_fitness",
    "record_verification_telemetry",
    "harvest_git_history",
]
