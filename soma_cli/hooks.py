"""Cross-platform lifecycle hook runner for Soma Governance.

Provides pure Python execution for:
- safety-gate: PreToolUse safety check intercepting destructive shell commands.
- pre-invocation: PreInvocation monitor checking project markers and critical alerts.
- session-close: Post-session evolution and fitness updates.
- pre-commit: Git pre-commit hook running deterministic checkpoint, cell scan, and enforcement.

Enables native Windows lifecycle hook execution (BUG-014, BUG-032) without bash dependencies.
Can be invoked as:
    soma hook <phase>
    python -m soma_cli hook <phase>
    python -m soma_cli.hooks <phase>
"""
from __future__ import annotations

import datetime
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Tuple

# ── Safety Gate: Fast-Path & Destructive Patterns ─────────────────────────────

SAFE_COMMAND_PREFIXES: tuple[str, ...] = (
    "git status",
    "git diff",
    "git log",
    "git show",
    "git branch",
    "git rev-parse",
    "git check-ref-format",
    "ls",
    "dir",
    "cat",
    "head",
    "tail",
    "wc",
    "pwd",
    "date",
    "whoami",
    "pytest",
    "python -m pytest",
    "cargo test",
    "npm test",
    "echo",
)

METACHARACTERS: frozenset[str] = frozenset({";", "&", "|", ">", "<", "`", "$", "\n", "\r", "(", ")", "\\"})
DANGEROUS_FLAGS: tuple[str, ...] = ("-f", "--force", "-D", "-d", "-M", "--output", "--ext-cmd", "--delete")

SECRET_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"""
            AKIA[0-9A-Z]{16}  # AWS standard access key
            """,
            re.VERBOSE,
        ),
        "AKIA_REDACTED",
    ),
    (
        re.compile(
            r"""
            ASIA[0-9A-Z]{16}  # AWS temporary/session access key
            """,
            re.VERBOSE,
        ),
        "ASIA_REDACTED",
    ),
    (
        re.compile(
            r"""
            ghp_[a-zA-Z0-9]{36}  # GitHub Personal Access Token (classic)
            """,
            re.VERBOSE,
        ),
        "ghp_REDACTED",
    ),
    (
        re.compile(
            r"""
            gh[ousr]_[a-zA-Z0-9]{36}  # GitHub OAuth/user/server/refresh tokens
            """,
            re.VERBOSE,
        ),
        "gh_token_REDACTED",
    ),
    (
        re.compile(
            r"""
            github_pat_[a-zA-Z0-9_]{20,}  # GitHub Fine-grained PAT
            """,
            re.VERBOSE,
        ),
        "github_pat_REDACTED",
    ),
    (
        re.compile(
            r"""
            sk-(?:proj-|ant-)?[a-zA-Z0-9_-]{20,}  # OpenAI / Anthropic API keys
            """,
            re.VERBOSE,
        ),
        "sk-REDACTED",
    ),
    (
        re.compile(
            r"""
            AIzaSy[a-zA-Z0-9_-]{33}  # Google API key
            """,
            re.VERBOSE,
        ),
        "AIzaSy_REDACTED",
    ),
    (
        re.compile(
            r"""
            Bearer\s+[a-zA-Z0-9._-]{20,}  # HTTP Bearer authentication token
            """,
            re.VERBOSE,
        ),
        "Bearer REDACTED",
    ),
    (
        re.compile(
            r"""
            GEMINI_API_KEY=[^\s]*  # Gemini API Key assignment
            """,
            re.VERBOSE,
        ),
        "GEMINI_API_KEY=REDACTED",
    ),
]


def redact_secrets(cmd: str) -> str:
    """Mask known secret patterns before logging."""
    for pattern, replacement in SECRET_REPLACEMENTS:
        cmd = pattern.sub(replacement, cmd)
    return cmd


def _find_gate_log_dir(workspace: Path) -> Path:
    """Locate the canonical directory for gate event logging."""
    env_logs = os.environ.get("SOMA_LOGS_DIR")
    if env_logs:
        return Path(env_logs) / "governance"
    home = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or Path.home())
    candidate = home / ".gemini" / "antigravity" / "scratch" / "ai-conversation-logs" / "governance"
    if candidate.parent.exists():
        return candidate
    return workspace / ".soma" / "governance"


