# Scripts Reference

This document catalogs 74 executable scripts, command modules, SDK modules, and MCP/core modules in the Soma governance framework.

## Counting Method

Counts are generated from the source tree with mutually exclusive categories: package initializers (`__init__.py`, `__main__.py`) are excluded; `install/hooks/pre-commit` is counted as the lifecycle script; and all non-initializer `soma_core/*.py` modules are grouped with the MCP modules. This produces 74 unique paths with no double counting.

## Summary by Category

| Category | Primary Language / Location | Count | Description |
|:---------|:----------------------------|:------|:------------|
| [Lifecycle Scripts (Hooks)](#lifecycle-scripts-hooks--bash) | bash (`install/hooks/`) | 1 | Git pre-commit lifecycle hook |
| [Verification Scripts](#verification-scripts--python) | Python (`soma_core/verification/`) | 12 | Deterministic AST checkers, coverage tools, and adversarial verification |
| [CLI Commands](#cli-commands--python-soma_cli) | Python and bash (`soma_cli/`, root) | 21 | CLI launcher and command implementation modules |
| [SDK Modules](#sdk-modules--python-soma_sdk) | Python (`soma_sdk/`) | 8 | Canonical scoring, parsing, telemetry, hot-zone, and governance APIs |
| [MCP and Core Modules](#mcp-and-core-modules) | Python (`soma_mcp/`, `soma_core/`) | 32 | MCP transport, dispatch, confinement, content inventory, canonical evidence, cache, errors, receipts, and atomic storage |
| **Total** | | **74** | Unique paths under the method above |

---

## Lifecycle Scripts (Hooks) — bash

This bash script is invoked automatically by git triggers. Following the v0.97.0 sunset phase, all runtime lifecycle hooks are driven directly by pure Python in `soma_cli/hooks.py` and `soma_core/sync.py`.

| Script | Location | Purpose |
|:-------|:---------|:--------|
| **`pre-commit`** | `install/hooks/pre-commit` | Git pre-commit hook that evaluates governance cells on staged diffs and mechanically blocks commits on violations. |

---

## Verification Scripts — Python

These 12 Python scripts form the deterministic and adversarial verification engine in `soma_core/verification/`.

| Script | Location | Purpose |
|:-------|:---------|:--------|
| **`arbiter.py`** | `soma_core/verification/arbiter.py` | Deterministic divergence detector comparing Spec Agent predictions against Code Agent claims, backed by Layer 1 tool evidence. |
| **`branch_coverage.py`** | `soma_core/verification/branch_coverage.py` | Deterministic branch coverage verification tool wrapping pytest-cov or Python's stdlib `trace` module. |
| **`call_graph.py`** | `soma_core/verification/call_graph.py` | Layer 1 AST checker verifying function reachability from call sites across the codebase. |
| **`checkpoint_checks.py`** | `soma_core/verification/checkpoint_checks.py` | Canonical stdlib-only verification implementations (test coverage, git cleanliness, docstring presence) shared by CLI and MCP. |
| **`immune_verify.py`** | `soma_core/verification/immune_verify.py` | Adversarial pair enzyme orchestrating the information-partitioned Spec Agent vs Code Agent verification protocol. |
| **`import_guard.py`** | `soma_core/verification/import_guard.py` | Layer 1 AST tool detecting unguarded third-party imports to prevent runtime `ImportError` failures. |
| **`mutation_tester.py`** | `soma_core/verification/mutation_tester.py` | Lightweight AST mutation tester that synthesizes mutant functions to evaluate test suite fault-detection capabilities. |
| **`persistence_checker.py`** | `soma_core/verification/persistence_checker.py` | Layer 1 AST checker verifying that in-memory state mutations have corresponding persistent serialization paths. |
| **`quality_gate.py`** | `soma_core/verification/quality_gate.py` | Deterministic AST test quality gate validating assertion presence, detecting hollow tests, and enforcing behavioral test standards. |
| **`review_adapter.py`** | `soma_core/verification/review_adapter.py` | Converts multi-agent review findings into structured Prediction and Claim objects for Arbiter evaluation. |
| **`runner.py`** | `soma_core/verification/runner.py` | Layer 1 orchestration runner executing all deterministic AST and coverage checks to produce a combined evidence package. |
| **`transcript_verifier.py`** | `soma_core/verification/transcript_verifier.py` | Orchestrator-level subagent transcript verifier extracting objective metrics (test passes, file modifications, fix cycles) from JSONL logs. |

---

## CLI Commands — Python (`soma_cli/`)

These 21 paths provide the root `soma` launcher and 20 non-initializer Python modules in `soma_cli/`. Fifteen modules implement registered subcommands; scanner/generator modules support Genesis, `pathcheck.py` supports `soma doctor` and the installers, and `migration.py` implements evidence epoch cutover.

| Command / Script | Location | Purpose |
|:-----------------|:---------|:--------|
| **`soma`** | `soma` | Root executable bash launcher with symlink resolution and environment configuration for the CLI. |
| **`cli.py`** | `soma_cli/cli.py` | Main CLI entrypoint and argument dispatcher routing user commands to subcommand modules. |
| **`checkpoint.py`** | `soma_cli/checkpoint.py` | `soma checkpoint`: Deterministic quality checks (test coverage, git status, docstring presence) without LLM calls. |
| **`completion.py`** | `soma_cli/completion.py` | `soma completion {bash,zsh,fish}`: Prints a shell completion script generated at runtime from the argparse parser, so it never drifts from the CLI. Never edits dotfiles. |
| **`demote.py`** | `soma_cli/demote.py` | `soma demote`: Evaluates and displays cell demotion candidates when false positive rates exceed acceptable bounds. |
| **`doctor.py`** | `soma_cli/doctor.py` | `soma doctor`: System health check verifying workspace structure, rules, configuration, and dependencies, the pre-commit hook format (BUG-047) and the MCP `python3` launcher (Windows Store stub). `--fix-path [--yes]` opt-in appends the PATH line to the zsh/bash/fish rc file and records it in `~/.soma/manifest.json` (`path_lines`). |
| **`genesis.py`** | `soma_cli/genesis.py` | `soma genesis`: Analyzes codebase architecture with 8 language-agnostic detectors and generates governance cell candidates. |
| **`genesis_generator.py`** | `soma_cli/genesis_generator.py` | Generates candidate cell files in `vacuoles/` and architecture map `docs/organelles.md` from scan results. |
| **`genesis_scanner.py`** | `soma_cli/genesis_scanner.py` | Language-agnostic codebase scanner detecting 8 architectural patterns for governance cell candidate generation. |
| **`hooks.py`** | `soma_cli/hooks.py` | `soma hook <phase>`: Pure Python cross-platform lifecycle hook runner for `pre-commit`, `safety-gate`, `pre-invocation`, and `session-close`. |
| **`init.py`** | `soma_cli/init.py` | `soma init`: Initializes rules for Gemini, Claude Code, Cursor, or Copilot; it does not auto-detect Kiro. |
| **`migration.py`** | `soma_cli/migration.py` | Generation-fenced evidence cutover: locks writers, reconciles legacy ledgers into canonical `signals.jsonl`, snapshots source bytes with `SHA256SUMS`, atomically publishes converted signals, then advances the epoch. |
| **`oracle.py`** | `soma_cli/oracle.py` | `soma oracle`: Cell health classification, diagnostics, and pruning recommendations (wraps `oracle_checkpoint.py`). |
| **`pathcheck.py`** | `soma_cli/pathcheck.py` | Shell-aware PATH guidance: finds where pip installed `soma` and prints the line to add for zsh, bash, fish or PowerShell. Used by `soma doctor` and the installers; never edits dotfiles itself (`soma doctor --fix-path` does, on request). |
| **`promote.py`** | `soma_cli/promote.py` | `soma promote`: Evaluates and displays high-performing local cells eligible for promotion to forest-floor rules. |
| **`quarantine.py`** | `soma_cli/quarantine.py` | `soma quarantine`: Inspects, lists, and prunes damaged or corrupted files isolated in `.soma/quarantine/`. |
| **`report.py`** | `soma_cli/report.py` | `soma report`: Session report card showing triggered rules, event counts, and ASCII activity distributions. |
| **`status.py`** | `soma_cli/status.py` | `soma status`: Displays active rules, cell inventory, operational metrics, and governance status. Counts rules merged into Claude's `CLAUDE.md` as well as loose rule files. |
| **`sync.py`** | `soma_cli/sync.py` | `soma sync`: Rebuilds cell fitness frontmatter from canonical `.soma/evidence/signals.jsonl`. |
| **`transfer.py`** | `soma_cli/transfer.py` | `soma transfer`: Transfers a governance cell to another project with fitness reset and generation incrementation. |
| **`verify.py`** | `soma_cli/verify.py` | `soma verify`: Runs verification on changed files (Layer 1 deterministic tools and Layer 2 adversarial LLM pair). |

---



---

## SDK Modules — Python (`soma_sdk/`)

These 8 non-initializer modules provide the canonical Python APIs used by the CLI, MCP server, and enzymes.

| Module | Location | Purpose |
|:-------|:---------|:--------|
| **`errors.py`** | `soma_sdk/errors.py` | Structured error hierarchy for governance operations (parse errors, validation failures, scoring exceptions). |
| **`scoring.py`** | `soma_sdk/scoring.py` | Wilson interval confidence-bound scoring and related fitness calculations. |
| **`cells.py`** | `soma_sdk/cells.py` | Canonical YAML frontmatter parser and cell file utilities. |
| **`governance.py`** | `soma_sdk/governance.py` | Governance state API for querying active rules, cells, and configuration. |
| **`analysis.py`** | `soma_sdk/analysis.py` | Analytical utilities for fitness landscapes, trends, and evidence aggregation. |
| **`hot_zones.py`** | `soma_sdk/hot_zones.py` | Computes file and root-cause heat from the bug registry for antifragile fitness boosts. |
| **`invariants.py`** | `soma_sdk/invariants.py` | Evaluates the cell invariant DSL and enforcement tiers. |
| **`telemetry.py`** | `soma_sdk/telemetry.py` | Canonical locked, idempotent, generation-fenced writer for `.soma/evidence/signals.jsonl`. |

---

## MCP and Core Modules

These 32 modules implement the MCP server, state-bound authorization, safe cell inventory, frontmatter parsing, lifecycle state machine, verification job orchestration, canonical evidence reading, transactional resource locking, self-healing quarantine, atomic storage, and standardized domain errors. Package initializers and `soma_mcp/__main__.py` are excluded from the count.

| Module | Location | Purpose |
|:-------|:---------|:--------|
| **`server.py`** | `soma_mcp/server.py` | JSON-RPC transport, capability filtering, canonical `SOMA_WORKSPACE` injection, and receipt issuance/redemption. |
| **`tools.py`** | `soma_mcp/tools.py` | Canonical 19-tool definitions and implementations for read, write, and execute operations. |
| **`security.py`** | `soma_mcp/security.py` | Workspace/path confinement and cell-name validation. |
| **`integrity.py`** | `soma_mcp/integrity.py` | Cell manifest generation, signing, and verification. |
| **`cell_cache.py`** | `soma_mcp/cell_cache.py` | Content-fingerprinted parsed-cell cache using the canonical race-detecting inventory; stale or unsafe trees fail closed. |
| **`jit_engine.py`** | `soma_mcp/jit_engine.py` | JIT cell matching, frontmatter parsing, and governance expression. |
| **`scoring.py`** | `soma_core/scoring.py` | Zero-dependency Wilson interval lower bound and SNR confidence calculations. |
| **`workspace.py`** | `soma_core/workspace.py` | Zero-dependency workspace root discovery from any filesystem path. |
| **`arbitration.py`** | `soma_core/arbitration.py` | Test-to-code (TTC) verification, deterministic oracle scoring, and checkpoint validation. |
| **`enforcement.py`** | `soma_core/enforcement.py` | Cell enforcement, CI outcome reporting, bug registry integrity, and documentation claim verification. |
| **`defects.py`** | `soma_core/defects.py` | Escaped defect tracking, cell expiry pruning, and hot zone diagnosis. |
| **`insights.py`** | `soma_core/insights.py` | Structured insight capture and correlation engine. |
| **`homeostasis.py`** | `soma_core/homeostasis.py` | Session sleep consolidation, system coherence, interoception health check, and resilience engine. |
| **`sync.py`** | `soma_core/sync.py` | Escalation sentinel, liveness sentinel, team sync, HGT ribosome, immune sweep, and post-session hooks. |
| **`telemetry.py`** | `soma_core/telemetry.py` | Telemetry signal collection, outcome processing, fitness updating, metrics snapshots, cell quorum, coverage, and immune grading. |
| **`receipts.py`** | `soma_core/receipts.py` | In-memory single-use receipts bound to session, workspace, operation, exact arguments, target-file digest, canonical cell fingerprint, and expiry. |
| **`cell_inventory.py`** | `soma_core/cell_inventory.py` | Captures stable cell bytes and content fingerprints without following symlinks; detects concurrent changes and unsafe trees. |
| **`evidence.py`** | `soma_core/evidence.py` | Standard-library canonical reader for weighted `signals.jsonl` evidence, independent trigger/outcome dimensions, and structured parse errors. |
| **`errors.py`** | `soma_core/errors.py` | Standardized typed domain error hierarchy (`SomaError`, `SomaValidationError`, `CellCorruptError`, `ReceiptExpiredError`, `LockTimeoutError`). |
| **`frontmatter.py`** | `soma_core/frontmatter.py` | Standalone zero-dependency frontmatter parsing and YAML header extraction decoupled from MCP runtime. |
| **`lifecycle.py`** | `soma_core/lifecycle.py` | Canonical cell lifecycle state machine (`NEW`, `SURVIVE`, `ADAPT`, `EXTINCT`, `APOPTOSIS`, `WALL`, `GENOME`) with Laplace smoothing and protected rule guards. |
| **`locking.py`** | `soma_core/locking.py` | Cross-platform transactional resource locking with timeout fences and native Windows fallback. |
| **`quarantine.py`** | `soma_core/quarantine.py` | Self-healing quarantine isolating damaged YAML cells and unparseable JSONL files to preserve system availability. |
| **`storage.py`** | `soma_core/storage.py` | Crash-resilient atomic file writes via temporary files, directory fsync, and exponential backoff retry on Windows sharing violations (WinError 32). |
| **`verification_jobs.py`** | `soma_core/verification_jobs.py` | In-memory asynchronous verification job store and background thread worker for Layer 2 verification. |
| **`inference_provider.py`** | `soma_core/inference_provider.py` | Inference provider abstraction layer with secure credential lookup and key management for AI-assisted operations. |
| **`sweep_session.py`** | `soma_core/sweep_session.py` | Session transcript scanning, signal aggregation, and metric collection for sweep operations. |
| **`evidence_collector.py`** | `soma_core/evidence_collector.py` | Ground-truth evidence collection and observation processing for rule evaluation. |
| **`command_safety.py`** | `soma_core/command_safety.py` | Pure-stdlib lexical command tokenizer, wrapper unrolling automaton, and structured safety-gate analyzer. |
| **`outcomes.py`** | `soma_core/outcomes.py` | Verifiable outcome reflection, credit assignment, fitness signals, transcript updater, and ACE reflector loop. |
| **`metrics.py`** | `soma_core/metrics.py` | Metrics snapshots, token census aggregation, cell quorum sensing, coverage mapping, and immune report cards. |
| **`sentinels.py`** | `soma_core/sentinels.py` | Subagent liveness & deadlock detection, protocol escalation recommender, and last-gasp apoptosis sentinels. |

---

## Privacy Invariant

All scripts in this catalog are strictly constrained by the **Soma Privacy Invariant**: No script may output, log, or transmit raw file paths, usernames, hostnames, directory structures, code diffs, or patches outside the local environment. Only aggregate counts, booleans, and sanitized strings are permitted across telemetry and external synchronization.
