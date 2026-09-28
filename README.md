# 🔮 Prism AI Steering

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue?style=flat-square)](LICENSE)
[![Rules](https://img.shields.io/badge/Rules-11-green?style=flat-square)](#rules)
[![Skills](https://img.shields.io/badge/Skills-15-purple?style=flat-square)](#skills)
[![Scripts](https://img.shields.io/badge/Scripts-25-red?style=flat-square)](#scripts)
[![Phases](https://img.shields.io/badge/Phases-15-blue?style=flat-square)](docs/EVOLUTION.md)
[![Cells](https://img.shields.io/badge/Cells-4-orange?style=flat-square)](#adaptive-governance-cells)

Prism AI Steering is an adaptive governance framework that generates, measures, and evolves its own rules based on observed agent behavior. Built on top of continuous feedback loops and biological natural selection principles, it ensures agents remain grounded, efficient, and safe across different repositories. See the [NOTICE](NOTICE) file for our full local-only Data Privacy Statement.

## Quick Start

> **Prerequisites:** `git`, and one of: [Gemini/Antigravity](https://github.com/google-gemini/antigravity), [Kiro](https://kiro.dev), or [GitHub Copilot](https://github.com/features/copilot)

```bash
git clone https://github.com/nseney1/prism-ai-steering.git
cd prism-ai-steering
cp install/steering.conf.example steering.conf   # Optional: customize for your team

# Linux, macOS, WSL, Windows (Git Bash):
make install                              # Gemini / Antigravity (default)
bash install/install.sh gemini --local    # Install rules to project .prism/ dir

# Windows (Native PowerShell):
.\install.ps1                             # Rules + skills only (hooks require bash)
```

**Activate Genesis onboarding:** Run the `genesis` skill on your repository to generate initial project-specific governance cells.
**Verify Installation:** Run `make validate` and `make doctor` to ensure your deployment is healthy.

## Architecture

The governance architecture follows a three-layer biological hierarchy:

```text
🌲 BIOME (Global)       → Review Modes: Breeze through Tempest
🍄 FOREST FLOOR         → Review Prongs: Spores through Mulch  
🌱 CELL (Repo-Local)    → Adaptive: Vacuoles, Chloroplasts, Walls, Membranes, Plasmodesmata
```

- **Biome Layer**: Global operational modes that determine the rigorousness of review.
- **Forest Floor Layer**: Modular analytical prongs that compose the reviews, ranging from basic heuristics (Spores) to deep security verification (Bedrock).
- **Cell Layer**: Ephemeral, repository-specific invariants generated dynamically based on local codebase features, traps, and performance metrics.

## Review Protocol

The framework enforces code modifications using tiered Review Modes and structured Review Prongs.

### Review Modes
| Mode | Dispatches | Cost | Best For |
|:-----|:----------:|:----:|:---------|
| 🌱 Breeze | 2 | ~3-4k | Known bugs, renames |
| 🌬️ Gale | 3-4 | ~4k | Quick reviews |
| 🔱 Trident | 5-8 | ~8-12k | Features, refactors |
| 🌊 Maelstrom | 7-12 | ~15-20k | Architecture, security |
| ⛈️ Tempest | 8-12 | ~30-50k | Catastrophic risk |

### Review Prongs
| Prong | Purpose | Output Budgets |
|:------|:--------|:---------------|
| 🍄 Spores | Width/Heuristics survey | Lightweight |
| 🍄 Mycelium | Blast radius impact | Medium |
| 🌿 Roots | Root-cause depth | High |
| 🌹 Thorns | Adversarial testing | High |
| 🪨 Bedrock | Final verification gate | Binary Gate |
| 🍂 Mulch | Learning extraction | Lightweight |

*An **escalation sentinel** runs dynamically in the PreInvocation lifecycle to evaluate diff sensitivity and automatically dictate the minimum Review Mode (e.g., Breeze vs Tempest).*

## 📜 Rules

| Rule | Trigger | Purpose |
|:-----|:--------|:--------|
| [providence.md](rules/providence.md) | always_on | Codebase grounding, no hallucinations, diagnose-before-repair. |
| [cost-optimization.md](rules/cost-optimization.md) | always_on | Token efficiency, diffs-only edits, FPSR metric (>80%). |
| [subagent-delegation.md](rules/subagent-delegation.md) | always_on | Context protection, concurrency limits, delegation floor. |
| [architectural-tenets.md](rules/architectural-tenets.md) | model_decision | Pragmatism, trade-off analysis, scale-to-zero. |
| [polyglot-standards.md](rules/polyglot-standards.md) | model_decision | Unified entrypoints (Makefiles), containerization. |
| [feature-specs.md](rules/feature-specs.md) | model_decision | PRD structure, acceptance criteria, documentation. |
| [testing.md](rules/testing.md) | model_decision | Behavioral testing, sad paths, ast.parse ban. |
| [documentation.md](rules/documentation.md) | model_decision | ADRs, actionable READMEs, Mermaid diagrams. |
| [destructive-ops.md](rules/destructive-ops.md) | model_decision | Dry-run mandates for IaC, database mutations, bulk git. |
| [git-workflow.md](rules/git-workflow.md) | model_decision | Conventional commits, .gitignore verification. |
| [desktop-automation.md](rules/desktop-automation.md) | model_decision | PyAutoGUI/xdotool safety, focus verification. |

## 🧠 Skills

| Skill | Purpose |
|:------|:--------|
| [adaptive-reviewer](skills/adaptive-reviewer/SKILL.md) | Auto-escalating review orchestrator with subagent nesting. |
| [domain-researcher](skills/domain-researcher/SKILL.md) | Compiles verified external facts (wikis, API docs). |
| [genesis](skills/genesis/SKILL.md) | 5-stage codebase onboarding: Canopy → Rings → Taproot → Lichen → Cytogenesis. |
| [governance-auditor](skills/governance-auditor/SKILL.md) | Mechanical per-rule PASS/FAIL compliance checks. |
| [incident-debug](skills/incident-debug/SKILL.md) | SRE: reproduce → isolate → diagnose → fix → verify. |
| [performance-audit](skills/performance-audit/SKILL.md) | Hot-path allocations, O(n²) patterns, GC pressure. |
| [post-mortem](skills/post-mortem/SKILL.md) | Blameless retrospective analysis, pattern extraction. |
| [readme-writer](skills/readme-writer/SKILL.md) | Scannable, copy-pasteable developer READMEs. |
| [refactoring-pilot](skills/refactoring-pilot/SKILL.md) | Mikado Method, incremental moves across 4+ files. |
| [security-audit](skills/security-audit/SKILL.md) | AppSec Engineer: OWASP Top 10, hardcoded secrets. |
| [session-monitor](skills/session-monitor/SKILL.md) | Live waste trajectory tracking, periodic probes. |
| [session-preflight](skills/session-preflight/SKILL.md) | Pre-flight: venv health, git state, test suite verification. |
| [spec-synthesizer](skills/spec-synthesizer/SKILL.md) | Cross-references multi-lens findings into prioritized plans. |
| [staff-review](skills/staff-review/SKILL.md) | Multi-lens fan-out (10 lenses) with staff-level synthesis. |
| [visual-analyst](skills/visual-analyst/SKILL.md) | Screen & UI analysis: game state, regressions. |

## Adaptive Governance (Cells)

Cells are atomic, dynamically generated governance invariants that live exclusively inside a repository (`.prism/cells/`). 
1. **Vacuole**: Traps and anti-patterns.
2. **Chloroplast**: Accelerators and repo-specific personas.
3. **Cell Wall**: Boundary conditions and invariants.
4. **Membrane**: Context filtering and escalation overrides.
5. **Plasmodesmata**: Cross-repo data boundaries and service connections.

### Cell Lifecycle
Cells operate on a Darwinian evolutionary lifecycle:
`Generate → Score → Adapt → Prune → Promote`

A background **fitness function** monitors the success rate (true positives) of each cell against its disruption rate (false positives). Overperforming cells are kept (or promoted globally), and underperforming ones are autonomously adapted or driven to extinction. 

You can manually trigger these via: `python3 scripts/cell_fitness.py`, `scripts/cell_selection.sh`, `python3 scripts/cell_adapt.py`, `python3 scripts/cell_promote.py`.

## 📜 Scripts

Refer to [docs/SCRIPTS.md](docs/SCRIPTS.md) for full documentation of the 25 system scripts. Highlights include:
- `cell_selection.sh`: Main entrypoint for evaluating cell fitness.
- `cell_signal.sh`: External fitness signal API for CI/CD and monitoring integration.
- `cell_create.sh`: Programmatic cell creation from automated systems.
- `cell_demote.py`: Reverse promotion for cells causing issues in new contexts.
- `escalation_sentinel.sh`: Predicts escalation necessity.
- `governance_init.sh`: Seeds contexts, domain hints and tests.
- `metrics_snapshot.sh`: Snapshots environment metrics telemetry.
- `token_census.py`: Uses Gemini SDK to validate token budgets.

## Configuration

Copy [`steering.conf.example`](install/steering.conf.example) → `steering.conf` to customize platform, team size, git strategy, approval chains, and hooks configuration. 
It includes `TEAM_REPO` and `ORG_REPO` configuration for multi-developer and multi-team governance convergence.

### Cross-OS Support Matrix

| OS / Environment | Shell | Command | Rules | Skills | Hooks | Notes |
|:-----------------|:------|:--------|:-----:|:------:|:-----:|:------|
| **Linux** | Bash | `make install` | ✅ | ✅ | ✅ | Full support (`--local` supported) |
| **macOS** | Zsh / Bash | `make install` | ✅ | ✅ | ✅ | Full support |
| **WSL** | Bash | `make install` | ✅ | ✅ | ✅ | Auto-resolves Windows user profile |
| **Windows (Git Bash)** | Bash | `make install` | ✅ | ✅ | ✅ | Full support via bash runtime |
| **Windows (PowerShell)** | PowerShell | `.\install.ps1` | ✅ | ✅ | ❌ | Rules + skills only; hooks require bash |

## Team Setup

Prism AI Steering supports team-level governance through a shared Git repository. To set this up, define `TEAM_REPO` in your `steering.conf`.

```bash
# Sync local cells and metrics to the team repo
bash scripts/team_sync.sh push

# Pull new cells from other team members
bash scripts/team_sync.sh pull
```

## Uninstalling

To remove all Prism AI Steering files from your system:

```bash
bash install/uninstall.sh gemini
```

You can also use `--dry-run` to see what will be removed, and `--keep-config` to preserve `steering.conf`.


## Evolution
Prism AI Steering has evolved across 15 measured phases, from manually written logic into a self-adapting machine:
- Phases 1-5: Prescriptive logic extraction and optimization.
- Phases 6-10: Multi-lens scaling and Autonomous Orchestration.
- Phases 11-12: Full dataset mapping and token census calibration.
- Phase 13: Cytogenesis — Local governance and cell generation.
- Phase 14: Natural Selection — Evolutionary scaling and cross-repo speciation.
- Phase 15: Team Topology & Clean Uninstaller.
- Phase 17: Evolutionary Computation — GA operators, half-life decay, metamorphosis, horizontal gene transfer.

Read the [EVOLUTION.md](docs/EVOLUTION.md) for a comprehensive breakdown, driven by 6 core Design Principles ensuring empirical, adaptive, hypothesis-driven, system-first governance.

## Metrics
- **Total System Idle Overhead**: 4,380 tokens/turn
- **Waste Rate**: ~1.1% in best governed sessions
- **Calibrated Token Ratio**: 1.35 measured directly against models
See [METRICS.md](docs/METRICS.md) for a complete system breakdown.

## Design Principles

1. **Evidence over intuition** — Every rule traces back to observed steps wasted. No rule exists "just in case."
2. **Accuracy over speed** — The agent must never sacrifice correctness to save tokens.
3. **Rules as a system** — Cross-references between rules are intentional. Providence §3 mandates read-before-write; refactoring-pilot operationalizes it as a phased workflow.
4. **Continuous validation** — Rules aren't "done" after review. Governance is a living system that evolves with each session.
5. **Installation completeness** — Governance installed at partial fidelity provides false assurance. Every installer path must deploy rules, skills, and hooks with the same completeness.
6. **Hypothesis-driven governance** — Every governance extension must carry its own falsifiability criteria. A rule, persona, or adaptation that cannot be tested has no place in the system. Generated extensions (Chloroplasts, Vacuoles) must specify what they predict, how to measure it, and when to prune if unvalidated. The scientific method is not just how we evolve the system — it IS the system.

## License

Apache 2.0 — Copyright 2026 Nicholas Seney
See [NOTICE](NOTICE) for Data Privacy details.
