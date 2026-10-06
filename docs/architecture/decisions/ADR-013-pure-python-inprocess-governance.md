# ADR-013: Pure-Python In-Process Governance Engine & Facade Unification

## Status
**Accepted** (v0.97.0 — 2026-10-06)

## Context
In release v0.97.0, the legacy `enzymes/` directory containing standalone bash and python scripts was deprecated and purged to consolidate core logic into `soma_core/`. However, the public SDK facade (`soma_sdk/governance.py`), build system (`Makefile`), lifecycle hooks (`soma_cli/hooks.py`), and gate generators (`soma_core/enforcement.py`) retained legacy subprocess invocations:
1. **Broken SDK Facade**: `Governance` methods (`fitness_landscape`, `coverage_report`, `grade`, `create_cell`) routed calls through `_run_script()`, which attempted `importlib.resources.files('enzymes').joinpath(...)` and spawned subprocesses. When installed as a pure wheel without source code, these calls crashed with `RuntimeError: Soma enzyme script not found or failed to load: cell_fitness.py (No module named 'enzymes')`.
2. **Build System & Tooling Failure**: `Makefile:18` resolved `SOMA_PYTHON_BIN` via `. enzymes/soma_python.sh`, failing `make install`, `make doctor`, and `make validate`.
3. **Silent Session-Close Hooks**: `soma_cli/hooks.py:run_session_close()` checked for `outcome_engine.py` and `cell_fitness.py` under `root / "enzymes"`, silently skipping evolutionary cycles when the directory was absent.
4. **Shell Injection Vector in Enforcement**: Generated pre-commit scripts interpolated cell names into bash double quotes (`python3 -c "append_signal('.', {quoted_name}, ...)"`), allowing arbitrary command expansion if cell names contained `$(cmd)` or special characters.

## Decision
1. **Pure-Python In-Process Mandate**:
   - All `Governance` SDK methods (`fitness_landscape`, `coverage_report`, `grade`, `create_cell`, `create_cell_from_description`, `signal`, `quorum`, `scan`, `entropy`) must execute in-process via pure-Python APIs in `soma_core.lifecycle`, `soma_core.telemetry`, and `soma_core.scoring`.
   - Internal subprocess execution of repository or package script files is strictly prohibited. `_run_script()` is deprecated with an explicit `RuntimeError`.
2. **MCP Dictionary Guarantees**:
   - `soma_grade`, `soma_coverage`, and `soma_fitness` return typed dictionaries directly from in-process core calls.
   - If `calculate_immune_grade()` returns `None` (empty workspace), a structured fallback dictionary is guaranteed so MCP clients never receive raw text or `null`.
   - Remove `_safe_import_enzyme` and enzyme fallbacks for `soma_propose_change` and `soma_capture_insight`.
3. **Safe Shell Execution & Enforcement**:
   - Enforcement generators in `soma_core/enforcement.py` must pass cell names safely via `sys.argv[1]` to prevent shell interpolation:
     ```bash
     python3 -c "import sys; from soma_core.telemetry import append_signal; append_signal('.', sys.argv[1], 'tp', 'mechanical')" {quoted_name}
     ```
   - Gate assertions define complete cell dictionaries before calling `record_escaped_defect()`.
4. **Resilient Makefile Tooling**:
   - Replace bash source scripts with a robust shell loop probing `$SOMA_PYTHON`, `$VIRTUAL_ENV`, `python3`, `python`, `py`.
   - Update `make doctor` and `make validate` to verify `soma_*` packages.

## Consequences

### Positive
- **Guaranteed Portability**: Eliminates all shell subprocess dependencies from SDK and MCP execution, ensuring identical behavior across Windows, Linux, and macOS.
- **High Performance**: Eliminates process fork/exec overhead (~50ms per invocation down to <1ms in-process).
- **Security Hardening**: Completely removes shell injection vectors in pre-commit hook generators.
- **Reliable Wheel Smoke Testing**: Package installations pass isolated source-hidden validation.

### Negative / Trade-offs
- **Sunset of Standalone Scripts**: External scripts directly invoking `enzymes/*.sh` or `enzymes/*.py` are unsupported. All callers must use `soma` CLI subcommands or the `soma_sdk` Python API.

## Verification
- Verified by:
  - `pytest tests/test_governance.py`
  - `pytest tests/test_mcp_readonly_tools.py`
  - `pytest tests/test_enforcement.py tests/test_enforce_hooks.py tests/test_hooks_lifecycle.py`
  - `pytest tests/test_bayesian_correctness.py tests/test_exponential_decay.py tests/test_escaped_defects_behavioral.py`
  - `python3 -I .github/scripts/wheel_smoke.py`
