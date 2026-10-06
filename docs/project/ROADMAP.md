# Soma Governance — Roadmap

> Features listed here are planned or in-progress. They are NOT yet shipped in the current release.
> A feature moves from this roadmap to the README only when:
> 1. Its behavioral test suite is written
> 2. All tests pass
> 3. It has a Claim Registry entry with status `unlocked`

## Shipped Features

### Layer 2 Verification
**Status**: ✅ SHIPPED (v0.60)  
AST-based verification tools with information-partitioned evaluation.

### Transcript Verifier
**Status**: ✅ SHIPPED (v0.60)  
Verify agent conversation transcripts against governance rules.

### Genesis
**Status**: ✅ SHIPPED (v0.70)  
Automated codebase scanning and governance cell candidate generation.

### Review Intensity Levels (Breeze → Supercell)
**Status**: ✅ SHIPPED (v0.60)  
Dynamic review depth escalation based on diff risk assessment.

### Phase 1 — Stop the Bleeding
**Status**: ✅ SHIPPED (v0.73)  
README stripped to earned claims, hook fix, claim registry, roadmap/release workflow docs.

### Phase 2 — Foundation
**Status**: ✅ SHIPPED (v0.74)  
Canonical cell parser, Wilson-bounded scoring, error hierarchy, 27-file parser migration.

## Phase 3 — v0.75 ✅ Shipped

### Credit Assignment
**Status**: ✅ Shipped (v0.75)  
**Tracking**: `claim_credit_assignment` in `docs/project/CLAIM_REGISTRY.json`  
Attribute session outcomes to the specific cells that fired, enabling causal fitness updates.

### Crossover (Structured Rule Merging)
**Status**: ✅ Shipped (v0.75)  
**Tracking**: `claim_structured_crossover` in `docs/project/CLAIM_REGISTRY.json`  
Field-level merge of parent cell attributes to create hybrid rules.

### Tournament Selection
**Status**: ✅ Shipped (v0.75)  
**Tracking**: `claim_tournament_selection` in `docs/project/CLAIM_REGISTRY.json`  
Competitive evaluation between rules to select higher-fitness survivors.

## Phase 4 — v0.80 ✅ Shipped

### Quorum Sensing (Multi-Rule Consensus)
**Status**: ✅ Shipped (v0.80)  
**Tracking**: `claim_quorum_sensing` in `docs/project/CLAIM_REGISTRY.json`  
Require agreement from multiple rules before taking high-stakes actions.

### Gate Enforcement (Invariant DSL)
**Status**: ✅ Shipped (v0.80)  
**Tracking**: `claim_gate_enforcement` in `docs/project/CLAIM_REGISTRY.json`  
CI-required invariant checks defined in cell YAML frontmatter.

## Phase 4.5 — v0.81 ✅ Shipped

### CI Outcome Reporter
**Status**: ✅ Shipped (v0.81)  
**Tracking**: CI step summary integration  
Report-only advisory showing which cells match changed files in PRs.

### Telemetry Consolidation
**Status**: ✅ Shipped (v0.81)  
Unified signal evidence writer and 3 telemetry bug fixes.

## Phase 4.6 — v0.82 ✅ Shipped

### Writer Migration
**Status**: ✅ Shipped (v0.82)  
Migrate all fitness signal writers to unified telemetry path.

### Documentation Reconciliation  
**Status**: ✅ Shipped (v0.82)  
Update ROADMAP and README to match shipped state.

## Phase 4.7 — v0.83 ✅ Shipped

### JIT Cell Cache
**Status**: ✅ Shipped (v0.83; hardened in v0.89)  
Content-fingerprinted in-memory cache for the MCP hot path. The canonical inventory captures exact bytes, rejects symlinked cell trees, detects concurrent changes, and invalidates even when an edit restores a file's mtime.

## Phase 4.8 — v0.84 ✅ Shipped

### Bug Registry
**Status**: ✅ Shipped (v0.84)  
Machine-parseable bug registry with verification enzyme and governance cell. Backfilled Bugs 1–5.

## Phase 4.9 — v0.85 ✅ Shipped

### Antifragile Hot Zones
**Status**: ✅ Shipped (v0.85)  
Hot zone engine feeds bug patterns into cell fitness scoring. Bugs make the system smarter.

## Phase 5.0 — v0.89.0 ✅ Shipped

### MCP Execution Security
**Status**: ✅ Shipped (v0.89.0)  
Opaque, stateful, session-bound cryptographic receipts. MCP write/execute tools safely verify client authority and enforce strict workspace confinement.

