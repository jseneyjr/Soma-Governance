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

    # None means the trace script crashed — fail closed
    if missing_lines is None:
        missing_lines = [-1]

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
    try:
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
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return False
    return os.path.exists(json_report)


def _try_coverage_module(test_file, target_dir, json_report, tmpdir):
    """Attempt coverage module. Returns True if JSON report was generated."""
    data_file = os.path.join(tmpdir, "coverage.data")
    try:
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
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return False
    try:
        subprocess.run(
            [
                sys.executable, "-m", "coverage", "json",
                f"--data-file={data_file}",
                "-o", json_report,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return False
    return os.path.exists(json_report)


def _run_trace_fallback(test_file, target_file, target_dir, tmpdir):
    """Use stdlib trace module via subprocess to find uncovered lines."""
    # Build a helper script that uses trace to run pytest and report coverage
    trace_script = os.path.join(tmpdir, "_trace_runner.py")
    results_file = os.path.join(tmpdir, "trace_results.json")

    with open(trace_script, "w") as f:
        f.write(
            _TRACE_SCRIPT_TEMPLATE.format(
                test_file_repr=repr(test_file),
                target_file_repr=repr(target_file),
                target_dir_repr=repr(target_dir),
                results_file_repr=repr(results_file),
            )
        )

    try:
        subprocess.run(
            [sys.executable, trace_script],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return None

    if not os.path.exists(results_file):
        return None

    with open(results_file, encoding='utf-8', errors='replace') as f:
        return json.load(f)


_TRACE_SCRIPT_TEMPLATE = '''\
"""Trace runner: executes pytest under trace and reports uncovered lines."""
import dis
import json
import os
import sys
import trace

# Run pytest with tracing
tracer = trace.Trace(count=True, trace=False, countfuncs=False, countcallers=False)
sys.argv = ["pytest", {test_file_repr}, "-x", "-q", "--no-header", "--tb=no"]
tracer.runfunc(
    __import__("pytest").main,
    [{test_file_repr}, "-x", "-q", "--no-header", "--tb=no"],
)

target_file = {target_file_repr}
results_file = {results_file_repr}

# Get counts: dict of (filename, lineno) -> count
counts = tracer.results().counts

# Determine which lines of the target were executed
executed_lines = set()
for (fname, lineno), count in counts.items():
    if count > 0 and os.path.abspath(fname) == target_file:
        executed_lines.add(lineno)

# Determine all executable lines in the target file.
# Disassembly via dis.findlinestarts precisely identifies executable bytecode
# statements while ignoring comments, multiline docstrings, and bare structural keywords.
all_lines = set()
try:
    with open(target_file, encoding='utf-8', errors='replace') as f:
        src = f.read()
    co = compile(src, target_file, "exec")
    def _extract_linestarts(code_obj):
        for offset, lineno in dis.findlinestarts(code_obj):
            if lineno > 0:
                all_lines.add(lineno)
        for const in code_obj.co_consts:
            if hasattr(const, "co_code"):
                _extract_linestarts(const)
    _extract_linestarts(co)
except Exception:
    all_lines = set()

# Fallback to source-line heuristic with multiline docstring state tracking
if not all_lines:
    in_triple_double = False
    in_triple_single = False
    with open(target_file, encoding='utf-8', errors='replace') as f:
        for i, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            if stripped.startswith("@"):
                continue

            # Handle triple-quote boundaries
            if not in_triple_single:
                if in_triple_double:
                    if '"""' in stripped:
                        in_triple_double = False
                    continue
                elif stripped.startswith('"""') or stripped.startswith('r"""') or stripped.startswith('f"""'):
                    content_after = stripped[stripped.find('"""') + 3:]
                    if '"""' not in content_after:
                        in_triple_double = True
                    continue

            if not in_triple_double:
                if in_triple_single:
                    if "\\'\\'\\'" in stripped:
                        in_triple_single = False
                    continue
                elif stripped.startswith("\\'\\'\\'") or stripped.startswith("r\\'\\'\\'") or stripped.startswith("f\\'\\'\\'"):
                    content_after = stripped[stripped.find("\\'\\'\\'") + 3:]
                    if "\\'\\'\\'" not in content_after:
                        in_triple_single = True
                    continue

            # Exclude bare structural keywords and closing brackets
            if stripped in ("else:", "try:", "finally:", ")", "]", "}}", "):", "],", "}},", "),"):
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
        return [-1]

    missing = list(file_data.get("missing_lines", []))
    # Also include branch-specific uncovered lines
    for from_line, to_line in file_data.get("missing_branches", []):
        if to_line not in missing:
            missing.append(to_line)
    return missing
