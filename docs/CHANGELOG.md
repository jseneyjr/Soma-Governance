# Changelog

All notable changes to Soma are documented here.
This project uses [Semantic Versioning](https://semver.org/).

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