### Bug Registry
**Status**: ✅ Shipped (v0.89.0)
Open bug tracking, Windows/MCP platform compatibility categorizations.

## Phase 5.1 — v0.93.0 ✅ Shipped

### Autonomous Cell Lifecycle
**Status**: ✅ Shipped (v0.93.0)  
Unified cell lifecycle state machine (`NEW`, `SURVIVE`, `ADAPT`, `EXTINCT`, `APOPTOSIS`, `WALL`, `GENOME`) with Laplace-smoothed scoring, Wilson confidence bounds, protected rules guards, and atomic rollback semantics.

### Multi-Platform Hook Parity
**Status**: ✅ Shipped (v0.93.0)  
Native cross-platform lifecycle hook runner (`soma hook <phase>`) providing 100% parity across Linux, macOS, and native Windows (PowerShell 5.1 / 7). Resolved BUG-014 (UTF-8 encoding / BOM) and BUG-032 (lifecycle hooks). All 69 registered bugs verified fixed.

### Asynchronous Verification Engine
**Status**: ✅ Shipped (v0.93.0)  
Non-blocking Layer 2 verification over MCP (`soma_verify_changes` with `async_mode`) and read-only polling (`soma_poll_verification`) with m8ven annotations.

## Phase 5.2 — v0.94.0 ✅ Shipped

### Operational Resilience & Self-Healing
**Status**: ✅ Shipped (v0.94.0)  
Cross-process and thread-safe file locking (`soma_core/locking.py`) with stale lockfile recovery (>60s), self-healing file quarantine (`soma_core/quarantine.py`) isolating corrupt JSON/YAML state without read failures, and graceful daemon worker lifecycle management (`soma_core/verification_jobs.py`).

### Mathematical Invariants & Property-Based Verification
**Status**: ✅ Shipped (v0.94.0)  
Hardened Wilson score intervals and Laplace smoothing validated through exhaustive Hypothesis property-based testing (`tests/test_math_properties.py`), typed domain error hierarchy (`soma_core/errors.py`), and idempotent state transitions (`tests/test_idempotency.py`).

### Zero-Overhead Optimization & Pure-Python Enzymes
**Status**: ✅ Shipped (v0.94.0)  
Sub-0.1ms safety-gate fast-path allow-list for read-only commands (0.087ms mean latency), zero-copy directory scanning via `os.scandir`, parallelized test execution via `pytest-xdist` (3.9x speedup: 71s down to 18s), and complete pure-Python migration of 12 utility enzymes with backwards-compatible shell delegations.

## Phase 5.3 — v0.94.1 ✅ Shipped

### Concurrency Integrity & Reentrant Locking
**Status**: ✅ Shipped (v0.94.1)  
Thread-local recursion tracking (`_THREAD_STATE`) in `soma_core/locking.py` `workspace_lock` eliminating reentrant self-deadlock, and graceful worker shutdown invariant preservation in `soma_core/verification_jobs.py`.

### Cross-Platform Normalization & CI Portability
**Status**: ✅ Shipped (v0.94.1)  
Windows path backslash-to-slash normalization in `enzymes/fitness_updater.py` unblocking glob pattern matching (`src/**`), dynamic Python interpreter discovery in `install/install.ps1`, `sys.stdout.reconfigure(errors="replace")` guards across all CLI tools preventing `cp1252` encoding crashes, and CI runner xdist flag fix.

### Sandbox & Safety Gate Hardening
**Status**: ✅ Shipped (v0.94.1)  
Subshell metacharacter protection and destructive command flag detection (`-D`, `--output=`, `--ext-cmd=`) in `soma_cli/hooks.py` safety gate, path traversal confinement across `soma_mcp/tools.py` (`soma_scan`, `soma_propose_change`), atomic single-use cryptographic receipt invalidation on failed verification in `soma_core/receipts.py`, and pure-noise SNR `-inf` boundary invariant.

## Phase 5.4 — v0.95.0 ✅ Shipped

### Architecture Consolidation & Shell Enzyme Retirement
**Status**: ✅ Shipped (v0.95.0)  
Replaced bulky legacy shell implementations in `safety_gate.sh`, `immune_init.sh`, `session_close.sh`, and `cell_transfer.sh` with ultra-thin backward-compatible forwarding shims delegating to `soma_cli.hooks` and `soma_cli.transfer`, reducing over 800 lines of shell code with zero regression.

