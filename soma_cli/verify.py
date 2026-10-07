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
    from soma_core.verification import runner, Verdict
    return runner, Verdict


# ── Exit Code Mapping ─────────────────────────────────────────────────

def _lazy_verdict():
    from soma_core.verification import Verdict
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
        repo_root = os.path.realpath(getattr(args, 'workspace', None) or getattr(args, 'repo_root', None) or getattr(args, '_project_root', None) or os.getcwd())
        safe_files = []
        for f in args.files:
            resolved = os.path.realpath(os.path.join(repo_root, f))
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


def discover_test_evidence(target_files: list[str], repo_root: str) -> tuple[list[str], str]:
    """Discover matching test files, parse test names via AST, and execute tests.

    Returns (test_names, test_results).
    """
    import ast
    all_test_names: list[str] = []
    discovered_test_files: list[str] = []

    for tf in target_files:
        full_path = os.path.join(repo_root, tf) if not os.path.isabs(tf) else tf
        basename = os.path.basename(full_path)
        if basename.startswith("test_") and basename.endswith(".py"):
            if os.path.isfile(full_path) and full_path not in discovered_test_files:
                discovered_test_files.append(full_path)
            continue

        stem = os.path.splitext(basename)[0]
        # Candidate test file locations
        candidates = [
            os.path.join(repo_root, os.path.dirname(tf), f"test_{stem}.py"),
            os.path.join(repo_root, "tests", f"test_{stem}.py"),
            os.path.join(repo_root, f"test_{stem}.py"),
        ]
        # Also check tests/ directory matching prefix
        tests_dir = os.path.join(repo_root, "tests")
        if os.path.isdir(tests_dir):
            try:
                for fname in os.listdir(tests_dir):
                    if fname.startswith(f"test_{stem}") and fname.endswith(".py"):
                        candidates.append(os.path.join(tests_dir, fname))
            except OSError:
                pass

        for cand in candidates:
            if os.path.isfile(cand) and cand not in discovered_test_files:
                discovered_test_files.append(cand)

    for test_file in discovered_test_files:
        try:
            with open(test_file, "r", encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.startswith("test_") and node.name not in all_test_names:
                        all_test_names.append(node.name)
        except Exception:
            continue

    if not discovered_test_files:
        return ([], "")

    # Run tests with python -m pytest
    run_outputs = []
    for test_file in discovered_test_files:
        try:
            res = subprocess.run(
                [sys.executable, "-m", "pytest", test_file, "-q", "--tb=no"],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=repo_root,
            )
            out = (res.stdout or "") + (res.stderr or "")
            run_outputs.append(f"[{os.path.basename(test_file)}]\n{out.strip()}")
        except Exception as e:
            run_outputs.append(f"[{os.path.basename(test_file)}] error: {e}")

    return (all_test_names, "\n\n".join(run_outputs))


# ── Plan & Provider Resolution ────────────────────────────────────────

def resolve_task_plan(args: argparse.Namespace, repo_root: str) -> str | None:
    """Resolve task plan from --plan, --plan-file, or standard plan conventions."""
    if getattr(args, 'plan', None):
        return args.plan.strip()

    plan_file = getattr(args, 'plan_file', None)
    if plan_file:
        plan_path = plan_file if os.path.isabs(plan_file) else os.path.join(repo_root, plan_file)
        if not os.path.isfile(plan_path):
            print(f"Error: plan file not found: {plan_file}", file=sys.stderr)
            return None
        try:
            with open(plan_path, encoding='utf-8') as f:
                return f.read().strip()
        except OSError as e:
            print(f"Error: could not read plan file {plan_file}: {e}", file=sys.stderr)
            return None

    # Check conventional plan files
    for default_name in ("docs/plan.md", ".soma/plan.md", "PLAN.md"):
        cand = os.path.join(repo_root, default_name)
        if os.path.isfile(cand):
            try:
                with open(cand, encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        return content
            except OSError:
                pass

    return None


def is_usable_provider(provider) -> bool:
    """Return True if provider can perform programmatic generation."""
    if provider is None:
        return False
    try:
        from soma_core.inference_provider import PromptOnlyProvider
        if isinstance(provider, PromptOnlyProvider):
            return False
    except ImportError:
        pass
    return hasattr(provider, 'generate') or callable(provider)


def resolve_cli_provider(args: argparse.Namespace, repo_root: str):
    """Resolve configured inference provider or return None if none available."""
    try:
        from soma_core.inference_provider import resolve_key, resolve_provider, PromptOnlyProvider
    except ImportError:
        return None

    explicit_provider = getattr(args, 'provider', None)
    if not explicit_provider:
        explicit_provider = resolve_key(repo_root, ["SOMA_INFERENCE_PROVIDER"])

    # If no provider is explicitly requested, check if any API key exists
    if not explicit_provider:
        has_key = any(
            resolve_key(repo_root, [k])
            for k in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
        )
        if not has_key:
            return None

    try:
        provider = resolve_provider(workspace=repo_root, provider_name=explicit_provider)
        if isinstance(provider, PromptOnlyProvider) and explicit_provider not in ("prompt-only", "prompt"):
            return None
        return provider
    except Exception as e:
        print(f"Warning: could not initialize inference provider: {e}", file=sys.stderr)
        return None


def format_layer2_summary(result) -> str:
    """Format Layer 2 arbitration results for CLI output."""
    from soma_core.verification import Verdict
    lines = []
    verdict_str = result.verdict.name if hasattr(result.verdict, 'name') else str(result.verdict)
    icon = "✅" if result.verdict == Verdict.SHIP else "🔴"
    lines.append(f"Layer 2: {icon} {verdict_str}")

    if result.divergences:
        lines.append(f"  Divergences ({len(result.divergences)}):")
        for d in result.divergences:
            pred_desc = f" [{d.prediction.severity.value}] {d.prediction.risk}" if d.prediction else ""
            lines.append(f"    - {d.category.value} ({d.divergence_type}):{pred_desc}")
            if d.resolution:
                lines.append(f"      Resolution: {d.resolution}")

    if result.convergences:
        lines.append(f"  Convergences ({len(result.convergences)}): {', '.join(c.value for c in result.convergences)}")

    return "\n".join(lines)


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
    repo_root = getattr(args, 'workspace', None) or getattr(args, 'repo_root', None) or getattr(args, '_project_root', None) or os.getcwd()
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

    # ── Clean Repository ──────────────────────────────────────────────
    if not target_files:
        print("Layer 1: 0 files changed (clean repository)")
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
    provider = resolve_cli_provider(args, repo_root)
    if provider is None:
        if not layer1_pass:
            return 1
        print("Notice: No inference provider configured. Layer 2 skipped (Layer 1 deterministic checks passed).",
              file=sys.stderr)
        return 0

    task_plan = resolve_task_plan(args, repo_root)
    if getattr(args, 'plan_file', None) and task_plan is None:
        return 1

    if not task_plan:
        if not layer1_pass:
            return 1
        print("Notice: No task plan provided (--plan or --plan-file). Layer 2 skipped (Layer 1 deterministic checks passed).",
              file=sys.stderr)
        return 0

    llm_backend = provider.generate if hasattr(provider, 'generate') else provider
    test_names, test_results = discover_test_evidence(target_files, repo_root)
    try:
        l2_result = runner.run_layer2(
            changed_files=target_files,
            repo_root=repo_root,
            task_plan=task_plan,
            layer1_evidence=results,
            llm_backend=llm_backend,
            test_names=test_names,
            test_results=test_results,
        )
    except Exception as e:
        print(f"Error: Layer 2 verification failed: {e}", file=sys.stderr)
        return 1

    print(format_layer2_summary(l2_result))
    l2_exit = verdict_to_exit_code(l2_result.verdict)
    if not layer1_pass or l2_exit != 0:
        return 1

    return 0
