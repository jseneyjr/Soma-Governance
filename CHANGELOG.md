# Changelog

All notable changes to Prism AI Steering are documented here.
This project uses [Semantic Versioning](https://semver.org/).

## [0.15.0] — 2026-09-27

### Added
- Team topology: `TEAM_REPO` and `ORG_REPO` configuration for multi-developer governance convergence
- `team_sync.sh` for push/pull/status of shared cells and metrics
- Clean uninstaller (`uninstall.sh`) with backup/restore and manifest tracking
- Install manifest (`~/.prism-ai-steering/manifest.json`) for safe uninstall
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
- Cytogenesis infrastructure (`.gemini/cells/`)
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
- Renamed project from internal naming to Prism AI Steering

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