### Deep Defense & Sandbox Hardening
**Status**: ✅ Shipped (v0.95.0)  
Pre-tokenization quote/escape dequoting in safety gate blocking evasion bypasses (`\rm`, `r"m"`, `git diff --o\utput=`), word-bounded git branch deletion flags, git configuration/exec-path injection protection, and path confinement rejecting null bytes, Windows device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`), alternate data streams, and extended namespaces.

### Storage Resiliency & Process Lifecycle Hardening
**Status**: ✅ Shipped (v0.95.0)  
Crash-resilient atomic storage (`soma_core/storage.py`) with exponential backoff on Windows file locking sharing violations (`WinError 32`), new `soma quarantine` CLI subcommand (`list`, `inspect`, `prune`), universal `utf-8-sig` BOM handling, and worker thread registry tracking with bounded shutdown joins in `soma_core/verification_jobs.py`.

## Phase 5.5 — v0.96.0 ✅ Shipped

### Pure-Stdlib Core Layer & Codebase Consolidation
**Status**: ✅ Shipped (v0.96.0)  
Consolidated all functional domains (Scoring/Workspace, Arbitration, Enforcement, Defects, Insights, Homeostasis, Sync, Telemetry, and Cell Genetics/Lifecycle) into pure-stdlib `soma_core/`. Converted 58 enzyme modules into backward-compatible dual-mode forwarding shims with explicit re-exports, dynamic module dispatch, and console encoding compliance, reducing architectural bloat in preparation for 1.0.0.

## Phase 5.6 — v0.96.1 ✅ Shipped

### 100% Zero-Dependency Framework & Stdlib Frontmatter Engine
**Status**: ✅ Shipped (v0.96.1)  
Achieved complete zero-dependency architecture across all runtime surfaces (`soma_cli/`, `soma_core/`, `soma_mcp/`, `soma_sdk/`, `enzymes/`). Eliminated PyYAML from required dependencies (`dependencies = []` in `pyproject.toml`). Upgraded `soma_core.frontmatter` to support 100% of cell YAML patterns in pure Python standard library (wrapped plain scalars, same-indent sequences, literal/folded block scalars with chomping, and multiline quoted strings with unicode escapes), verified across 102 cells and 2,522 tests. Upgraded invariant SOMA-C01 to repository-wide SOMA-C02.

## Phase 5.7 — v0.97.0 ✅ Shipped

### The Sunset Phase: Legacy Enzymes Purge, Native Platform Adapters & Dynamic Colocality
**Status**: ✅ Shipped (v0.97.0)  
Purged all 75 legacy enzyme scripts and 4,277 lines of shell/PowerShell installers in favor of pure-Python native platform adapters (`soma_cli.platforms`). Transitioned the SDK facade and MCP endpoints to 100% in-process execution without subprocess overhead (ADR-013). Established canonical 1:1 mirrored test package directories (`tests/soma_core/`, `tests/soma_cli/`, etc.) with hermetic import isolation and fully dynamic candidate resolution in checkpoint verification.

## Phase 5.8 — v0.97.1 ✅ Shipped

### Structured Command Safety & Safety Gate Pattern De-bloating
**Status**: ✅ Shipped (v0.97.1)  
Adversarially audited and rejected proposed `RegexBuilder` class in favor of pure-stdlib `CommandAnalyzer` (`soma_core.command_safety`, ADR-014). Eliminated 123 lines of fragile, unmaintainable shell regexes in `soma_cli/hooks.py` while providing lexical tokenization, wrapper unwrapping (`sudo`, `env`, `nice`, `time`, `nohup`), quote-aware subshell and pipeline extraction, and bounded recursion depth clamps.

## Phase 5.9 — v0.98.0 ✅ Shipped

### Test Suite Rationalization & Deadwood Pruning
**Status**: ✅ Shipped (v0.98.0)  
Consolidated 83 individual 1:1 mirrored stub files into a single high-speed parameterized test suite (`tests/test_module_contracts.py`). Purged 11 obsolete test suites (2,647 LOC) guarding deleted v0.97.0 assets (`enzymes/`, `install.sh`, etc.), eliminated 140 dead skipped tests in pytest runs, preserved historical bug registry traceability via tombstone regressions, and added dedicated unit tests for `soma_sdk.analysis`.

## Phase 5.10 — v0.99.0 ✅ Shipped

### Core/CLI Decoupling & Legacy CLI Purge
**Status**: ✅ Shipped (v0.99.0)  
Decoupled command-line execution and argument parsing from `soma_core/`. Extracted pure `evaluate_cell_tiers()` into `soma_core.lifecycle` and wired `soma promote --tier-check`. Purged 29 dead `cli_*` functions across `soma_core/` (`lifecycle.py`, `homeostasis.py`, `defects.py`, `insights.py`, `sync.py`, `telemetry.py`, `arbitration.py`, `enforcement.py`). Deleted legacy pass-through `soma_cli/handlers/` and its test suite. Net code reduction of ~1,660 lines.

## Phase 5.11 — v0.100.0 ✅ Shipped

### Core God Module Decomposition & Verification Deduplication
**Status**: ✅ Shipped (v0.100.0)  
Decomposed `soma_core/telemetry.py` (1,911 LOC) into `soma_core/outcomes.py` and `soma_core/metrics.py`, leaving `soma_core/telemetry.py` as a ~450 LOC cohesive evidence ledger with proxy mutation mirroring. Decomposed `soma_core/sync.py` (1,206 LOC) into `soma_core/sentinels.py`. Deduplicated triplicate glob matchers across telemetry and enforcement into canonical `find_matching_cells` in `soma_core/cell_inventory.py`. Centralized OS locking inside `soma_core/locking.py`. Added colocated test suites `test_outcomes.py`, `test_metrics.py`, and `test_sentinels.py`.

## Phase 5.12 — v0.101.0 ✅ Shipped

### Immune System Unification & Lifecycle Consolidation
**Status**: ✅ Shipped (v0.101.0)  
Unified the verification framework by establishing `soma_core/verification/` as the canonical package housing 12 deterministic and adversarial verification modules. Replaced the 3,672 LOC in `immune_system/verification/*.py` with lightweight backward-compatibility facade modules mirroring attributes and re-exporting all symbols. Consolidated `evaluate_promotions` and `evaluate_demotions` directly into `soma_core/lifecycle.py`, eliminating the duplicate lifecycle engine. Streamlined `cli_cell_create` description generation in `soma_core/lifecycle.py`. Rerouted internal CLI, MCP, and Core callers to canonical verification paths. Purged deprecated enzyme stubs (`_safe_import_enzyme` and `_ENZYME_ALLOWLIST`). Updated scripts reference to 74 total scripts.

## Phase 5.13 — v0.102.0 ✅ Shipped

### Facade Hardening & Final Prune (Bloat Initiative Completion)
**Status**: ✅ Shipped (v0.102.0)  
Decomposed monolithic `execute_tool()` in `soma_mcp/tools.py` into modular per-tool handlers with a declarative dispatch map, fixing syntax anomalies. Streamlined `_list_cells_stdlib` while preserving `TOOL_DEFINITIONS` literal AST compliance. Pruned dead legacy enzyme stubs in `soma_sdk/governance.py` (`_run_script`, `replay`, `trends`, `dependencies`, `adversarial`) and write-hook dead code in `soma_sdk/cells.py`. Eliminated leftover empty shims (`DESTRUCTIVE_PATTERNS = ()` and `STARTER_RULES_LEGACY`). Optimized `soma_core/__init__.py` with PEP 562 dynamic attribute resolution, accelerating cold package import by ~16x (down to 3.3ms) and process startup to 41ms. Completed comprehensive 5-phase bloat and latency audit.

## Phase 6 — v0.103.0 ✅ Shipped

### Legacy Sunset & Lifecycle Modularization
**Status**: ✅ Shipped (v0.103.0)  
Sunsetted legacy `immune_system/` compatibility shims, pruning 18 forwarding files. Pruned unmaintained `soma_sdk_js/` zero-dependency Node.js client package. Sunsetted dead epoch migration CLI engine `soma_cli/migration.py` and `tests/test_migration.py` while ensuring continuous BUG-019 and BUG-025 test suite coverage via tombstone regressions in `tests/test_legacy_purged_regressions.py`. Purged dead `install/starter_pack.txt` stub. Modularized 1,884-line monolithic `soma_core/lifecycle.py` into a structured, highly maintainable `soma_core/lifecycle/` package (`constants`, `parsers`, `quorum`, `decay`, `creation`, `promotion`, `selection`) with backward-compatible symbol re-exporting.

## Research

### Antifragile Scaling
**Status**: Research  
Cells that perform better under stress receive fitness bonuses.

### External Validation Benchmarks
**Status**: Research  
Standardized benchmarks for comparing governance effectiveness across projects.

### Natural Language Rule Creation
**Status**: Experimental  
Create cells from natural language descriptions via `cell_create.sh --from-description`.

### Team Topology (Multi-Repo Sync)
**Status**: Experimental  
Synchronize governance rules across multiple repositories.

### Counterfactual ROI
**Status**: Research  
Causal inference for measuring governance impact.