def log_gate_event(cmd: str, decision: str, reason: str, workspace: Path) -> None:
    """Log safety gate evaluations to gate_events.jsonl."""
    log_dir = _find_gate_log_dir(workspace)
    log_file = log_dir / "gate_events.jsonl"
    snippet = redact_secrets(cmd)[:200]
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record = {
        "timestamp": now_iso,
        "command": snippet,
        "decision": decision,
    }
    if reason:
        record["reason"] = reason

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError:
        pass


def run_safety_gate(
    cmd: str | None = None,
    payload: dict[str, Any] | None = None,
    workspace: Path | None = None,
) -> tuple[int, dict[str, Any]]:
    """Evaluate a tool-use command against destructive patterns.

    Fail-closed: if unable to parse the command or command is empty, returns force_ask.
    """
    root = workspace or Path.cwd()
    if cmd is None and payload is not None:
        tc = payload.get("toolCall", {})
        args = tc.get("args", {})
        cmd = args.get("CommandLine", "")
    if not cmd or not isinstance(cmd, str) or not cmd.strip():
        reason = "Unable to parse command — requesting confirmation"
        log_gate_event(cmd or "", "BLOCKED", reason, root)
        return 0, {
            "decision": "force_ask",
            "reason": f"🛡️ Safety Gate: {reason}",
        }

    trimmed = cmd.strip()

    # Pre-tokenization normalization & evasion detection
    candidates = [cmd]
    unescaped = re.sub(r"\\([a-zA-Z0-9_\-\.\/])", r"\1", cmd)
    if unescaped != cmd:
        candidates.append(unescaped)
    for src in [cmd, unescaped]:
        try:
            toks = shlex.split(src)
            if toks:
                candidates.append(" ".join(toks))
        except Exception:
            pass
    dequoted = re.sub(r"['\"]([a-zA-Z0-9_\-]+)['\"]", r"\1", unescaped)
    if dequoted not in candidates:
        candidates.append(dequoted)

    # Fast-path: benign read-only inspection commands without chaining or force flags (<0.01ms)
    if any(trimmed.startswith(prefix) for prefix in SAFE_COMMAND_PREFIXES):
        if not any(c in trimmed for c in METACHARACTERS):
            tokens = trimmed.split()
            is_dangerous = any(
                t in DANGEROUS_FLAGS
                or t.startswith(("-D", "-d", "-M", "--output", "--ext-cmd", "--force", "--delete"))
                or (t.startswith("-") and not t.startswith("--") and any(c in t for c in "fDdM"))
                for t in tokens
            )
            if not is_dangerous:
                from soma_core.command_safety import CommandAnalyzer
                eval_res = CommandAnalyzer.evaluate(cmd)
                if not eval_res.is_destructive:
                    log_gate_event(cmd, "ALLOWED", "", root)
                    return 0, {"decision": "allow"}

    # Structured AST / Token Analyzer (soma_core.command_safety)
    from soma_core.command_safety import CommandAnalyzer
    for cand in candidates:
        eval_res = CommandAnalyzer.evaluate(cand)
        if eval_res.is_destructive:
            log_gate_event(cmd, "BLOCKED", eval_res.reason, root)
            return 0, {
                "decision": "force_ask",
                "reason": f"🛡️ Safety Gate: {eval_res.reason}",
            }

    log_gate_event(cmd, "ALLOWED", "", root)
    return 0, {"decision": "allow"}


# ── Pre-Invocation / Governance Monitor ────────────────────────────────────────

def run_pre_invocation(
    payload: dict[str, Any] | None = None,
    workspace: Path | None = None,
) -> tuple[int, dict[str, Any]]:
    """Run pre-invocation checks on session start and periodically.

    - Detects coding projects and suggests session-preflight.
    - Checks for pending critical proposals and rotates them.
    """
    data = payload or {}
    invocation_num = int(data.get("invocationNum", 1))

    # Run on first invocation and every 100th invocation
    if invocation_num != 1 and (invocation_num % 100) != 0:
        return 0, {}

    ws_list = data.get("workspacePaths", [])
    target_str = ws_list[0] if ws_list else (str(workspace) if workspace else os.getcwd())
    target = Path(target_str)

    response: dict[str, Any] = {}
    steps: list[dict[str, Any]] = []

    # Project detection (invocation 1 only)
    is_gov = any(k in target_str.lower() for k in ["soma", "ai-conversation-logs"])
    if invocation_num == 1 and target.is_dir() and not is_gov:
        markers: list[str] = []
        if any((target / f).exists() for f in ["venv", ".venv", "requirements.txt", "pyproject.toml"]):
            markers.append("python")
        if (target / "package.json").exists():
            markers.append("node")
        if (target / "Makefile").exists():
            markers.append("Makefile")
        if (target / "tests").is_dir():
            markers.append("tests/")

        if "python" in markers or "node" in markers:
            marker_str = ", ".join(markers)
            steps.append({
                "ephemeralMessage": (
                    f"⚡ PREFLIGHT: Coding project detected at {target_str} ({marker_str}). "
                    "Per session-preflight skill, verify venv health, git status, and test suite "
                    "before modifying files."
                )
            })

    # Critical proposals check
    log_dir = _find_gate_log_dir(target)
    pending_crit = log_dir / "pending_critical.md"
    last_crit = log_dir / "last_critical.md"

    if pending_crit.is_file():
        try:
            content = pending_crit.read_text(encoding="utf-8")
            pending_crit.replace(last_crit)
            steps.append({
                "criticalMessage": f"🔴 CRITICAL GOVERNANCE ALERT:\n{content}"
            })
        except OSError:
            pass

    if steps:
        response["injectSteps"] = steps
        response["steps"] = steps

    return 0, response


