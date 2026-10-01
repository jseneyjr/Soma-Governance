# Scripts Reference

This document catalogs the 87 executable scripts and tools that power the Soma governance framework.

## Summary by Category

| Category | Primary Language / Location | Count | Description |
|:---------|:----------------------------|:------|:------------|
| [Lifecycle Scripts (Hooks)](#lifecycle-scripts-hooks--bash) | bash (`enzymes/`, `install/hooks/`) | 7 | Environment, agent execution, and pre-commit lifecycle hooks |
| [Verification Scripts](#verification-scripts--python) | Python (`immune_system/verification/`) | 13 | Deterministic AST checkers, coverage tools, and adversarial verification |
| [CLI Commands](#cli-commands--python-soma_cli) | Python & bash (`soma_cli/`, root) | 12 | User-facing commands and binary wrapper for the `soma` CLI |
| [Install Scripts](#install-scripts--bash) | bash (`install/`, root) | 3 | Multi-platform installers, uninstaller, and root wrapper |
| [Utility Scripts](#utility-scripts) | Python & bash (`enzymes/`, root) | 52 | Cell genetics, runtime engines, telemetry, and shared utilities |
| **Total** | | **87** | |

---

## Lifecycle Scripts (Hooks) — bash

These 7 bash scripts are invoked automatically by the IDE, terminal hook systems, or git triggers.

| Script | Location | Purpose |
|:-------|:---------|:--------|
| **`immune_init.sh`** | `enzymes/immune_init.sh` | PreInvocation hook that fires before model calls. Sets up the workspace, seeds agent contexts, injects domain hints, and runs pre-flight scans. |
| **`safety_gate.sh`** | `enzymes/safety_gate.sh` | PreToolUse hook that screens tool commands for destructive or globally scoped operations (e.g., `rm -rf /`, `git push -f`). |
| **`session_close.sh`** | `enzymes/session_close.sh` | Post-session cleanup hook that exports conversation logs, triggers offline memory consolidation (`soma_sleep.py`), and executes local reporting. |
| **`post_session_hook.sh`** | `enzymes/post_session_hook.sh` | Post-session hook that parses session transcripts and updates cell fitness data in `.soma/evidence/`. |
| **`escalation_sentinel.sh`** | `enzymes/escalation_sentinel.sh` | Zero-token review escalation recommender. Analyzes staged and unstaged git changes to recommend review levels (Breeze vs Trident vs Tempest). |
| **`liveness_sentinel.sh`** | `enzymes/liveness_sentinel.sh` | Subagent dispatch health monitor during multi-agent orchestration. Detects stalled or deadlocked agents. |
| **`pre-commit`** | `install/hooks/pre-commit` | Git pre-commit hook that evaluates governance cells on staged diffs and mechanically blocks commits on violations. |

---

## Verification Scripts — Python

These 13 Python scripts form the deterministic and adversarial verification engine in `immune_system/verification/`.

| Script | Location | Purpose |
|:-------|:---------|:--------|
| **`arbiter.py`** | `immune_system/verification/arbiter.py` | Deterministic divergence detector comparing Spec Agent predictions against Code Agent claims, backed by Layer 1 tool evidence. |
| **`branch_coverage.py`** | `immune_system/verification/branch_coverage.py` | Deterministic branch coverage verification tool wrapping pytest-cov or Python's stdlib `trace` module. |
| **`call_graph.py`** | `immune_system/verification/call_graph.py` | Layer 1 AST checker verifying function reachability from call sites across the codebase. |
| **`checkpoint_checks.py`** | `immune_system/verification/checkpoint_checks.py` | Canonical stdlib-only verification implementations (test coverage, git cleanliness, docstring presence) shared by CLI and MCP. |
| **`immune_verify.py`** | `immune_system/verification/immune_verify.py` | Adversarial pair enzyme orchestrating the information-partitioned Spec Agent vs Code Agent verification protocol. |
| **`import_guard.py`** | `immune_system/verification/import_guard.py` | Layer 1 AST tool detecting unguarded third-party imports to prevent runtime `ImportError` failures. |
| **`lifecycle.py`** | `immune_system/verification/lifecycle.py` | Deterministic cell lifecycle transition engine computing promotion, demotion, and retirement decisions from empirical evidence. |
| **`mutation_tester.py`** | `immune_system/verification/mutation_tester.py` | Lightweight AST mutation tester that synthesizes mutant functions to evaluate test suite fault-detection capabilities. |
| **`persistence_checker.py`** | `immune_system/verification/persistence_checker.py` | Layer 1 AST checker verifying that in-memory state mutations have corresponding persistent serialization paths. |
| **`quality_gate.py`** | `immune_system/verification/quality_gate.py` | Deterministic AST test quality gate validating assertion presence, detecting hollow tests, and enforcing behavioral test standards. |
| **`review_adapter.py`** | `immune_system/verification/review_adapter.py` | Converts multi-agent review findings into structured Prediction and Claim objects for Arbiter evaluation. |
| **`runner.py`** | `immune_system/verification/runner.py` | Layer 1 orchestration runner executing all deterministic AST and coverage checks to produce a combined evidence package. |
| **`transcript_verifier.py`** | `immune_system/verification/transcript_verifier.py` | Orchestrator-level subagent transcript verifier extracting objective metrics (test passes, file modifications, fix cycles) from JSONL logs. |

---

## CLI Commands — Python (`soma_cli/`)

These 12 scripts provide the command-line interface for Soma, including the root shell launcher and all 11 subcommands in `soma_cli/`.

| Command / Script | Location | Purpose |
|:-----------------|:---------|:--------|
| **`soma`** | `soma` | Root executable bash launcher with symlink resolution and environment configuration for the CLI. |
| **`cli.py`** | `soma_cli/cli.py` | Main CLI entrypoint and argument dispatcher routing user commands to subcommand modules. |
| **`checkpoint.py`** | `soma_cli/checkpoint.py` | `soma checkpoint`: Deterministic quality checks (test coverage, git status, docstring presence) without LLM calls. |
| **`demote.py`** | `soma_cli/demote.py` | `soma demote`: Evaluates and displays cell demotion candidates when false positive rates exceed acceptable bounds. |
| **`doctor.py`** | `soma_cli/doctor.py` | `soma doctor`: System health check verifying workspace structure, rules, configuration, and dependencies. |
| **`init.py`** | `soma_cli/init.py` | `soma init`: Initializes Soma governance for a project, detecting platform and project type, installing starter rules. |
| **`oracle.py`** | `soma_cli/oracle.py` | `soma oracle`: Cell health classification, diagnostics, and pruning recommendations (wraps `oracle_checkpoint.py`). |
| **`promote.py`** | `soma_cli/promote.py` | `soma promote`: Evaluates and displays high-performing local cells eligible for promotion to forest-floor rules. |
| **`report.py`** | `soma_cli/report.py` | `soma report`: Session report card showing triggered rules, event counts, and ASCII activity distributions. |
| **`status.py`** | `soma_cli/status.py` | `soma status`: Displays active rules, cell inventory, operational metrics, and governance status. |
| **`sync.py`** | `soma_cli/sync.py` | `soma sync`: Reconciles empirical JSONL evidence (`fitness.jsonl`, `outcomes.jsonl`) into cell YAML frontmatter. |
| **`verify.py`** | `soma_cli/verify.py` | `soma verify`: Runs verification on changed files (Layer 1 deterministic tools and Layer 2 adversarial LLM pair). |

---

## Install Scripts — bash

These 3 bash scripts manage the installation and clean removal of Soma across development environments.

| Script | Location | Purpose |
|:-------|:---------|:--------|
| **`install.sh`** | `install/install.sh` | Unified installer deploying steering rules, skills, and hooks across supported platforms (Gemini, Antigravity, Claude, Copilot, Kiro). |
| **`uninstall.sh`** | `install/uninstall.sh` | Clean uninstaller that removes Soma files using `~/.soma/manifest.json`, with automated backup and restore capabilities. |
| **`install.sh`** | `install.sh` | Root-level convenience wrapper delegating directly to `install/install.sh`. |

---

## Utility Scripts

These 52 scripts encompass the master pipeline orchestrator, evolutionary computation enzymes, runtime verification engines, telemetry scanners, and shared infrastructure libraries.

### 1. Master Pipeline Orchestrator (1 script)

| Script | Location | Purpose |
|:-------|:---------|:--------|
| **`soma_run.py`** | `soma_run.py` | Master execution orchestrator connecting all Soma engines into a unified pipeline (Oracle Check -> Change Execution -> Outcome Verification -> Interoception -> Coherence). |

### 2. Cell Evolutionary Lifecycle & Genetics (19 scripts)

| Script | Location | Purpose |
|:-------|:---------|:--------|
| **`cell_selection.sh`** | `enzymes/cell_selection.sh` | Shell entrypoint for evaluating local cell fitness, invoking `cell_fitness.py` and downstream adaptation scripts. |
| **`cell_fitness.py`** | `enzymes/cell_fitness.py` | Computes cell fitness scores using a Beta-Binomial posterior with Jeffrey's prior from empirical TP/FP/trigger counts. |
| **`cell_adapt.py`** | `enzymes/cell_adapt.py` | Modifies underperforming cells (score 0.3–0.7) by refining hypotheses, predictions, and target paths to improve SNR. |
| **`cell_promote.py`** | `enzymes/cell_promote.py` | Promotes high-performing cells (score > 0.7) into global forest-floor rules with decay weighting to prevent Beta-locking. |
| **`cell_demote.py`** | `enzymes/cell_demote.py` | Demotes global rules back to local cells when they cause false positives in new repository contexts. |
| **`cell_signal.sh`** | `enzymes/cell_signal.sh` | External fitness signal API allowing CI/CD, test suites, or humans to record TP/FP/FN outcomes back to cells. |
| **`cell_scan.py`** | `enzymes/cell_scan.py` | Evaluates git diffs against cell `target_paths` globs to trigger matching governance cells. |
| **`cell_create.sh`** | `enzymes/cell_create.sh` | Programmatic cell creation CLI for automated systems, incident responses, or test failures. |
| **`cell_create_nl.py`** | `enzymes/cell_create_nl.py` | Natural language cell creation via Gemini API, synthesizing complete governance cells from plain English descriptions. |
| **`cell_crossover.py`** | `enzymes/cell_crossover.py` | Genetic algorithm crossover operator merging hypotheses from two high-fitness parent cells into a new offspring cell. |
| **`cell_tournament.py`** | `enzymes/cell_tournament.py` | Tournament selection operator picking k random cells and returning the fittest to preserve diversity during pruning. |
| **`cell_metamorphose.py`** | `enzymes/cell_metamorphose.py` | Transforms cell maturity types (Vacuoles harden into Walls, Walls graduate to Rules) based on empirical proof. |
| **`cell_transfer.sh`** | `enzymes/cell_transfer.sh` | Horizontal gene transfer utility copying cells to other projects with fitness resets and probation tracking. |
| **`cell_genesis_stochastic.py`** | `enzymes/cell_genesis_stochastic.py` | Probabilistic diversity injection sampling domain templates periodically to prevent evolutionary monoculture. |
| **`cell_expiry.py`** | `enzymes/cell_expiry.py` | Audits governance cells against `expiry_days` and `expiry_sessions` limits, recommending or applying pruning. |
| **`cell_enforce.py`** | `enzymes/cell_enforce.py` | Auto-generates mechanical pre-commit checks or runtime assertions for cells reaching enforcement tiers. |
| **`cell_quorum.py`** | `enzymes/cell_quorum.py` | Quorum sensing detector identifying when ≥3 cells trigger simultaneously on the same diff, escalating review modes. |
| **`bayesian_score.py`** | `enzymes/bayesian_score.py` | Centralized Laplace-smoothed Bayesian scoring utility providing a single source of truth for posterior calculations. |
| **`hgt_ribosome.py`** | `enzymes/hgt_ribosome.py` | Horizontal Gene Transfer ribosome engine translating domain-specific cells into universal engineering principles. |

### 3. Runtime Verification, Integrity & Test-Time Compute (10 scripts)

| Script | Location | Purpose |
|:-------|:---------|:--------|
| **`ttc_oracle.py`** | `enzymes/ttc_oracle.py` | Test-Time Compute Oracle evaluating proposed diffs against hidden foundational rules (.oracles) using an LLM-as-a-judge before execution. |
| **`ttc_verifier.py`** | `enzymes/ttc_verifier.py` | Advisory TTC verifier reviewing proposed file changes against active JIT playbooks and TTC oracles, returning unified diffs. |
| **`cell_adversarial.py`** | `enzymes/cell_adversarial.py` | Adversarial cell testing tool probing governance cells for bypass vulnerabilities (renaming, indirection, test alteration). |
| **`resilience_engine.py`** | `enzymes/resilience_engine.py` | Endocrine resilience engine monitoring consecutive agent execution failures (Stress) and intervening before runaway loops. |
| **`soma_coherence.py`** | `enzymes/soma_coherence.py` | Signal Coherence Layer (Integrity Engine) cross-validating disparate Soma signals and detecting contradictions. |
| **`soma_interoception.py`** | `enzymes/soma_interoception.py` | Internal state awareness (proprioception) engine reading four internal signals before major actions. |
| **`evidence_collector.py`** | `enzymes/evidence_collector.py` | Scans session transcripts to correlate rule compliance patterns directly with session outcomes. |
| **`outcome_engine.py`** | `enzymes/outcome_engine.py` | Verifiable execution feedback engine capturing real outcomes (test exit codes, build status, git reverts). |
| **`immune_replay.py`** | `enzymes/immune_replay.py` | Governance replay tool retrospectively testing current cells against historical commits to verify catch rates. |
| **`sweep_session.py`** | `enzymes/sweep_session.py` | Lightweight waste signal scanner and session transcript scorer for governance sweeps. |

### 4. Telemetry, Reporting & Analysis (17 scripts)

| Script | Location | Purpose |
|:-------|:---------|:--------|
| **`token_census.py`** | `enzymes/token_census.py` | Validates token footprints of active rules and skills via Gemini SDK counting or calibrated fallbacks. |
| **`metrics_snapshot.sh`** | `enzymes/metrics_snapshot.sh` | Saves automated governance performance baselines and ROI deltas into `METRICS_REPO`. |
| **`export_logs.sh`** | `enzymes/export_logs.sh` | Prepares conversation logs and transcripts for post-mortem analysis and archiving. |
| **`immune_sweep.sh`** | `enzymes/immune_sweep.sh` | Performs batch scans across past session transcripts to extract recurring waste patterns. |
| **`log_finding.sh`** | `enzymes/log_finding.sh` | Canonical entrypoint for logging governance findings and routing critical findings to `mulch_queue.jsonl`. |
| **`team_sync.sh`** | `enzymes/team_sync.sh` | Syncs local promoted cells and metrics snapshots to a shared team repository for multi-developer convergence. |
| **`immune_entropy.py`** | `enzymes/immune_entropy.py` | Computes governance entropy rate using Shannon entropy to detect system stagnation or monoculture. |
| **`immune_grade.py`** | `enzymes/immune_grade.py` | Governance report card generator producing single-grade compliance summaries. |
| **`immune_trends.py`** | `enzymes/immune_trends.py` | Cross-session trend dashboard aggregating metrics over rolling windows with Shannon diversity indices. |
| **`fitness_landscape.py`** | `enzymes/fitness_landscape.py` | ASCII visualization of governance effectiveness and cell fitness scores. |
| **`fitness_updater.py`** | `enzymes/fitness_updater.py` | Extracts session evidence from JSONL transcripts and appends fitness update records. |
| **`cell_coverage.py`** | `enzymes/cell_coverage.py` | Generates visual coverage maps showing which workspace files are covered by active cells and highlighting blind spots. |
| **`cell_deps.py`** | `enzymes/cell_deps.py` | Computes and visualizes cell co-trigger dependencies and interaction networks. |
| **`cell_escaped_defects.py`** | `enzymes/cell_escaped_defects.py` | Correlates test regressions, crashes, and build failures with files to pinpoint unmonitored blind spots. |
| **`oracle_checkpoint.py`** | `enzymes/oracle_checkpoint.py` | Mid-session fitness feedback tool analyzing cell health, expiry status, and evidence trends. |
| **`insight_capture.py`** | `enzymes/insight_capture.py` | Captures human developer insights into `.soma/human_insights.jsonl` and correlates them with existing cells. |
| **`insight_correlator.py`** | `enzymes/insight_correlator.py` | Clusters captured human insights over rolling windows to automatically propose new governance cells. |

### 5. Shared Infrastructure & Workspace Resolution (5 scripts)

| Script | Location | Purpose |
|:-------|:---------|:--------|
| **`common.sh`** | `enzymes/common.sh` | Shared bash library providing standardized output, error handling, config loading, and path resolutions. |
| **`soma_resolve.py`** | `enzymes/soma_resolve.py` | Centralized workspace resolution library (respecting `SOMA_ROOT`, CWD, and parent repository roots). |
| **`soma_sleep.py`** | `enzymes/soma_sleep.py` | Memory consolidation engine executed at session close for offline evidence distillation and cell decay. |
| **`escalation_sentinel.py`** | `enzymes/escalation_sentinel.py` | Python engine managing review mode configuration and steering rules for protocol escalation. |
| **`inference_provider.py`** | `enzymes/inference_provider.py` | Inference provider abstraction layer with secure credential lookup and key management for AI-assisted enzymes. |

---

## MCP Server

* **`soma-mcp`** (`soma_mcp.server`): The Model Context Protocol server exposing `soma_create_cell`, `soma_scan`, `soma_grade`, `soma_coverage`, and `soma_fitness` to any MCP-compatible agent (Claude Code, Cursor, Antigravity).

---

## Privacy Invariant

All scripts in this catalog are strictly constrained by the **Soma Privacy Invariant**: No script may output, log, or transmit raw file paths, usernames, hostnames, directory structures, code diffs, or patches outside the local environment. Only aggregate counts, booleans, and sanitized strings are permitted across telemetry and external synchronization.
