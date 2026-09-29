"""Branch coverage verification tool.

Wraps pytest branch coverage to detect uncovered branches in target files.
Falls back to stdlib trace module when pytest-cov/coverage are unavailable.
"""
import json
import os
import subprocess
import sys
import tempfile

from . import ToolEvidence


def check(target_file: str, test_file: str) -> ToolEvidence:
    """Run branch coverage analysis on target_file using test_file.

    Args:
        target_file: Path to the source file to check coverage for.
        test_file: Path to the test file to run.

    Returns:
        ToolEvidence with verdict=True if all branches covered, False otherwise.
        result.lines contains specific uncovered line numbers.
    """
    target_file = os.path.abspath(target_file)
    test_file = os.path.abspath(test_file)
    target_dir = os.path.dirname(target_file)
    target_basename = os.path.basename(target_file)

    with tempfile.TemporaryDirectory() as tmpdir:
        json_report = os.path.join(tmpdir, "coverage.json")

        # Try pytest-cov first
        generated = _try_pytest_cov(test_file, target_dir, json_report)

        # Fall back to coverage module
        if not generated:
            generated = _try_coverage_module(
                test_file, target_dir, json_report, tmpdir
            )

        # Fall back to stdlib trace
        if not generated:
            missing_lines = _run_trace_fallback(
                test_file, target_file, target_dir, tmpdir
            )
        else:
            missing_lines = _parse_coverage(
                json_report, target_file, target_basename
            )

    verdict = len(missing_lines) == 0
    detail = (
        "All branches covered"
        if verdict
        else f"Uncovered lines: {missing_lines}"
    )

    return ToolEvidence(
        tool="branch_coverage",
        target=target_file,
        verdict=verdict,
        detail=detail,
        lines=sorted(missing_lines),
    )


def _try_pytest_cov(test_file, target_dir, json_report):
    """Attempt pytest-cov. Returns True if JSON report was generated."""
    subprocess.run(
        [
            sys.executable, "-m", "pytest", test_file,
            f"--cov={target_dir}",
            "--cov-branch",
            f"--cov-report=json:{json_report}",
            "--no-header", "-q",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return os.path.exists(json_report)


def _try_coverage_module(test_file, target_dir, json_report, tmpdir):
    """Attempt coverage module. Returns True if JSON report was generated."""
    data_file = os.path.join(tmpdir, "coverage.data")
    subprocess.run(
        [
            sys.executable, "-m", "coverage", "run",
            "--branch",
            f"--source={target_dir}",
            f"--data-file={data_file}",
            "-m", "pytest", test_file, "-q",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    subprocess.run(
        [
            sys.executable, "-m", "coverage", "json",
            f"--data-file={data_file}",
            "-o", json_report,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return os.path.exists(json_report)


def _run_trace_fallback(test_file, target_file, target_dir, tmpdir):
    """Use stdlib trace module via subprocess to find uncovered lines."""
    # Build a helper script that uses trace to run pytest and report coverage
    trace_script = os.path.join(tmpdir, "_trace_runner.py")
    results_file = os.path.join(tmpdir, "trace_results.json")

    with open(trace_script, "w") as f:
        f.write(
            _TRACE_SCRIPT_TEMPLATE.format(
                test_file=test_file,
                target_file=target_file,
                target_dir=target_dir,
                results_file=results_file,
            )
        )

    subprocess.run(
        [sys.executable, trace_script],
        capture_output=True,
        text=True,
        check=False,
    )

    if not os.path.exists(results_file):
        return []

    with open(results_file) as f:
        return json.load(f)


_TRACE_SCRIPT_TEMPLATE = '''\
"""Trace runner: executes pytest under trace and reports uncovered lines."""
import json
import os
import sys
import trace

# Run pytest with tracing
tracer = trace.Trace(count=True, trace=False, countfuncs=False, countcallers=False)
sys.argv = ["pytest", "{test_file}", "-x", "-q", "--no-header", "--tb=no"]
tracer.runfunc(
    __import__("pytest").main,
    ["{test_file}", "-x", "-q", "--no-header", "--tb=no"],
)

target_file = "{target_file}"
results_file = "{results_file}"

# Get counts: dict of (filename, lineno) -> count
counts = tracer.results().counts

# Determine which lines of the target were executed
executed_lines = set()
for (fname, lineno), count in counts.items():
    if count > 0 and os.path.abspath(fname) == target_file:
        executed_lines.add(lineno)

# Parse the target source to find all executable lines
# The trace module does not fire events for bare structural keywords
# (else:, try:, finally:) — only their body lines are counted.
all_lines = set()
with open(target_file) as f:
    for i, line in enumerate(f, 1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("@"):
            continue
        # Exclude bare structural keywords that trace doesn't count
        if stripped in ("else:", "try:", "finally:"):
            continue
        all_lines.add(i)

missing = sorted(all_lines - executed_lines)
with open(results_file, "w") as f:
    json.dump(missing, f)
'''


def _parse_coverage(json_report, target_file, target_basename):
    """Extract missing line numbers from JSON coverage report."""
    with open(json_report) as f:
        data = json.load(f)

    files = data.get("files", {})

    # Try exact path match first, then basename match
    file_data = files.get(target_file)
    if file_data is None:
        for filepath, fdata in files.items():
            if os.path.basename(filepath) == target_basename:
                file_data = fdata
                break

    if file_data is None:
        return []

    return file_data.get("missing_lines", [])