# ── Session Close / Post-Session ──────────────────────────────────────────────

def run_session_close(workspace: Path | None = None) -> tuple[int, dict[str, Any]]:
    """Run session close lifecycle tasks (outcome evaluation, cell evolution, and consolidation)."""
    import random

    root = workspace or Path.cwd()

    # 1. Outcome engine (in-process ACE reflector)
    try:
        from soma_core.telemetry import run_outcome_engine
        run_outcome_engine(workspace=str(root))
    except Exception:
        pass

    # 2. Cell fitness calculation
    try:
        from soma_core.lifecycle import compute_cells_fitness
        compute_cells_fitness(workspace=str(root))
    except Exception:
        pass

    # 3. Cell selection pressure (archive extinct cells)
    try:
        from soma_core.lifecycle import run_cell_selection
        run_cell_selection(workspace=root, execute=True)
    except Exception:
        pass

    # 4. Probabilistic crossover
    try:
        from soma_core.evidence import aggregate_signals
        from soma_core.lifecycle import crossover_cells
        evidence_dir = root / ".soma" / "evidence"
        if evidence_dir.is_dir():
            signal_counts = aggregate_signals(evidence_dir).counts
            cell_triggers = {
                cell_id: counts["triggers"]
                for cell_id, counts in signal_counts.items()
                if counts["has_triggers"]
            }
            high_fitness = [cid for cid, count in cell_triggers.items() if count >= 5]
            if len(high_fitness) >= 2:
                pair = random.sample(high_fitness, 2)
                crossover_cells(root, pair[0], pair[1])
    except Exception:
        pass

    return 0, {}



# ── Pre-Commit Hook ───────────────────────────────────────────────────────────

