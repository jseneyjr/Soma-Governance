"""Layer 1 Runner — orchestrates all deterministic verification tools.

Runs mandatory checks on changed files and produces a combined evidence package.
The output feeds directly into the Arbiter as Layer 1 evidence.
"""
import os
import sys
from typing import Optional

from . import ToolEvidence
from . import persistence_checker
from . import call_graph


def run_layer1(
    changed_files: list[str],
    repo_root: str,
    persistence_targets: Optional[list[tuple[str, str]]] = None,
) -> list[ToolEvidence]:
    """Run all Layer 1 verification tools.

    Args:
        changed_files: List of file paths that were modified
        repo_root: Root of the repository
        persistence_targets: List of (filepath, dict_name) tuples for
            persistence checking. If None, auto-detects from changed_files.

    Returns:
        List of ToolEvidence results for the Arbiter
    """
    results: list[ToolEvidence] = []

    # ── Persistence Completeness ──────────────────────────────────────
    if persistence_targets:
        for filepath, dict_name in persistence_targets:
            full_path = os.path.join(repo_root, filepath)
            if os.path.exists(full_path):
                results.append(persistence_checker.check(full_path, dict_name))

    # ── Call Graph Completeness ───────────────────────────────────────
    for filepath in changed_files:
        full_path = os.path.join(repo_root, filepath)
        if os.path.exists(full_path) and filepath.endswith('.py'):
            # Skip test files and __init__.py
            basename = os.path.basename(filepath)
            if basename.startswith('test_') or basename == '__init__.py':
                continue
            results.append(call_graph.check(
                full_path, repo_root,
                exclude_names={'main', '_parse_args', 'parse_args'}
            ))

    # ── Branch Coverage (placeholder — requires pytest execution) ─────
    # TODO: Implement branch_coverage.check() once the wrapper is built

    # ── Mutation Testing (placeholder — requires test execution) ──────
    # TODO: Implement mutation_tester.check() once the harness is built

    return results


def gate_verdict(results: list[ToolEvidence]) -> bool:
    """Simple gate: PASS if all tools pass, FAIL if any fails."""
    return all(r.verdict for r in results)


def format_summary(results: list[ToolEvidence]) -> str:
    """One-line summary of Layer 1 results."""
    passed = sum(1 for r in results if r.verdict)
    failed = sum(1 for r in results if not r.verdict)
    total = len(results)
    if failed:
        return f"Layer 1: {failed}/{total} FAILED — {', '.join(r.tool for r in results if not r.verdict)}"
    return f"Layer 1: {passed}/{total} PASSED"


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <repo_root> [file1 file2 ...]")
        sys.exit(1)

    repo_root = sys.argv[1]
    changed = sys.argv[2:] if len(sys.argv) > 2 else []

    results = run_layer1(changed, repo_root)
    for r in results:
        icon = "✅" if r.verdict else "🔴"
        print(f"{icon} {r.tool}: {r.target} — {r.detail}")

    print(f"\n{format_summary(results)}")
    sys.exit(0 if gate_verdict(results) else 1)
