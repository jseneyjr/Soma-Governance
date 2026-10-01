# Changelog

All notable changes to Soma are documented here.
This project uses [Semantic Versioning](https://semver.org/).

## [0.80.0] — 2026-10-01 — "Consensus"

### Added
- **Quorum sensing** (Phase 4.1): `evaluate_quorum()` detects when ≥N cells trigger simultaneously on the same changed files, escalates to the highest `minimum_mode`, and logs events to JSONL. Extracted from CLI `main()` for testability.
- **Gate enforcement DSL** (Phase 4.2): `soma_sdk/invariants.py` with `check_import_banned()` (AST-based), `check_file_must_exist()`, `check_invariants()` aggregate, and `evaluate_enforcement()` three-tier ladder.
- **Enforcement ladder**: `advisory` (warn, exit 0) → `mechanical` (block, exit 1) → `gate` (block, exit 1). Unknown tiers default to advisory.
- **TDD test suite**: 3 new test files — `test_quorum.py` (11), `test_gate_invariant_dsl.py` (9), `test_enforcement_ladder.py` (7). Total: 1,492 passed, 7 skipped.

### Fixed
- **Documentation cleanup**: 9 doc files updated — stale version refs, broken post-restructure links, removed claim terminology, outdated phase statuses.
- **Stale release branches**: Deleted 10 local release branches (`release/v0.60` through `release/v0.75`).

### Claims Unlocked
- `claim_quorum_sensing` — Multi-rule consensus for high-confidence decisions
- `claim_gate_enforcement` — Invariant DSL-based gate enforcement in CI

---

## [0.75.0] — 2026-10-01 — "Credit Where Due"

### Added
- **Credit assignment** (Phase 3.1): `prob_round()` probabilistic rounding, `compute_credit_weights()` per-file scope narrowing with credit conservation. Signal provenance tracked in JSONL via `credit_weight` and `signal_method` fields.
- **Mutation operators** (Phase 3.2): Comparison swap (`<`↔`>`, `<=`↔`>=`, `==`↔`!=`), boolean swap (`and`↔`or`), statement deletion (stmt→pass), return value mutation (`return X`→`return None`).
- **TDD test suite**: 8 new behavioral test files — `test_credit_assignment.py` (14), `test_outcome_engine.py` (18), `test_jit_engine_behavioral.py` (22), `test_error_handling.py` (13), `test_mcp_tools_contract.py` (12), `test_tournament_integration.py` (8), `test_crossover_structured.py` (12), `test_mutation_tester_upgraded.py` (10).

### Fixed
- **Crossover target_paths** (Phase 3.6): `cell_crossover.py` now merges `target_paths` as deduplicated union of both parents. Previously omitted entirely, making child cells unable to match any files.
- **Crossover tags**: Tags now merged as union instead of reset to empty list.

### Changed
- `compute_fitness_signals()` accepts optional `changed_files` kwarg for credit weighting.
- `update_cell_fitness()` uses `prob_round(credit_weight)` for tp/fp counter updates.
- `append_fitness_log()` includes `credit_weight` and `signal_method` provenance.
- Claim registry: `claim_credit_assignment`, `claim_structured_crossover`, `claim_tournament_selection` unlocked.

### Metrics
- Test suite: **1465 passed**, 7 skipped, 0 failed (up from 1359 in v0.74)

---

## [0.71.0] — 2026-10-01 — "Branch Sync"

### Fixed
- **Gitflow step 7**: Release checklist now merges **main** back to develop (not the release branch). Previous workflow skipped main's PR merge commit, causing main and develop to diverge over 5 releases.

---

## [0.74.0] — 2026-10-01 — "Foundation"

### Added
- `soma_sdk/errors.py`: Complete error hierarchy (SomaError → CellParseError, CellNotFoundError, CellPathTraversalError, FitnessError)
- `soma_sdk/scoring.py`: Wilson-bounded fitness scoring (bayesian_posterior, laplace_score, _wilson_interval)
- `soma_sdk/cells.py`: Canonical cell parser (parse_cell_file, write_cell_frontmatter, load_cell, _sanitize_cell_id)
- `tests/test_bayesian_correctness.py`: 17 mathematical ground truth tests
- `tests/test_sdk_behavioral.py`: 21 SDK public API tests
- `tests/test_escaped_defects.py`: 12 antifragile behavior tests
- `tests/test_cell_deps_behavioral.py`: 5 co-trigger detection tests
- `tests/test_integration_lifecycle.py`: 8 end-to-end lifecycle tests
- `tests/test_threshold_recalibration.py`: 12 boundary value tests

### Changed
- Migrated 27 enzyme/CLI files from inline YAML parsing to canonical `parse_cell_file()`
- `CellFitness.bayesian()` upgraded from Wald approximation to Wilson score interval
- `Cell.is_extinct` / `Cell.is_promotable` now use `laplace_score()` import
- `enzymes/bayesian_score.py` converted to thin wrapper re-exporting from `soma_sdk.scoring`
- `enzymes/cell_deps.py` added `--workspace` argument for testability

### Metrics
- Suite: 1359 passed, 5 skipped, 0 failed
- Claims: 8 unlocked, 5 locked, 7 removed (20/20 verified)
- Net code change: +1606/-353 lines across 41 files

---

## [0.73.0] — 2026-10-01 — "Stop the Bleeding"

### Added
- `docs/CLAIM_REGISTRY.json`: Machine-readable claim tracking (locked/unlocked/removed)
- `enzymes/verify_readme_claims.py`: CI gate verifying README claims against tests
- `tests/test_static_invariants.py::test_version_is_single_sourced`: Version sync invariant
- `docs/ROADMAP.md`: Future features moved from README
- `docs/RELEASE_WORKFLOW.md`: Codified gitflow release procedure

### Changed
- README stripped to earned claims only — removed 7 unverified claims
- Fixed `exit 1` bug in pre-commit hook generation (cell_enforce.py)
- Version synced across pyproject.toml and VERSION file

### Removed
- Unearned README claims: evolutionary computation, gate enforcement, < 1.0% waste rate, deterministic verification, inflated test count

---

## [0.70.0] — 2026-10-01 — "Genesis"

### Added
- **`soma genesis` command**: Scans codebase architecture with 8 language-agnostic detectors and generates governance cell candidates.
  - Detectors: module boundaries, config stores, shared state, API surfaces, data pipelines, state machines, test boundaries, dependency walls
  - All generated cells start as vacuoles with `proposed_type` frontmatter
  - Generates `docs/organelles.md` architecture map
  - Flags: `--dry-run`, `--json`, `--force`, `--yes`

### Security
- Path traversal fix: import regex rejects relative imports; `is_relative_to()` containment check
- Memory exhaustion fix: streaming `read(limit)` replaces `read_text()[:limit]`
- Symlink guard: `is_symlink()` check before all file writes

### Fixed
- Dry-run no longer creates `.soma/cells/vacuoles/` directory
- `docs/organelles.md` respects `--dry-run`, `--force`, and symlink guards
- `input()` wrapped in `try/except` for headless environments
- `rglob` replaced with filtered `_iter_source_files` (no `.git`/`.venv` traversal)
- Frontmatter/markdown sanitization prevents injection via crafted identifiers
- 80% I/O reduction via single-pass source cache across 5 detectors

---

## [0.62.2] — 2026-10-01 — "Documentation Sweep"

### Fixed
- **README.md**: Version badge 0.60.0 → 0.62.2, test badge 1162 → 1228, script count 58 → 57. Added `soma sync` to CLI table. Added PyPI install to Quick Start. Added Python 3.9+ label.
- **QUICKSTART.md**: Added all CLI commands (sync, checkpoint, oracle, promote, demote, doctor, verify). Fixed repo URL. Updated PyPI status from "coming soon" to available. Added PEP 668 hint. Added Kiro platform.
- **SCRIPTS.md**: Full recount and rewrite — 39 → 57 scripts cataloged.
- **CONTRIBUTING.md**: Added Python 3.9 compat requirement, CI matrix info, test command, `from __future__ import annotations` requirement.
- **pyproject.toml**: Added Python 3.9/3.10/3.11/3.12 classifiers.

---

## [0.62.1] — 2026-10-01 — Patch

### Fixed
- **`make install`**: Handle PEP 668 externally-managed Python environments (`--user --break-system-packages` fallback chain).
- **`make install`**: Print PATH hint when `~/.local/bin` is not on PATH.
- **`install.sh`**: Fix skill install crash when a previously-installed file/symlink is being replaced by a directory (`cp: cannot overwrite non-directory`).

---

## [0.62.0] — 2026-10-01 — "Evidence Pipeline"

### Added
- **`soma sync` command**: Reconciles `.soma/evidence/fitness.jsonl` and `outcomes.jsonl` with cell frontmatter. Supports `--dry-run` and `--json` flags.

### Fixed
- **Fitness pipeline disconnect**: `fitness_updater.py` wrote trigger events to JSONL but never updated cell frontmatter, causing `immune_grade.py` and `cell_fitness.py` to report zero fitness despite evidence existing.
- **`soma checkpoint`** now auto-syncs evidence → frontmatter before running quality checks, so the report card is always fresh.
- **`fitness_updater.py`** now auto-syncs frontmatter after writing JSONL, closing the pipeline gap.

### Changed
- Bootstrapped fitness evidence from two Supercell session transcripts (170+ trigger events, 42 cells scored).

---

## [0.61.0] — 2026-10-01 — "Python 3.9 Compatibility"

### Fixed
- **Python 3.9 runtime crash**: 6 files in `immune_system/verification/` used PEP 604 union syntax (`X | None`) in function signatures without `from __future__ import annotations`, causing `TypeError: unsupported operand type(s) for |` on Python 3.9. Added the future import to all affected files.

### Changed
- **CI matrix**: Added Python 3.9 to test matrix (Ubuntu, macOS, Windows).
- **CI publish**: Auto-publish to PyPI on GitHub release creation via `PYPI_API_TOKEN` secret.

---

## [0.60.0] — 2026-09-30 — "Two-Layer Verification & Cell Lifecycle"

### Added
- **Two-Layer Verification System** (`immune_system/verification/`):
  - **Layer 1 (Deterministic AST Tools)**: Objective, ungameable evidence collection via `persistence_checker`, `call_graph`, `mutation_tester`, `branch_coverage`, and `import_guard`. Orchestrated via `runner.py` producing boolean `ToolEvidence`.
  - **Layer 2 (Adversarial Information-Partitioned Agents)**: Multi-agent verification leveraging information asymmetry between Spec Agent (sees task specification) and Code Agent (sees implementation/tests).
  - **Deterministic Arbiter**: Set-algebra adjudication over a fixed 14-category risk taxonomy, issuing `SHIP`, `BLOCK`, or `REVISE` verdicts with zero LLM in the loop.
  - **Transcript Verifier**: Post-hoc validation of self-reported agent claims against JSONL session logs.
- **Unified CLI Suite** (`soma`): 9 subcommands — `init`, `status`, `report`, `doctor`, `verify`, `checkpoint`, `oracle`, `promote`, `demote`.
  - `soma verify`: Full two-layer verification with `--layer1-only` support.
  - `soma checkpoint`: Fast deterministic quality gate with `--pre-commit` hook integration.
  - `soma oracle`: Cell health classification (healthy, noisy, expired, unobserved).
  - `soma promote` / `soma demote`: Automated lifecycle evaluation with `--dry-run` and `--json`.
  - `soma init`: Enhanced with `--rules {minimal|standard|full}`, MCP config, and pre-commit hook.
- **Cell Lifecycle Engine** (`immune_system/verification/lifecycle.py`):
  - Deterministic state machine: Vacuole → Wall → Genome (and demotions).
  - Grounded in JSONL evidence ledgers, not YAML frontmatter.
  - Promotion: triggers ≥ 20, tp_rate > 0.85, age > 30 days.
  - Demotion: fp_rate > 0.5 or dormancy ≥ 90 days.
- **MCP Tools**: Added `soma_verify_changes` and `soma_checkpoint` for zero-API-key in-agent verification.
- **Supercell Review Intensity**: New highest review tier (above Tempest) — adversarial Prosecutor/Defender pairs per prong, iterative fix-revalidate with no deferrals until clean ship.
- **Quality Gate Checks**: Assertion density, bare `pass` detection, import verification, test sanity.
- **Doc Consistency Tests**: 6 tests verifying README ↔ SKILL.md intensity level consistency.
- **Test Suite**: 1184 tests with shared fixtures (`tests/helpers_cell.py`).
- **Governance Cells**: 44 total — 20 walls, 2 plasmodesmata, 3 membranes, 3 chloroplasts, 16 vacuoles.
  - NEW: `trap-stdout-protocol-corruption` (wall) — hooks emitting to stdout after JSON.
  - NEW: `trap-tautological-test` (wall) — tests that verify nothing.
  - NEW: `contract-sdk-feature-parity` (plasmodesmata) — Python/JS SDK method parity.
- **SDK Parity**: Added `entropy()` and `adversarial()` to Python SDK (matching JS SDK).

### Changed
- Package discovery updated to include `immune_system*`.
- Pre-commit hook auto-installed by `soma init`.
- Architecture diagram widened for Supercell intensity level.
- **SDK `is_extinct`/`is_promotable`**: Now use Bayesian scoring aligned with `cell_promote.py` standards (score > 0.85, triggers ≥ 20) instead of legacy `raw_score`.
- **DRY**: `outcome_engine.py` imports canonical `resolve_workspace()` from `soma_resolve.py`. Intentional duplication in `soma_mcp/` documented (zero-dep wall).
- **Type Annotations**: Added to all public APIs in `governance.py`, `cells.py`, `jit_engine.py`, `bayesian_score.py`.
- **Test Fixtures**: Deduplicated `soma_workspace`, `_write_cell`, `_make_cell` into shared `helpers_cell.py`.
- **Hardcoded Paths**: `safety_gate.sh` and `immune_init.sh` now use `${SOMA_LOGS_DIR}` / `${SOMA_CONF}` env vars with fallbacks.
- **Makefile validate**: Now covers `soma_cli/` and `immune_system/` in addition to `enzymes/`, `soma_mcp/`, `soma_sdk/`.
- **Docs**: Fixed ABSTRACT contribution count (3→4), step count (12,000→11,900), removed duplicate PHYLOGENY section, added Phase 16/18/19/20/21 stubs.

### Fixed
- **Evidence Pipeline**: 4 critical bugs fixed (schema mismatch, dead detectors, missing FPSR extraction).
- 2 new evidence detectors: `test-before-implementation`, `no-hardcoded-paths`.
- **Security (Supercell S1)**: Code injection via `.format()` in `branch_coverage.py` — paths now escaped with `repr()`.
- **Security (Supercell S2)**: Path traversal via `--files` — containment check added to `verify.py`.
- **Correctness (Supercell C1)**: Outcomes path/schema desync between MCP and lifecycle engine.
- **Correctness (Supercell C2)**: JSONL crash on non-dict lines in lifecycle evidence loading.
- **Correctness (Supercell C3)**: Lifecycle threshold bugs (boundary values, min sample size, dormancy).
- **Bug**: 5 pre-existing `test_status.py` failures from real filesystem leak through platform auto-detection.
- **Robustness (Phase 2)**: 9 fixes across verification tools:
  - `branch_coverage.py`: Parse `missing_branches`, add subprocess timeout (120s), UTF-8 encoding.
  - `transcript_verifier.py`: FileNotFoundError guard, tool_calls-based write detection (no more content-string false positives), collection error sentinel `(-1,-1)`, multi-run false positive fix.
  - `immune_init.sh`: JSON protocol corruption — 4 echo statements redirected to stderr.
  - `escalation_sentinel.sh`: Frontmatter `target_paths` parsing replaces fragile hypothesis regex.
- **Layer 2 Fail-Open (Phase 3)**: Empty spec agent predictions now produce `Verdict.BLOCK` instead of silently passing through to `SHIP`.

---

## [0.60.0-rc] — 2026-09-30 — "Wire Verification & Cell Lifecycle RC"

### Added
- **Gitflow**: Standardized branch lifecycle with session pattern rules.
- **Content Coherence Tests**: Automated doc ↔ code consistency validation.
- **MCP Self-Install**: `soma init` auto-configures MCP server in agent config.
- `soma init --rules {minimal|standard|full}`: Tiered rule installation.
- **Wire Verification System (Phase 2)**: End-to-end evidence pipeline validation.
- **Pre-Commit Hook**: Deterministic quality gate via `soma checkpoint --pre-commit`.
- **Cell Lifecycle Engine**: Oracle, promote, and demote commands with deterministic state machine.
- **Supercell Review Process**: Highest review tier — adversarial Prosecutor/Defender pairs per prong.
- **Checkpoint Extraction**: Deterministic quality gate checks (assertion density, bare `pass`, imports).
- **Evidence Pipeline Fix**: 4 critical bugs (schema mismatch, dead detectors, missing FPSR extraction).

### Changed
- 5 review cycles completed during RC hardening.

---

## [0.52.0] — 2026-09-30 — "Gitflow & Hardening"

### Added
- **Gitflow**: Standardized branch lifecycle in `docs/GITFLOW.md`.
- **Gitflow Review Gate**: Rule enforcing branch naming and PR-based landing.

### Fixed
- All 15 findings from v0.52 production audit.
- 4 must-fix findings from audit round 2.
- Hardcoded absolute paths in documentation.

---

## [0.51.0] — 2026-09-30 — "Soma CLI & Distribution"

### Added
- **Soma CLI** (`soma_cli/`): `soma init`, `soma status`, `soma report`.
- Starter pack manifests and templates.
- CLI entrypoints in `pyproject.toml`.

### Fixed
- 10 audit findings across argument validation, path resolution, error reporting.

---

## [0.50.0] — 2026-09-29 — "Incentive-Compatible Governance"

> Tagged release — Version jump from v0.22.0 reflects Phases 23–50: TTC Oracles, JIT context, interoception, and the evidence pipeline.

### Added
- **Evidence Pipeline**: `evidence_collector.py`, `fitness_updater.py`, `cell_expiry.py`, `oracle_checkpoint.py`, `post_session_hook.sh`.
- **Mechanism Design Framework** (`docs/MECHANISM_DESIGN.md`).
- **Fitness Updater**: Automated fitness scoring from evidence ledgers.
- **Cell Expiry**: Time- and session-based cell lifecycle enforcement.
- **Oracle Checkpoint**: Cell health classification with evidence grounding.
- **Trap Cells**: `trap-fix-one-not-all`, `trap-unverified-delegation`, `trap-local-green-ci-red`.
- README trustworthiness rewrite.

### Changed
- Fitness ledger decoupled from frontmatter → append-only JSONL.
- `pyyaml` accepted as mandatory dependency.
- Idle overhead stabilized at ~3,800 tokens/turn (down 8.6%).
- 6 audit rounds completed.

### Fixed
- Tautological assertions and brittle source-code grepping remediated (515+ tests).
- Critical fitness inflation bug.
- CI execution hang from hook test sourcing.

---

## [0.31.0] — 2026-09-29 — "Human Insight Pipeline"

### Added
- **Human Insight Pipeline**: Structured pathway for human-observed defects to influence cell fitness.
- **TDD Protocol** (`genome/.oracles/tdd-protocol.md`): Test-driven development with sequential phase gates.
- **Mechanism Design Framework**: Incentive-compatible governance architecture documentation.
- **Evidence Collector**: Automated correlation of rule compliance with session outcomes.

---

## [0.30.0] — 2026-09-29 — "Two-Layer Verification Foundation"

### Added
- **Two-Layer Verification Framework**: Deterministic AST tools (Layer 1) + adversarial information-partitioned agents (Layer 2).
- **Import Guard** (`import_guard`): Layer 1 tool detecting unguarded third-party imports that crash CI.
- **Keyring Secret Storage**: Secure credential management for inference providers.

---

## [0.25.0] — 2026-09-28 — "TTC & Biological Docs"

### Added
- **TTC/Tempest MCP Tooling**: Test-Time Compute oracle integration with MCP server.
- **Last Gasp Auto-Escalator**: Pre-failure evaluation mechanism that auto-escalates before token budget is consumed.
- **Biological Documentation Suite**: PHYLOGENY.md, MECHANISM_DESIGN.md, and naming unification docs.

### Fixed
- 15 bug fixes across the governance pipeline.

---

## [0.22.0] — 2026-09-28 — "Soma Rebirth"

### Breaking Changes
- **Project renamed**: Prism AI Steering → **Soma**
- **Repository**: `prism-ai-steering` → `soma`
- **SDK packages**: `prism-steering` → `soma-steering` (Python + npm)
- **Config**: `steering.conf` → `soma.conf`
- **Directory**: `.prism/` → `.soma/` (auto-migrated on install)

### Added — Biological Naming Unification
- `rules/` → `genome/` — Rules are now **Genes** in the organism's **Genome**
- `skills/` → `organs/` — Skills are now **Organs** (complex multi-cell structures)
- `scripts/` → `enzymes/` — Scripts are now **Enzymes** (catalytic reactions)
- `governance/` → `immune_system/` — Governance is the **Immune System**
- `EVOLUTION.md` → `PHYLOGENY.md` — Project history as evolutionary tree
- Half-Life → Telomere Shortening — Biological aging mechanism
- `governance_*.py` → `immune_*.py` — All governance scripts renamed
- Auto-migration in `install.sh`: detects `.prism/` and renames to `.soma/`

### Added — Host-Agent Delegation (Provider Abstraction)
- `enzymes/inference_provider.py` — Multi-provider inference abstraction
- Supports Gemini, Anthropic, OpenAI, and prompt-only mode
- `--provider` flag on `cell_create_nl.py`: `auto|gemini|anthropic|openai|prompt-only`
- `SOMA_INFERENCE_PROVIDER` config key in `soma.conf`
- No API key required when running inside an AI agent via MCP

### Added — MCP Stdio Server
- `soma_mcp/` — Model Context Protocol server for host-agent delegation
- Tools: `soma_create_cell`, `soma_scan`, `soma_grade`, `soma_coverage`, `soma_fitness`, `soma_list_cells`
- `soma_create_cell` delegates LLM reasoning to the host agent — zero API key needed
- Runnable as `python -m soma_mcp` or configured in any agent's MCP settings
- Works with Gemini Antigravity, Claude Code, Cursor, and any MCP-compatible agent

## [0.21.1] — 2026-09-28

### Added
- `cell_enforce.py`: Auto-generates enforcement artifacts for promoted cells
- Mechanical cells generate pre-commit hook checks in `.soma/enforcement/`
- Gate cells generate runtime assertion classes in `.soma/enforcement/`
- `enforcement_artifact` field links cells to their generated artifacts
- Coverage map now shows enforcement tier per directory
- Pre-commit hook runs mechanical checks from `.soma/enforcement/`
- Auto-trigger enforcement generation on tier promotion
- Script count: 38 → 39

## [0.21.0] — 2026-09-28

### Added
- Tiered enforcement system: cells declare `advisory`, `mechanical`, or `gate` enforcement level
- `cell_escaped_defects.py`: Independent defect tracking from CI/tests/crashes (breaks self-evaluation loop)
- Enhanced fitness formula: `bayesian_mean × (1 - escaped_defect_rate) × tier_weight`
- Enforcement tier promotion/demotion lifecycle in `cell_promote.py --tier-check`
- Tier distribution in governance report card
- Backfilled all existing cells with `enforcement: advisory`
- Script count: 37 → 38

## [0.20.0] — 2026-09-27

### Added
- Natural language cell creation (`cell_create_nl.py`) via Gemini API with multi-source API key resolution
- Python SDK (`soma_sdk/`): `pip install soma-steering` for programmatic governance access
- Counterfactual replay (`--counterfactual --cell <name>`): ROI estimation against historical commits
- Adversarial cell testing (`cell_adversarial.py`): probe cells for bypass vulnerabilities
- Governance entropy rate (`immune_entropy.py`): fossilization detection via Shannon entropy
- `pyproject.toml` for PyPI packaging
- Script count: 34 → 37

## [0.19.1] — 2026-09-27

### Fixed
- `cell_create.sh`: Added `--minimum-mode` and `--id` flags
- `cell_coverage.py`: Excludes .soma/, vendor/, .git/ from coverage counts
- `cell_fitness.py`: Fixed UnboundLocalError in --bayesian mode

### Added
- `install/hooks/pre-commit`: Git pre-commit hook for automatic cell scanning
- `cell_deps.py`: Cell dependency graph with Mermaid output
- `immune_grade.py`: Single-grade governance report card
- Script count: 32 → 34

## [0.19.0] — 2026-09-27

### Added
- Wall extinction immunity (walls immune to apoptosis, get APOPTOSIS_WARNING instead)
- Specificity penalty (anti-Goodhart: penalize cells triggering >80% of sessions)
- Bayesian cell fitness (`--bayesian`): Beta-Binomial posterior with Jeffrey's prior
- Antifragile fitness bonus (+5% per survived Tempest/Maelstrom review)
- Signal-to-noise ratio (SNR dB) per cell in fitness output
- `cell_quorum.py`: Detect systemic issues when ≥3 cells trigger simultaneously
- `cell_coverage.py`: Visualize governance blind spots across codebase
- `immune_replay.py`: Retrospective "would cells have caught this?" analysis
- `immune_trends.py`: Cross-session trend dashboard with Shannon diversity index
- Dormant spore archive (pruned cells saved to `.spores.jsonl`, reactivated on match)
- `cell_genesis_stochastic.py`: Random template injection every N sessions
- Mulch→Cell pipeline: Tempest findings auto-create vacuole cells
- Script count: 27 → 32

## [0.18.1] — 2026-09-27

### Fixed
- Wire `escalation_sentinel.sh` into `immune_init.sh` (was orphaned)
- Escalation sentinel now scans walls AND membranes for `minimum_mode`
- Thorns terminology disambiguation in README

### Added
- `cell_scan.py`: Automated diff→cell triggering via git diff and target_paths
- `target_paths` field in cell YAML schema
- `DEFAULT_REVIEW_MODE` and `MINIMUM_REVIEW_MODE` in soma.conf
- Session fitness dashboard in session_close.sh

## [0.18.0] — 2026-09-27

### Added
- Centralized workspace resolution (`soma_resolve.py`) — CWD-first, vendor-safe
- Automated evolutionary loop in `session_close.sh`
- Apoptotic fast-kill in `cell_fitness.py` (FP > 2×TP)
- Homeostatic governance intensity in `immune_init.sh`

### Changed
- All scripts use `soma_resolve.py` instead of inline resolution
- Script count: 25 → 26

## [0.17.1] — 2026-09-27

### Added
- Cell lineage tracking (`lineage` block in YAML) — phylogenetic tree support
- Per-type telomere shortening configuration (`CELL_TELOMERE_WALL`, etc.)
- Effector→Memory auto-transition via `decay_to` field
- Benchmark protocol (`docs/BENCHMARK.md`)

## [0.17.0] — 2026-09-27

### Added
- GA crossover operator (`cell_crossover.py`) — merges complementary cell hypotheses
- Tournament selection (`cell_tournament.py`) — diversity-preserving cell selection
- Cell metamorphosis (`cell_metamorphose.py`) — vacuole → wall → rule maturity paths
- Horizontal gene transfer (`cell_transfer.sh`) — cross-project cell sharing with fitness reset
- Fitness landscape visualization (`fitness_landscape.py`) — ASCII governance dashboard
- Confidence telomere shortening decay in `cell_fitness.py` — stale cells fade naturally
- Effector/memory cell flags in `cell_create.sh` — incident response patterns
- Incident response templates (`templates/incident-response/`)
- `CELL_TELOMERE_DAYS` configuration in `soma.conf.example`

### Changed
- Script count: 20 → 25
- `cell_signal.sh` now records `last_trigger_date` for telomere shortening calculation

## [0.16.0] — 2026-09-27

### Added
- External fitness signal API (`cell_signal.sh`) — any system (CI/CD, monitoring, game results) can feed outcomes to cells
- Programmatic cell creation (`cell_create.sh`) — create cells from automated systems
- Cell demotion (`cell_demote.py`) — reverse promotion when cells cause issues in new contexts
- Cell templates by domain (`templates/`) — RL training, web backend, infrastructure, data pipeline
- 14 domain-specific cell templates with self-pruning (`expiry_sessions: 5`)
- Template auto-detection in Genesis Stage 5 based on project dependencies

### Changed
- Script count: 18 → 20

## [0.15.1] — 2026-09-27

### Added
- Liveness sentinel script (`liveness_sentinel.sh`) for subagent health monitoring
- Enhanced Genesis Lichen phase with magic number / hardcoded coordinate detection
- Enhanced Plasmodesmata detection with explicit patterns (pip install -e, shared DBs, protobuf imports)

## [0.15.0] — 2026-09-27

### Added
- Team topology: `TEAM_REPO` and `ORG_REPO` configuration for multi-developer governance convergence
- `team_sync.sh` for push/pull/status of shared cells and metrics
- Clean uninstaller (`uninstall.sh`) with backup/restore and manifest tracking
- Install manifest (`~/.soma/manifest.json`) for safe uninstall
- Backup-on-install: archives existing config before overwriting
- Peer-reviewed research abstract (`ABSTRACT.md`) with 5-reviewer record (`REVIEWS.md`)
- GitHub Actions CI workflow
- `CONTRIBUTING.md` with CLA language
- `VERSION` file and semantic versioning

### Changed
- Deprecated legacy per-platform installers in favor of unified `install.sh`
- Script count: 15 → 17

## [0.14.0] — 2026-09-27

### Added
- Cross-repo fitness aggregation (`cell_fitness.py --cross-repo`)
- Adaptive cell refinement (`cell_adapt.py`)
- Speciation/promotion path (`cell_promote.py`) — local cells graduate to global rules
- Plasmodesmata cell type for cross-repo connections

## [0.13.0] — 2026-09-27

### Added
- Cytogenesis infrastructure (`.soma/cells/`)
- Cell fitness scoring (`cell_fitness.py`)
- Cell selection lifecycle (`cell_selection.sh`)
- Four cell types: Vacuole, Chloroplast, Cell Wall, Membrane
- Genesis Stage 5: automated cell generation

## [0.12.0] — 2026-09-27

### Added
- Calibrated tokenizer (1.35 ratio, validated against Gemini API)
- Apache 2.0 license, NOTICE file, privacy statement
- Privacy-safe metrics via `METRICS_REPO` configuration
- Rule compression optimization

### Changed
- Token census now uses empirical calibration instead of estimates

## [0.11.0] — 2026-09-27

### Added
- Cross-platform validation (bash + PowerShell)
- Genesis onboarding skill (5-stage codebase reconnaissance)
- 66-session expanded dataset analysis
- Unified installer (`install.sh`) replacing per-platform scripts

### Changed
- Renamed project from internal naming to Soma

## [0.10.0] — 2026-09-26

### Added
- Tempest cross-conversation analysis
- Subagent nesting (E11)
- Adaptive review orchestrator
- Escalation sentinel script

## [0.9.0] — 2026-09-26

### Added
- Maelstrom academic integration (Refutation Gate, Boundary Verification, Orthogonal Personas)
- FPSR metric (First-Pass Success Rate)

## [0.1.0–0.8.0] — 2026-09-26

### Added
- Initial governance rules (Providence, cost optimization, subagent delegation)
- Review protocol (Breeze through Tempest, Spores through Mulch)
- Testing and git workflow rules
- Lifecycle hooks (governance_init, safety_gate, session_close)
- Experiment framework (E1–E22)
- Metrics infrastructure (token census, metrics snapshot)