def run_pre_commit(
    workspace: Path | None = None,
    strict: bool = False,
    use_json: bool = False,
) -> int:
    """Run pre-commit checks: checkpoint quality, cell triggers, and enforcement."""
    import fnmatch
    import subprocess

    root = workspace or Path.cwd()
    repo_root = root

    # 1. Deterministic quality checkpoint
    try:
        from soma_core.verification.checkpoint_checks import run_all_checks
        issues = run_all_checks(root)
    except ImportError:
        issues = []

    has_checkpoint_issues = len(issues) > 0

    # 2. Check staged files against cell target paths
    staged_files: list[str] = []
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "--cached"],
            cwd=repo_root,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        staged_files = [line.strip() for line in out.splitlines() if line.strip()]
    except Exception:
        pass

    cells_dir = repo_root / ".soma" / "cells"
    all_target_patterns: list[str] = []
    triggered_cells: list[str] = []

    if cells_dir.is_dir() and staged_files:
        from soma_sdk.cells import parse_cell_file
        for cell_file in cells_dir.glob("**/*.md"):
            if cell_file.name == "README.md":
                continue
            try:
                fm, _ = parse_cell_file(cell_file)
                targets = fm.get("target_paths", [])
                all_target_patterns.extend(targets)
                hypothesis = fm.get("hypothesis", "")

                matched = False
                for sf in staged_files:
                    for tp in targets:
                        if fnmatch.fnmatch(sf, tp) or fnmatch.fnmatch(sf, f"*{tp}*"):
                            matched = True
                            break
                    if os.path.basename(sf) in hypothesis:
                        matched = True
                    if matched:
                        break
                if matched:
                    triggered_cells.append(cell_file.stem)
            except Exception:
                continue

    info_file = sys.stderr if use_json else sys.stdout

    if triggered_cells:
        print(f"🧬 Soma: {len(triggered_cells)} governance cell(s) triggered by this commit ({', '.join(triggered_cells)})", file=info_file)

    # 3. Mechanical enforcement scripts
    mechanical_failed = False
    enforcement_dir = repo_root / ".soma" / "enforcement"
    if enforcement_dir.is_dir():
        for check in sorted(enforcement_dir.glob("check-*")):
            if check.is_file():
                try:
                    if check.suffix == ".py":
                        cmd = [sys.executable, str(check)]
                    elif check.suffix in [".sh", ""] and os.name != "nt":
                        cmd = ["bash", str(check)]
                    elif check.suffix in [".bat", ".cmd"]:
                        cmd = [str(check)]
                    else:
                        continue
                    res = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
                    if res.returncode != 0:
                        mechanical_failed = True
                        print(f"❌ Mechanical enforcement check failed: {check.name}", file=sys.stderr)
                        if res.stderr:
                            print(res.stderr.strip(), file=sys.stderr)
                except Exception as exc:
                    mechanical_failed = True
                    print(f"❌ Failed to run mechanical check {check.name}: {exc}", file=sys.stderr)

    # 4. Uncovered new files check
    new_files: list[str] = []
    try:
        out_new = subprocess.check_output(
            ["git", "diff", "--cached", "--diff-filter=A", "--name-only"],
            cwd=repo_root,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        new_files = [line.strip() for line in out_new.splitlines() if line.strip()]
    except Exception:
        pass

    uncovered_files = [
        nf for nf in new_files
        if all_target_patterns and not any(fnmatch.fnmatch(nf, p) for p in all_target_patterns)
    ]
    if uncovered_files:
        print("🔴 New files without governance coverage:", file=info_file)
        for uf in uncovered_files:
            print(f"  ⚠️  {uf}", file=info_file)

    if mechanical_failed:
        print("❌ Commit blocked by mechanical enforcement gates.", file=sys.stderr)
        if use_json:
            print(json.dumps({
                "status": "blocked",
                "reason": "mechanical_enforcement_failed",
                "triggered_cells": triggered_cells,
                "uncovered_files": uncovered_files,
                "checkpoint_issues": issues,
            }))
        return 1

    if has_checkpoint_issues:
        if strict:
            print("❌ Commit blocked: quality checkpoint failed in strict mode.", file=sys.stderr)
            if use_json:
                print(json.dumps({
                    "status": "blocked",
                    "reason": "checkpoint_failed",
                    "triggered_cells": triggered_cells,
                    "uncovered_files": uncovered_files,
                    "checkpoint_issues": issues,
                }))
            return 1
        else:
            print(f"⚠️  Quality checkpoint found {len(issues)} issue(s) (warn mode; commit allowed).", file=info_file)

    if use_json:
        print(json.dumps({
            "status": "ok",
            "triggered_cells": triggered_cells,
            "uncovered_files": uncovered_files,
            "checkpoint_issues": issues,
        }))

    return 0


# ── Git Pre-Commit Hook Management (Format 3) ──────────────────────────────────

_SOMA_HOOK_START = "# >>> soma pre-commit >>>"
_SOMA_HOOK_END = "# <<< soma pre-commit <<<"
SOMA_HOOK_FORMAT = "# soma-hook-format: 3"
CURRENT_HOOK_FORMAT_VERSION = 3


def generate_hook_block(python: str | None = None) -> str:
    """The marked pre-commit block (portable POSIX sh with dynamic multi-repo resolution)."""
    py = python if python is not None else sys.executable
    if os.name == "nt":
        py = py.replace("\\", "/")
    q = shlex.quote(py)
    return (
        f"{_SOMA_HOOK_START}\n"
        "# Installed by soma hook install (v0.116.0)\n"
        f"{SOMA_HOOK_FORMAT}\n"
        "if command -v soma >/dev/null 2>&1; then\n"
        "  soma checkpoint --pre-commit || exit $?\n"
        'elif [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/python" ] && "$VIRTUAL_ENV/bin/python" -c \'import soma_cli\' >/dev/null 2>&1; then\n'
        '  "$VIRTUAL_ENV/bin/python" -m soma_cli checkpoint --pre-commit || exit $?\n'
        'elif [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/Scripts/python.exe" ] && "$VIRTUAL_ENV/Scripts/python.exe" -c \'import soma_cli\' >/dev/null 2>&1; then\n'
        '  "$VIRTUAL_ENV/Scripts/python.exe" -m soma_cli checkpoint --pre-commit || exit $?\n'
        'elif [ -x "$PWD/.venv/bin/python" ] && "$PWD/.venv/bin/python" -c \'import soma_cli\' >/dev/null 2>&1; then\n'
        '  "$PWD/.venv/bin/python" -m soma_cli checkpoint --pre-commit || exit $?\n'
        'elif [ -x "$PWD/.venv/Scripts/python.exe" ] && "$PWD/.venv/Scripts/python.exe" -c \'import soma_cli\' >/dev/null 2>&1; then\n'
        '  "$PWD/.venv/Scripts/python.exe" -m soma_cli checkpoint --pre-commit || exit $?\n'
        f"elif {q} -c 'import soma_cli' >/dev/null 2>&1; then\n"
        f"  {q} -m soma_cli checkpoint --pre-commit || exit $?\n"
        "elif command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(0)' 2>/dev/null && python3 -c 'import soma_cli' >/dev/null 2>&1; then\n"
        "  python3 -m soma_cli checkpoint --pre-commit || exit $?\n"
        "else\n"
        '  echo "soma pre-commit: cannot execute quality checks." >&2\n'
        '  echo "  Neither \'soma\' nor a Python interpreter with \'soma_cli\' installed was found on PATH." >&2\n'
        '  echo "  Run \'soma hook status\' or \'soma doctor\' to diagnose environment resolution." >&2\n'
        "  exit 1\n"
        "fi\n"
        f"{_SOMA_HOOK_END}\n"
    )


def _replace_hook_block(content: str, block: str) -> str | None:
    """content with its marked block swapped for block, or None if malformed."""
    start = content.find(_SOMA_HOOK_START)
    end = content.find(_SOMA_HOOK_END, start)
    if start < 0 or end < 0:
        return None
    line_start = content.rfind("\n", 0, start) + 1
    end += len(_SOMA_HOOK_END)
    if content.startswith("\r\n", end):
        end += 2
    elif content.startswith("\n", end):
        end += 1
    return content[:line_start] + block + content[end:]


def install_hook(
    project_root: str | Path | Any | None = None,
    force: bool = False,
    python: str | None = None,
    dry_run: bool = False,
) -> bool:
    """Install or refresh Soma pre-commit hook into a git repository."""
    from soma_core.workspace import Workspace, resolve_git_hooks_dir

    if isinstance(project_root, Workspace):
        ws = project_root
        root = ws.root
        git_hooks_dir = ws.git_hooks_dir or resolve_git_hooks_dir(root)
    else:
        root = Path(project_root or Path.cwd()).resolve()
        git_hooks_dir = resolve_git_hooks_dir(root)

    if not git_hooks_dir:
        return False

    if dry_run:
        return True

    git_hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_file = git_hooks_dir / "pre-commit"

    target_file = hook_file
    if hook_file.is_symlink():
        real_target = hook_file.resolve()
        if not real_target.exists():
            if not force:
                print(
                    f"Error: {hook_file} is a dangling symlink. Use --force to replace.",
                    file=sys.stderr,
                )
                return False
            hook_file.unlink()
            target_file = hook_file
        else:
            is_contained = False
            for boundary in (root, git_hooks_dir):
                if boundary:
                    try:
                        real_target.relative_to(boundary.resolve())
                        is_contained = True
                        break
                    except ValueError:
                        pass
            if not is_contained and not force:
                print(
                    f"Error: {hook_file} is a symlink pointing outside repository ({real_target}). Use --force to overwrite.",
                    file=sys.stderr,
                )
                return False
            target_file = real_target

    block = generate_hook_block(python)

    if target_file.exists():
        content = target_file.read_text(encoding="utf-8")
        if _SOMA_HOOK_START in content:
            updated = _replace_hook_block(content, block)
            if updated is None:
                print(f"  ⚠️  {target_file} has an unterminated soma block; left unchanged", file=sys.stderr)
                return True
            new_content = updated
        else:
            if not content.endswith("\n"):
                content += "\n"
            new_content = content + "\n" + block
    else:
        new_content = "#!/bin/sh\n\n" + block

    new_content = new_content.replace("\r\n", "\n")

    tmp_file = target_file.parent / f".pre-commit.tmp.{os.getpid()}"
    try:
        tmp_file.write_bytes(new_content.encode("utf-8"))
        if os.name != "nt":
            tmp_file.chmod(0o755)
        tmp_file.replace(target_file)
    finally:
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except OSError:
                pass

    if os.name != "nt" and target_file.exists():
        try:
            target_file.chmod(target_file.stat().st_mode | 0o755)
        except OSError:
            pass

    return True


def uninstall_hook(
    project_root: str | Path | Any | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> bool:
    """Safely remove Soma pre-commit hook while preserving user hooks."""
    from soma_core.workspace import Workspace, resolve_git_hooks_dir

    if isinstance(project_root, Workspace):
        ws = project_root
        root = ws.root
        git_hooks_dir = ws.git_hooks_dir or resolve_git_hooks_dir(root)
    else:
        root = Path(project_root or Path.cwd()).resolve()
        git_hooks_dir = resolve_git_hooks_dir(root)

    if not git_hooks_dir:
        return False

    hook_file = git_hooks_dir / "pre-commit"
    if not hook_file.exists() and not hook_file.is_symlink():
        return False

    target_file = hook_file
    if hook_file.is_symlink():
        real_target = hook_file.resolve()
        if not real_target.exists():
            if force:
                if not dry_run:
                    hook_file.unlink()
                return True
            return False
        else:
            is_contained = False
            for boundary in (root, git_hooks_dir):
                if boundary:
                    try:
                        real_target.relative_to(boundary.resolve())
                        is_contained = True
                        break
                    except ValueError:
                        pass
            if not is_contained and not force:
                print(
                    f"Error: {hook_file} is a symlink pointing outside repository ({real_target}). Use --force to uninstall.",
                    file=sys.stderr,
                )
                return False
            target_file = real_target

    content = target_file.read_text(encoding="utf-8")
    if _SOMA_HOOK_START not in content:
        return False

    if dry_run:
        return True

    start = content.find(_SOMA_HOOK_START)
    end = content.find(_SOMA_HOOK_END, start)
    if end >= 0:
        line_start = content.rfind("\n", 0, start) + 1
        end += len(_SOMA_HOOK_END)
        if content.startswith("\r\n", end):
            end += 2
        elif content.startswith("\n", end):
            end += 1
        remaining = content[:line_start] + content[end:]
    else:
        print(f"  ⚠️  {target_file} has an unterminated soma block; left unchanged", file=sys.stderr)
        return False

    stripped_lines = [line.strip() for line in remaining.splitlines() if line.strip()]
    is_empty_or_shebang_only = (
        not stripped_lines
        or (len(stripped_lines) == 1 and stripped_lines[0].startswith("#!"))
    )

    if is_empty_or_shebang_only:
        if hook_file.is_symlink():
            try:
                target_file.unlink()
            except OSError:
                pass
            try:
                hook_file.unlink()
            except OSError:
                pass
        else:
            hook_file.unlink()
        return True

    remaining = remaining.replace("\r\n", "\n")
    tmp_file = target_file.parent / f".pre-commit.tmp.{os.getpid()}"
    try:
        tmp_file.write_bytes(remaining.encode("utf-8"))
        if os.name != "nt":
            tmp_file.chmod(target_file.stat().st_mode)
        tmp_file.replace(target_file)
    finally:
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except OSError:
                pass
    return True


def hook_status(project_root: str | Path | Any | None = None) -> dict[str, Any]:
    """Inspect and report the status of Soma git hooks in the target repository."""
    from soma_core.workspace import Workspace, resolve_git_hooks_dir

    if isinstance(project_root, Workspace):
        ws = project_root
        root = ws.root
        git_hooks_dir = ws.git_hooks_dir or resolve_git_hooks_dir(root)
    else:
        root = Path(project_root or Path.cwd()).resolve()
        git_hooks_dir = resolve_git_hooks_dir(root)

    is_git_repo = git_hooks_dir is not None
    hook_file = (git_hooks_dir / "pre-commit") if is_git_repo else None

    hook_exists = hook_file.is_file() if hook_file else False
    managed_by_soma = False
    format_version = None
    status = "no_git_repository"

    if is_git_repo:
        if not hook_exists:
            status = "not_installed"
        else:
            try:
                text = hook_file.read_text(encoding="utf-8", errors="replace")
                if _SOMA_HOOK_START in text:
                    managed_by_soma = True
                    match = re.search(r"soma-hook-format:\s*(\d+)", text)
                    if match:
                        format_version = int(match.group(1))
                    else:
                        format_version = 1
                    if format_version == CURRENT_HOOK_FORMAT_VERSION:
                        status = "installed"
                    else:
                        status = "outdated"
                else:
                    status = "unmanaged"
            except OSError:
                status = "unreadable"

    soma_path = shutil.which("soma")
    venv_env = os.environ.get("VIRTUAL_ENV")
    local_venv = None
    if root:
        for candidate in (root / ".venv" / "bin" / "python", root / ".venv" / "Scripts" / "python.exe"):
            if candidate.is_file():
                local_venv = str(candidate)
                break

    py3_path = shutil.which("python3")
    py3_valid = False
    if py3_path:
        try:
            res = subprocess.run([py3_path, "-c", "import sys; sys.exit(0)"], capture_output=True, timeout=2)
            py3_valid = (res.returncode == 0)
        except Exception:
            py3_valid = False

    is_worktree = False
    if root and (root / ".git").is_file():
        is_worktree = True

    return {
        "status": status,
        "is_git_repo": is_git_repo,
        "is_worktree": is_worktree,
        "repository_root": str(root),
        "git_hooks_dir": str(git_hooks_dir) if git_hooks_dir else None,
        "hook_file": str(hook_file) if hook_file else None,
        "managed_by_soma": managed_by_soma,
        "format_version": format_version,
        "current_format_version": CURRENT_HOOK_FORMAT_VERSION,
        "interpreters": {
            "soma_on_path": soma_path is not None,
            "soma_path": soma_path,
            "virtual_env": venv_env,
            "local_venv": local_venv,
            "python3": py3_path,
            "python3_valid": py3_valid,
        },
    }


def run_hook_install(args: Any) -> int:
    ws = getattr(args, "ws", None) or getattr(args, "workspace", None)
    force = getattr(args, "force", False)
    dry_run = getattr(args, "dry_run", False)
    use_json = getattr(args, "json", False)

    ok = install_hook(ws, force=force, dry_run=dry_run)
    if use_json:
        print(json.dumps({"status": "installed" if ok else "failed", "success": ok}))
    else:
        if ok:
            st = hook_status(ws)
            print(f"✅ Soma pre-commit hook installed ({st.get('hook_file')})")
        else:
            print("❌ Failed to install Soma pre-commit hook (no .git directory or symlink outside repo)", file=sys.stderr)
    return 0 if ok else 1


def run_hook_uninstall(args: Any) -> int:
    ws = getattr(args, "ws", None) or getattr(args, "workspace", None)
    force = getattr(args, "force", False)
    dry_run = getattr(args, "dry_run", False)
    use_json = getattr(args, "json", False)

    ok = uninstall_hook(ws, force=force, dry_run=dry_run)
    if use_json:
        print(json.dumps({"status": "uninstalled" if ok else "not_found", "success": ok}))
    else:
        if ok:
            print("✅ Soma pre-commit hook removed")
        else:
            print("ℹ️ No Soma pre-commit hook found to uninstall")
    return 0 if ok else 1


def run_hook_status(args: Any) -> int:
    ws = getattr(args, "ws", None) or getattr(args, "workspace", None)
    use_json = getattr(args, "json", False)
    st = hook_status(ws)

    if use_json:
        print(json.dumps(st, indent=2))
        return 0

    print("🪝 Soma Git Hook Status")
    print(f"  Repository Root: {st['repository_root']}")
    if not st["is_git_repo"]:
        print("  Hooks Directory: ❌ No .git directory found")
        return 0

    print(f"  Hooks Directory: {st['git_hooks_dir']}")
    print(f"  Worktree:        {'Yes (linked worktree)' if st['is_worktree'] else 'No (main repository)'}")

    if st["status"] == "installed":
        print(f"  Pre-commit Hook: ✅ Installed & Current (format: {st['format_version']})")
    elif st["status"] == "outdated":
        print(f"  Pre-commit Hook: ⚠️  Outdated format ({st['format_version']} < {st['current_format_version']}) — run 'soma hook install' to refresh")
    elif st["status"] == "unmanaged":
        print("  Pre-commit Hook: ⚠️  Existing pre-commit hook present (not managed by Soma)")
    else:
        print("  Pre-commit Hook: ❌ Not installed — run 'soma hook install'")

    interp = st.get("interpreters", {})
    print("  Environment Resolution:")
    soma_disp = f"✅ ({interp['soma_path']})" if interp.get("soma_on_path") else "❌ (not found)"
    print(f"    • soma on PATH: {soma_disp}")
    venv_disp = f"✅ ({interp['virtual_env']})" if interp.get("virtual_env") else "❌ (none active)"
    print(f"    • VIRTUAL_ENV:  {venv_disp}")
    local_disp = f"✅ ({interp['local_venv']})" if interp.get("local_venv") else "❌ (none)"
    print(f"    • .venv:        {local_disp}")
    py3_disp = f"✅ ({interp['python3']})" if interp.get("python3_valid") else "❌ (invalid or missing)"
    print(f"    • python3:      {py3_disp}")
    return 0


# ── Unified Hook Dispatcher ────────────────────────────────────────────────────

def run_hook(args: Any) -> int:
    """Hybrid dispatcher routing porcelain commands or legacy lifecycle phases."""
    action = getattr(args, "hook_action", None) or getattr(args, "phase", None)

    if action == "install":
        return run_hook_install(args)
    elif action == "status":
        return run_hook_status(args)
    elif action == "uninstall":
        return run_hook_uninstall(args)
    elif action is None:
        return run_hook_status(args)

    phase = action
    workspace = Path(args.workspace) if getattr(args, "workspace", None) else Path.cwd()

    if phase == "safety-gate":
        cmd = getattr(args, "cmd", None)
        payload = None
        if cmd is None and not sys.stdin.isatty():
            try:
                raw = sys.stdin.read().strip()
                if raw:
                    payload = json.loads(raw)
            except Exception:
                pass
        rc, res = run_safety_gate(cmd=cmd, payload=payload, workspace=workspace)
        print(json.dumps(res))
        return rc

    elif phase in ("pre-invocation", "governance-monitor", "immune-init"):
        payload = None
        if not sys.stdin.isatty():
            try:
                raw = sys.stdin.read().strip()
                if raw:
                    payload = json.loads(raw)
            except Exception:
                pass
        rc, res = run_pre_invocation(payload=payload, workspace=workspace)
        print(json.dumps(res))
        return rc

    elif phase == "post-session":
        from soma_core.sync import run_post_session_hook
        transcript_arg = getattr(args, "transcript", None)
        transcript_path = Path(transcript_arg) if transcript_arg else None
        use_json = getattr(args, "json", False)
        if not transcript_path and not sys.stdin.isatty():
            try:
                raw = sys.stdin.read().strip()
                if raw:
                    data = json.loads(raw)
                    t_str = data.get("transcript_path") or data.get("transcript")
                    if t_str:
                        transcript_path = Path(t_str)
            except Exception:
                pass

        if transcript_path and transcript_path.is_file():
            if use_json:
                rc = run_post_session_hook(transcript_path=transcript_path, repo_root=workspace, use_json=True)
            else:
                rc = run_post_session_hook(transcript_path=transcript_path, repo_root=workspace)
            return rc
        else:
            if use_json:
                print(json.dumps({"status": "skipped", "reason": "transcript not provided"}))
            else:
                print("Skipping post-session hook: transcript file not provided or does not exist", file=sys.stderr)
            return 0

    elif phase in ("session-close", "stop"):
        rc, res = run_session_close(workspace=workspace)
        print(json.dumps(res))
        return rc

    elif phase == "pre-commit":
        strict = getattr(args, "strict", False)
        use_json = getattr(args, "json", False)
        return run_pre_commit(workspace=workspace, strict=strict, use_json=use_json)

    else:
        print(f"Unknown hook command or phase: {phase}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for standalone hook runner."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    import argparse

    parser = argparse.ArgumentParser(
        prog="soma hook",
        description="Manage and run cross-platform Soma lifecycle hooks",
    )
    parser.add_argument(
        "phase",
        nargs="?",
        default="status",
        choices=[
            "install",
            "status",
            "uninstall",
            "pre-commit",
            "safety-gate",
            "pre-invocation",
            "session-close",
            "post-session",
            "governance-monitor",
            "immune-init",
            "stop",
        ],
        help="Hook command or lifecycle phase to execute (default: status)",
    )
    parser.add_argument(
        "--cmd",
        type=str,
        default=None,
        help="Command line string for safety-gate check",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="In pre-commit, exit 1 on issues",
    )
    parser.add_argument(
        "--workspace",
        default=None,
        help="Target workspace path",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force install or uninstall",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without modifying disk",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output",
    )
    parser.add_argument(
        "--transcript",
        default=None,
        help="Path to transcript.jsonl for post-session hook",
    )
    args = parser.parse_args(argv)
    return run_hook(args)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
