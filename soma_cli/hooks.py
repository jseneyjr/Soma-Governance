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

import argparse
import datetime
import fnmatch
import glob
import json
import os
import re
import shlex
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Tuple

# ── Safety Gate: Destructive Patterns ──────────────────────────────────────────

DESTRUCTIVE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # rm: catch -rf, -r -f, -fr, --recursive targeting home, root, current dir or wildcard
    (
        re.compile(
            r'(?:^|[;&|`\(\)\s])rm\s+(?:-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r|-r\s+-f|-f\s+-r|--recursive)\s+(?:/|~|/home|\$HOME|\.|\.\.|\*|\s*/|\s*~)'
        ),
        "Recursive delete targeting home/root directory or wildcard/current directory",
    ),
    # shutil.rmtree
    (re.compile(r'rmtree\('), "Recursive directory deletion (rmtree) detected"),
    # rmdir bypass
    (
        re.compile(r'rmdir\s+--ignore-fail-on-non-empty'),
        "rmdir with --ignore-fail-on-non-empty — bypasses safety check",
    ),
    # mkfs: formatting filesystem
    (
        re.compile(r'(?:^|[^a-zA-Z0-9_])mkfs(?:[^a-zA-Z0-9_]|$)'),
        "Filesystem format (mkfs) detected — destructive operation",
    ),
    # dd if=: raw disk write
    (
        re.compile(r'(?:^|[^a-zA-Z0-9_])dd\s+.*if='),
        "Raw disk write (dd) detected — destructive operation",
    ),
    # chmod 777: overly permissive
    (
        re.compile(r'chmod\s+777'),
        "chmod 777 — overly permissive, potential security risk",
    ),
    # kill -9 -1: kill all processes
    (
        re.compile(r'kill\s+-9\s+-1'),
        "kill -9 -1 — would kill all user processes",
    ),
    # sudo
    (
        re.compile(r'(?:^|[^a-zA-Z0-9_])sudo(?:[^a-zA-Z0-9_]|$)'),
        "sudo detected — elevated privileges require confirmation",
    ),
    # Piping remote content to shell
    (
        re.compile(
            r'curl\s+.*\|\s*(?:sh|bash)|wget\s+.*\|\s*(?:sh|bash)|iwr\s+.*\|\s*iex|irm\s+.*\|\s*iex',
            re.IGNORECASE,
        ),
        "Piping remote content to shell — potential code execution risk",
    ),
    # Git force push
    (
        re.compile(r'git\s+push\s+.*(?:-f|--force|--force-with-lease)'),
        "Force push detected — destructive-ops mandate requires confirmation",
    ),
    (
        re.compile(r'git\s+push\s+[^\s]+\s+\+'),
        "Force push via +refspec detected — destructive-ops mandate requires confirmation",
    ),
    # Git reset --hard
    (
        re.compile(r'git\s+reset\s+--hard'),
        "Hard reset — will discard uncommitted changes",
    ),
    # Git checkout -f
    (
        re.compile(r'git\s+checkout\s+-f'),
        "Force checkout — will discard uncommitted changes",
    ),
    # Git clean -f
    (
        re.compile(r'git\s+clean\s+.*-[a-zA-Z]*f'),
        "git clean -f — will permanently remove untracked files",
    ),
    # Bulk git staging
    (
        re.compile(r'git\s+add\s+(?:-A|\.|\./?|\*|--all)(?:\s+|$|[;&|>)])'),
        "Bulk staging (git add -A/./*/--all) — run git status first to verify file count",
    ),
    # Database destruction without WHERE
    (
        re.compile(
            r'(?:DROP\s+(?:TABLE|DATABASE)|DELETE\s+FROM\s+[a-zA-Z0-9_]+\s*|TRUNCATE\s+TABLE)',
            re.IGNORECASE,
        ),
        "Destructive database operation without WHERE clause",
    ),
    # Windows disk formatting
    (
        re.compile(r'(?:Format-Volume|Initialize-Disk|Clear-Disk)', re.IGNORECASE),
        "Disk partition format detected — destructive operation",
    ),
    # Windows PowerShell destructive delete
    (
        re.compile(
            r'Remove-Item\s+.*-Recurse\s+.*-Force|Remove-Item\s+.*-Force\s+.*-Recurse',
            re.IGNORECASE,
        ),
        "PowerShell recursive force delete detected",
    ),
    # Windows cmd destructive delete
    (
        re.compile(r'(?:del|rmdir)\s+/(?:s|q)\s+.*[/\\]', re.IGNORECASE),
        "Windows command-line recursive delete (/s /q) detected",
    ),
]

