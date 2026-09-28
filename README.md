# 🔮 Prism AI Steering

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue?style=flat-square)](LICENSE)
[![Rules](https://img.shields.io/badge/Rules-11-green?style=flat-square)](#rules)
[![Skills](https://img.shields.io/badge/Skills-15-purple?style=flat-square)](#skills)
[![Scripts](https://img.shields.io/badge/Scripts-37-red?style=flat-square)](#scripts)
[![Phases](https://img.shields.io/badge/Phases-17-blue?style=flat-square)](docs/EVOLUTION.md)
[![Cells](https://img.shields.io/badge/Cells-5-orange?style=flat-square)](#adaptive-governance-cells)
[![Version](https://img.shields.io/badge/Version-0.20.0-informational?style=flat-square)](docs/CHANGELOG.md)

Prism AI Steering is an adaptive governance framework that generates, measures, and evolves its own rules based on observed agent behavior. Built on top of continuous feedback loops and biological natural selection principles, it ensures agents remain grounded, efficient, and safe across different repositories. See the [NOTICE](NOTICE) file for our full local-only Data Privacy Statement.

> **The Problem**: Ungoverned AI coding agents waste 25-56% of tokens in circular rework loops, hallucinated API calls, and broken assumptions. Static rule files (`.cursorrules`, `CLAUDE.md`) help but never adapt.
>
> **The Result**: Prism reduces waste to under 5% (1.1% best-case) while adding only ~3.4% idle context overhead. Rules that stop proving themselves die. Rules that keep proving themselves get promoted. This is Darwinian governance.

## Quick Start

### Installation

```bash
# Clone
git clone https://github.com/nseney1/prism-ai-steering.git && cd prism-ai-steering

# Option A: Global install (Gemini / Antigravity)
make install

# Option B: Project-local install (creates .prism/ in your repo)
bash install/install.sh gemini --local

# Other platforms
bash install/install.sh kiro       # AWS Kiro
bash install/install.sh copilot    # GitHub Copilot
```

### SDK Installation

```bash
# Python
pip install prism-steering

# JavaScript / TypeScript  
npm install prism-steering
```

```python
from prism_sdk import Governance

gov = Governance(project_root='.')
landscape = gov.fitness_landscape(bayesian=True)
coverage = gov.coverage_report()
grade = gov.grade()
gov.signal('wall-gae-truncation', 'tp', metric={'survival_day': 12})
```

```javascript
const { Governance } = require('prism-steering');
const gov = new Governance('.');
const grade = await gov.grade();
const entropy = await gov.entropy();
```

### Onboarding

After installation, open your AI assistant in your project and prompt:

> *Run the genesis skill to inspect this repository and seed governance cells.*

Genesis scans your stack (languages, frameworks, dependencies) and creates tailored `.prism/cells/` in seconds. Domain templates (`templates/`) are auto-detected based on your project type.

### Natural Language Cell Creation

Create cells by describing your concern in plain English:

```bash
bash scripts/cell_create.sh --from-description "PPO clip ratio must stay between 0.1 and 0.3"
```

Requires a Gemini API key configured via environment variable, `steering.conf`, or `.prism/credentials.conf`.

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

> **Note**: Thorns is a *review prong* (adversarial falsification stage), not a top-level review mode. It powers Maelstrom and Tempest automatically and can be invoked standalone. The 5 review modes are: Breeze → Gale → Trident → Maelstrom → Tempest.

*An **escalation sentinel** runs dynamically in the PreInvocation lifecycle to evaluate diff sensitivity and recommends diff-sensitivity review tiers during session initialization.*

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

| Biological Unit | Software Equivalent | What It Does |
|:----------------|:-------------------|:-------------|
| **Vacuole** | Anti-pattern trap | Catches known failure modes (e.g., "Don't use raw coordinates") |
| **Chloroplast** | Domain persona | Injects idiomatic patterns (e.g., "Use async FastAPI conventions") |
| **Cell Wall** | Hard invariant | Non-negotiable safety gate (e.g., "Never skip GAE truncation") |
| **Membrane** | Escalation gate | Forces elevated review when sensitive areas change |
| **Plasmodesmata** | Cross-repo contract | Governs data shapes and APIs between services |

### Cell Lifecycle
Cells operate on a Darwinian evolutionary lifecycle:

```text
Generate → Score (Half-Life) → Adapt / Crossover → Metamorphose → Prune / Apoptosis → Promote / Transfer
   ↑                                                                                    |
   └───────────────────────── External Fitness Signals (CI/CD, tests, metrics) ───────────┘
```

**Evolutionary Operators** (v0.17.0+):
- **Crossover** (`cell_crossover.py`): Merges complementary hypotheses from two high-fitness cells
- **Tournament Selection** (`cell_tournament.py`): Diversity-preserving selection pressure
- **Metamorphosis** (`cell_metamorphose.py`): Vacuoles harden into Walls, Walls graduate to Rules through proof
- **Half-Life Decay**: Cell confidence decays exponentially unless reinforced by new evidence
- **Apoptosis**: Immediate eviction when false positives exceed 2× true positives
- **Horizontal Gene Transfer** (`cell_transfer.sh`): Cross-project cell sharing with 5-session probation
- **Lineage Tracking**: Phylogenetic provenance (`parent_id`, `created_by`, `generation`)

**Research-Grade Analysis** (v0.19.0+):
- **Bayesian Fitness** (`cell_fitness.py --bayesian`): Beta-Binomial posterior with Jeffrey's prior and credible intervals
- **Quorum Sensing** (`cell_quorum.py`): Detects systemic issues when ≥3 cells trigger on the same diff
- **Coverage Maps** (`cell_coverage.py`): Visualize which files have governance cell coverage
- **Governance Replay** (`governance_replay.py`): Retrospective analysis — "Would today's cells have caught this bug?"
- **Counterfactual ROI** (`--counterfactual --cell <name>`): Dollar-value estimation against historical commits
- **Adversarial Testing** (`cell_adversarial.py`): Probes cells for bypass vulnerabilities (rename, config, import, staleness)
- **Entropy Rate** (`governance_entropy.py`): Shannon entropy to detect fossilization vs active adaptation
- **Report Card** (`governance_grade.py`): Single letter grade (A+ through F) across 5 dimensions

**Platform Features** (v0.19.1+):
- **Pre-Commit Hook** (`install/hooks/pre-commit`): Advisory cell scanning on every git commit
- **Cell Dependencies** (`cell_deps.py`): Co-trigger relationship graph with Mermaid output
- **Dormant Spores**: Pruned cells saved to `.spores.jsonl`, auto-reactivated on pattern match
- **Stochastic Genesis**: Diversity injection from domain templates every N sessions
- **Mulch→Cell Pipeline**: Tempest findings automatically create vacuole cells

**Security Hardening** (v0.19.0+):
- **Wall Extinction Immunity**: Walls can never be killed by apoptosis (APOPTOSIS_WARNING instead)
- **Specificity Penalty**: Anti-Goodhart measure — cells triggering >80% of sessions are penalized
- **Antifragile Bonus**: +5% fitness per survived Tempest/Maelstrom review
- **SNR Quality Metric**: Signal-to-noise ratio in dB per cell

A background **fitness function** monitors the success rate (true positives) of each cell against its disruption rate (false positives). Overperforming cells are kept (or promoted globally), and underperforming ones are autonomously adapted or driven to extinction. 

You can manually trigger these via: `python3 scripts/cell_fitness.py`, `scripts/cell_selection.sh`, `python3 scripts/cell_adapt.py`, `python3 scripts/cell_promote.py`, `scripts/cell_signal.sh`, `scripts/cell_create.sh`, `python3 scripts/cell_scan.py`, `python3 scripts/fitness_landscape.py`, `python3 scripts/cell_crossover.py`, `python3 scripts/cell_metamorphose.py`, `scripts/cell_transfer.sh`.

## 📜 Scripts

Refer to [docs/SCRIPTS.md](docs/SCRIPTS.md) for full documentation of the 37 system scripts. Highlights include:

**Cell Lifecycle**: `cell_fitness.py`, `cell_selection.sh`, `cell_adapt.py`, `cell_scan.py`, `cell_signal.sh`, `cell_create.sh`, `cell_crossover.py`, `cell_metamorphose.py`, `cell_promote.py`, `cell_transfer.sh`

**Analysis & Research**: `cell_quorum.py`, `cell_coverage.py`, `governance_replay.py`, `governance_trends.py`, `governance_grade.py`, `governance_entropy.py`, `cell_adversarial.py`, `cell_deps.py`

**AI-Assisted**: `cell_create_nl.py` (natural language cell creation via Gemini)

**Infrastructure**: `governance_init.sh`, `session_close.sh`, `escalation_sentinel.sh`, `prism_resolve.py`, `safety_gate.sh`, `team_sync.sh`, `metrics_snapshot.sh`, `token_census.py`

## Configuration

Copy [`steering.conf.example`](install/steering.conf.example) → `steering.conf` to customize platform, team size, git strategy, approval chains, and hooks configuration. 
It includes `TEAM_REPO` and `ORG_REPO` configuration for multi-developer and multi-team governance convergence.

Key `steering.conf` options (see `install/steering.conf.example` for full reference):

| Variable | Default | Description |
|:---------|:--------|:------------|
| `STEERING_PLATFORM` | `gemini` | Target AI platform |
| `DEFAULT_REVIEW_MODE` | `gale` | Session default review intensity |
| `CELL_HALF_LIFE_DAYS` | `30` | Days for fitness confidence to halve |
| `CELL_HALF_LIFE_WALL` | `null` | Walls (invariants) never decay |
| `TEAM_SIZE` | `solo` | Team topology configuration |
| `PRISM_ROOT` | (auto) | Override workspace resolution |
| `GEMINI_API_KEY` | (none) | API key for natural language cell creation |
| `STOCHASTIC_GENESIS_INTERVAL` | `10` | Sessions between diversity injection |
| `TOTAL_SESSIONS` | `30` | Session counter for specificity penalty |

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


## How Prism Differs

| | Static Linters | Prompt Files (`.cursorrules`) | Runtime Guardrails | **Prism** |
|:--|:---:|:---:|:---:|:---:|
| **Adaptability** | Static | Manual updates | Static policies | **Self-evolving via Darwinian fitness** |
| **Learns from outcomes** | No | No | No | **Yes — TP/FP scoring + half-life** |
| **Cross-repo learning** | No | Copy-paste | No | **Horizontal gene transfer** |
| **Context cost** | Zero | Fixed overhead | Extra inference | **Tiered loading (3.4% idle)** |
| **Failure modes caught** | Syntax/types | Generic guidelines | Unsafe strings | **Rework loops, hallucinations, waste** |
| **SDK available** | No | No | Sometimes | **Yes — Python + npm** |

## Documentation

| Document | Description |
|:---------|:------------|
| [CHANGELOG](docs/CHANGELOG.md) | Release history |
| [EVOLUTION](docs/EVOLUTION.md) | Phase-by-phase development narrative |
| [SCRIPTS](docs/SCRIPTS.md) | Full script catalog (37 scripts) |
| [BENCHMARK](docs/BENCHMARK.md) | Reproducible governance effectiveness protocol |
| [METRICS](docs/METRICS.md) | Empirical measurement methodology |
| [ABSTRACT](docs/ABSTRACT.md) | Research paper abstract |
| [CONTRIBUTING](docs/CONTRIBUTING.md) | Contribution guidelines |
| [Templates](templates/README.md) | Domain-specific cell template packs |

## Evolution
Prism AI Steering has evolved across 17 measured phases, from manually written logic into a self-adapting machine:
- Phases 1-5: Prescriptive logic extraction and optimization.
- Phases 6-10: Multi-lens scaling and Autonomous Orchestration.
- Phases 11-12: Full dataset mapping and token census calibration.
- Phase 13: Cytogenesis — Local governance and cell generation.
- Phase 14: Natural Selection — Evolutionary scaling and cross-repo speciation.
- Phase 15: Team Topology & Clean Uninstaller.
- Phase 16: Automated Workflows — CI/CD integration and automated cell triggering.
- Phase 17: Evolutionary Computation — GA operators, half-life decay, metamorphosis, horizontal gene transfer.
- Phase 18: Research Integration — Bayesian fitness, quorum sensing, coverage maps, governance replay.
- Phase 19: Platform Grade — Pre-commit hooks, report card, adversarial testing, entropy rate.
- Phase 20: SDK & AI-Assisted — Python/npm SDKs, natural language cell creation, counterfactual ROI.

Read the [EVOLUTION.md](docs/EVOLUTION.md) for a comprehensive breakdown, driven by 6 core Design Principles ensuring empirical, adaptive, hypothesis-driven, system-first governance.

## Metrics
- **Total System Idle Overhead**: 4,380 tokens/turn
- **Waste Rate**: ~1.1% in best governed sessions
- **Calibrated Token Ratio**: 1.35 measured directly against models
See [METRICS.md](docs/METRICS.md) for a complete system breakdown.
See [BENCHMARK.md](docs/BENCHMARK.md) for the standardized governance effectiveness benchmark.

## Design Principles

1. **Evidence over intuition** — Every rule traces back to observed steps wasted. No rule exists "just in case."
2. **Accuracy over speed** — The agent must never sacrifice correctness to save tokens.
3. **Rules as a system** — Cross-references between rules are intentional. Providence §3 mandates read-before-write; refactoring-pilot operationalizes it as a phased workflow.
4. **Continuous validation** — Rules aren't "done" after review. Governance is a living system that evolves with each session.
5. **Installation completeness** — Governance installed at partial fidelity provides false assurance. Every installer path must deploy rules, skills, and hooks with the same completeness.
6. **Hypothesis-driven governance** — Every governance extension must carry its own falsifiability criteria. A rule, persona, or adaptation that cannot be tested has no place in the system. Generated extensions (Chloroplasts, Vacuoles) must specify what they predict, how to measure it, and when to prune if unvalidated. The scientific method is not just how we evolve the system — it IS the system.

## Next Steps

- 🚀 **Try Prism**: `make install` and run Genesis on your repository
- 📦 **Use the SDK**: `pip install prism-steering` or `npm install prism-steering`
- 🔮 **NL Cell Creation**: `cell_create.sh --from-description "your concern here"`
- 📊 **Report Card**: `python3 scripts/governance_grade.py` for instant governance health
- 📊 **Run the Benchmark**: Measure governance effectiveness with [BENCHMARK.md](docs/BENCHMARK.md)
- 🧬 **Explore Templates**: Browse domain packs in [templates/](templates/README.md)
- 📄 **Read the Research**: Review the [Abstract](docs/ABSTRACT.md) and [Evolution](docs/EVOLUTION.md)
- 🤝 **Contribute**: See [CONTRIBUTING.md](docs/CONTRIBUTING.md)

## License

Apache 2.0 — Copyright 2026 Nicholas Seney
See [NOTICE](NOTICE) for Data Privacy details.
