"""soma verify — run verification on changed files.

Supports Layer 1 (deterministic tools) and Layer 2 (adversarial LLM pair).
Maps Verdict outcomes to exit codes: SHIP=0, BLOCK=1, REVISE=1.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys


# Lazy imports to keep CLI responsive
def _get_verification():
    from immune_system.verification import runner, Verdict
    return runner, Verdict


# ── Exit Code Mapping ─────────────────────────────────────────────────

def _lazy_verdict():
    from immune_system.verification import Verdict
    return Verdict


class _VerdictExitCodesProxy(dict):
    """Lazy dict proxy for VERDICT_EXIT_CODES."""
    _loaded = False

    def _ensure(self):
        if not self._loaded:
            V = _lazy_verdict()
            super().__setitem__(V.SHIP, 0)
            super().__setitem__(V.BLOCK, 1)
            super().__setitem__(V.REVISE, 1)
            self._loaded = True

    def __getitem__(self, key):
        self._ensure()
        return super().__getitem__(key)

    def __contains__(self, key):
        self._ensure()
        return super().__contains__(key)

    def __len__(self):
        self._ensure()
        return super().__len__()

    def __iter__(self):
        self._ensure()
        return super().__iter__()


VERDICT_EXIT_CODES = _VerdictExitCodesProxy()


def verdict_to_exit_code(verdict) -> int:
    """Map a Verdict enum to an exit code."""
    VERDICT_EXIT_CODES._ensure()
    return VERDICT_EXIT_CODES[verdict]


# ── Target File Resolution ────────────────────────────────────────────

def resolve_target_files(args: argparse.Namespace) -> list[str]:
    """Resolve target files from --files flag or git staged/changed files."""
    if args.files:
        repo_root = os.path.abspath(getattr(args, 'repo_root', None) or os.getcwd())
        safe_files = []
        for f in args.files:
            resolved = os.path.normpath(os.path.join(repo_root, f))
            if not resolved.startswith(repo_root + os.sep) and resolved != repo_root:
                print(f"Warning: skipping out-of-tree file: {f}", file=sys.stderr)
                continue
            safe_files.append(f)
        if not safe_files:
            print("Error: all specified files are outside the repository", file=sys.stderr)
        return safe_files

    # Default: query git for staged/changed files
    git_cwd = getattr(args, 'repo_root', None) or os.getcwd()
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", "HEAD"],
            capture_output=True, text=True, timeout=10, cwd=git_cwd,
        )
        files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except (subprocess.SubprocessError, FileNotFoundError):
        files = []

    # Also check staged files
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True, text=True, timeout=10, cwd=git_cwd,
        )
        staged = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        files = list(dict.fromkeys(files + staged))  # dedupe, preserve order
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    return files


# ── Main Handler ──────────────────────────────────────────────────────

def run_verify(args: argparse.Namespace) -> int:
    """Run verification on target files.

    Args:
        args: Parsed CLI arguments with layer1_only, dry_run, files, repo_root.

    Returns:
        Exit code: 0 for SHIP, 1 for BLOCK/REVISE or errors.
    """
    runner, Verdict = _get_verification()

    # Resolve repo root
    repo_root = getattr(args, 'repo_root', None) or os.getcwd()
    if not os.path.isdir(repo_root):
        print(f"Error: repo root does not exist: {repo_root}", file=sys.stderr)
        return 1

    # Resolve target files
    target_files = resolve_target_files(args)

    # Fail if all explicit --files were filtered out (out-of-tree)
    if getattr(args, 'files', None) and not target_files:
        return 1

    # Validate file existence when explicit files are provided
    if getattr(args, 'files', None) and not getattr(args, 'dry_run', False):
        missing = [f for f in target_files if not os.path.exists(os.path.join(repo_root, f))]
        if missing:
            for f in missing:
                print(f"Error: file not found: {f}", file=sys.stderr)
            return 1

    # ── Dry Run ───────────────────────────────────────────────────────
    if getattr(args, 'dry_run', False):
        layer_mode = "Layer 1 only" if getattr(args, 'layer1_only', False) else "Layer 1 + Layer 2"
        print(f"Dry run — {layer_mode}")
        print(f"Repo root: {repo_root}")
        print(f"Files to verify ({len(target_files)}):")
        for f in target_files:
            print(f"  {f}")
        return 0

    # ── Run Layer 1 ───────────────────────────────────────────────────
    results = runner.run_layer1(
        changed_files=target_files,
        repo_root=repo_root,
    )

    layer1_pass = runner.gate_verdict(results)
    summary = runner.format_summary(results)
    print(summary)

    if getattr(args, 'layer1_only', False):
        return 0 if layer1_pass else 1

    # ── Run Layer 2 (full verification) ───────────────────────────────
    # Layer 2 requires an LLM backend which is not wired to the CLI yet.
    print("Note: Layer 2 (adversarial LLM verification) not yet configured. "
          "Use --layer1-only for deterministic checks.", file=sys.stderr)
    if not layer1_pass:
        return 1

    return 0