SECRET_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AKIA_REDACTED"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "ghp_REDACTED"),
    (re.compile(r"github_pat_[a-zA-Z0-9_]{20,}"), "github_pat_REDACTED"),
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "sk-REDACTED"),
    (re.compile(r"AIzaSy[a-zA-Z0-9_-]{33}"), "AIzaSy_REDACTED"),
    (re.compile(r"Bearer [a-zA-Z0-9._-]{20,}"), "Bearer REDACTED"),
    (re.compile(r"GEMINI_API_KEY=[^\s]*"), "GEMINI_API_KEY=REDACTED"),
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
        cmd = args.get("CommandLine") or args.get("command") or args.get("cmd") or ""

    if not cmd or not isinstance(cmd, str) or not cmd.strip():
        reason = "Unable to parse command — requesting confirmation"
        log_gate_event(cmd or "", "BLOCKED", reason, root)
        return 0, {
            "decision": "force_ask",
            "reason": f"🛡️ Safety Gate: {reason}",
        }

    for pattern, reason in DESTRUCTIVE_PATTERNS:
        if pattern.search(cmd):
            log_gate_event(cmd, "BLOCKED", reason, root)
            return 0, {
                "decision": "force_ask",
                "reason": f"🛡️ Safety Gate: {reason}",
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
        response["steps"] = steps

    return 0, response


# ── Session Close / Post-Session ──────────────────────────────────────────────

def run_session_close(workspace: Path | None = None) -> tuple[int, dict[str, Any]]:
    """Run session close lifecycle tasks (outcome evaluation and cell evolution)."""
    root = workspace or Path.cwd()
    scripts_dir = root / "enzymes"

    # 1. Outcome engine if available
    outcome_engine = scripts_dir / "outcome_engine.py"
    if outcome_engine.is_file():
        try:
            subprocess.run([sys.executable, str(outcome_engine)], cwd=root, capture_output=True, text=True)
        except Exception:
            pass

    # 2. Cell fitness if available
    cell_fitness = scripts_dir / "cell_fitness.py"
    if cell_fitness.is_file():
        try:
            subprocess.run([sys.executable, str(cell_fitness)], cwd=root, capture_output=True, text=True)
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
    root = workspace or Path.cwd()
    repo_root = root

    # 1. Deterministic quality checkpoint
    try:
        from immune_system.verification.checkpoint_checks import run_all_checks
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

    if triggered_cells:
        print(f"🧬 Soma: {len(triggered_cells)} governance cell(s) triggered by this commit ({', '.join(triggered_cells)})")

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
        print("🔴 New files without governance coverage:")
        for uf in uncovered_files:
            print(f"  ⚠️  {uf}")

    if mechanical_failed:
        print("❌ Commit blocked by mechanical enforcement gates.", file=sys.stderr)
        return 1

    if has_checkpoint_issues:
        if strict:
            print("❌ Commit blocked: quality checkpoint failed in strict mode.", file=sys.stderr)
            return 1
        else:
            print(f"⚠️  Quality checkpoint found {len(issues)} issue(s) (warn mode; commit allowed).")

    return 0


# ── Unified Hook Dispatcher ────────────────────────────────────────────────────

def run_hook(args: argparse.Namespace) -> int:
    """Dispatch hook commands based on phase argument."""
    phase = args.phase
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

    elif phase in ("session-close", "post-session", "stop"):
        rc, res = run_session_close(workspace=workspace)
        print(json.dumps(res))
        return rc

    elif phase == "pre-commit":
        strict = getattr(args, "strict", False)
        use_json = getattr(args, "json", False)
        return run_pre_commit(workspace=workspace, strict=strict, use_json=use_json)

    else:
        print(f"Unknown hook phase: {phase}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for standalone hook runner."""
    parser = argparse.ArgumentParser(
        prog="soma hook",
        description="Run cross-platform Soma lifecycle hooks",
    )
    parser.add_argument(
        "phase",
        choices=[
            "pre-commit",
            "safety-gate",
            "pre-invocation",
            "session-close",
            "post-session",
            "governance-monitor",
            "immune-init",
            "stop",
        ],
        help="Hook lifecycle phase to execute",
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
        "--json",
        action="store_true",
        help="Emit JSON output",
    )
    args = parser.parse_args(argv)
    return run_hook(args)


if __name__ == "__main__":
    sys.exit(main())
