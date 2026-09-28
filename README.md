# 🧬 Soma

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue?style=flat-square)](LICENSE)
[![Genome](https://img.shields.io/badge/Genome-11_Genes-green?style=flat-square)](#-genome)
[![Organs](https://img.shields.io/badge/Organs-15-purple?style=flat-square)](#-organs)
[![Enzymes](https://img.shields.io/badge/Enzymes-40-red?style=flat-square)](#%EF%B8%8F-enzymes)
[![Cells](https://img.shields.io/badge/Cells-5_Types-orange?style=flat-square)](#-cells)
[![Version](https://img.shields.io/badge/Version-0.22.0-informational?style=flat-square)](docs/CHANGELOG.md)
[![Blog Post](https://img.shields.io/badge/Blog-dev.to-black?style=flat-square&logo=devdotto)](https://dev.to/nseney1/rules-that-cant-prove-themselves-die-adaptive-governance-for-ai-coding-agents-25bn)

**Your codebase is a living organism. Soma gives it an immune system.**

Soma is an adaptive governance framework that generates, measures, and evolves its own rules based on observed agent behavior. Built on biological natural selection, it ensures AI coding agents remain grounded, efficient, and safe — then gets out of the way.

> **The Problem**: Ungoverned AI coding agents waste 25–56% of tokens in circular rework loops, hallucinated API calls, and broken assumptions. Static rule files (`.cursorrules`, `CLAUDE.md`) help but never adapt.
>
> **The Organism**: Soma reduces waste to under 5% (1.1% best-case) while adding only ~3.4% idle context overhead. Genes that stop proving themselves die. Genes that keep proving themselves get promoted. This is Darwinian governance.

See the [NOTICE](NOTICE) file for our full local-only Data Privacy Statement.

---

## Quick Start

### Install

```bash
# Clone
git clone https://github.com/nseney1/soma.git && cd soma

# Option A: Global install (Gemini / Antigravity)
make install

# Option B: Project-local install (creates .soma/ in your repo)
bash install/install.sh gemini --local

# Other platforms
bash install/install.sh kiro       # AWS Kiro
bash install/install.sh copilot    # GitHub Copilot
```

### MCP Server (Recommended)

Add Soma as an MCP server in your AI agent's config — **zero API key needed**. The agent *is* the LLM.

```json
{
  "mcpServers": {
    "soma": {
      "command": "python3",
      "args": ["-m", "soma_mcp"],
      "cwd": "/path/to/your/project"
    }
  }
}
```

Works with Gemini Antigravity, Claude Code, Cursor, and any MCP-compatible agent. Tools exposed: `soma_create_cell`, `soma_scan`, `soma_grade`, `soma_coverage`, `soma_fitness`, `soma_list_cells`.

### SDK

```bash
pip install soma-steering          # Python
npm install soma-steering          # JavaScript / TypeScript
```

```python
from soma_sdk import Governance

gov = Governance(project_root='.')
landscape = gov.fitness_landscape(bayesian=True)
coverage = gov.coverage_report()
grade = gov.grade()
gov.signal('wall-gae-truncation', 'tp', metric={'survival_day': 12})
```

```javascript
const { Governance } = require('soma-steering');
const gov = new Governance('.');
const grade = await gov.grade();
const entropy = await gov.entropy();
```

### Onboarding

After installation, open your AI assistant in your project and prompt:

> *Run the genesis organ to inspect this repository and seed governance cells.*

Genesis scans your stack (languages, frameworks, dependencies) and creates tailored `.soma/cells/` in seconds. Domain templates (`templates/`) are auto-detected based on your project type.

### Natural Language Cell Creation

Create cells by describing your concern in plain English:

```bash
bash enzymes/cell_create.sh --from-description "PPO clip ratio must stay between 0.1 and 0.3"
```

Works with **any AI provider** — Gemini, Anthropic, OpenAI — or via MCP stdio (zero API key needed when running inside an AI agent). Set `--provider gemini|anthropic|openai|prompt-only` or configure `SOMA_INFERENCE_PROVIDER` in `soma.conf`.

---

## Anatomy of the Organism

Soma models your codebase as a living organism. Every component maps to biology:

```text
┌─────────────────────────────────────────────────────────────┐
│  🧬 GENOME (genome/)         11 Genes — inherited DNA      │
│  🫀 ORGANS (organs/)          15 Organs — complex skills    │
│  ⚗️  ENZYMES (enzymes/)       39 Enzymes — catalytic scripts│
├─────────────────────────────────────────────────────────────┤
│  🌲 BIOME (Global)      → Environmental Pressure Levels    │
│     Breeze → Gale → Trident → Maelstrom → Tempest          │
│  🍄 FOREST FLOOR        → Analytical Prongs                │
│     Spores → Mycelium → Roots → Thorns → Bedrock → Mulch   │
│  🌱 CELLS (.soma/cells/) → Adaptive Immune Response        │
│     Vacuoles · Chloroplasts · Walls · Membranes             │
└─────────────────────────────────────────────────────────────┘
```

| Biological Layer | Directory | What It Contains |
|:-----------------|:----------|:-----------------|
| **Genome** | `genome/` | 11 Genes — the organism's DNA. Inherited behavioral rules, rarely mutated. |
| **Organs** | `organs/` | 15 Organs — complex multi-cell structures. Skills like adaptive-reviewer, genesis, security-audit. |
| **Enzymes** | `enzymes/` | 39 Enzymes — small catalysts. Scripts that drive specific reactions (fitness scoring, cell creation, team sync). |
| **Immune System** | `immune_system/` | Mulch queue, immune data. The organism's self-defense memory. |
| **Cells** | `.soma/cells/` | Per-repo adaptive invariants. Generated, tested, evolved, or driven to extinction. |

---

## 🛡️ Immune Response (Review Protocol)

When code changes, the organism mounts an immune response. The intensity scales with risk:

### Environmental Pressure (Review Modes)

| Mode | Dispatches | Cost | Best For |
|:-----|:----------:|:----:|:---------|
| 🌱 Breeze | 2 | ~3-4k | Known bugs, renames |
| 🌬️ Gale | 3-4 | ~4k | Quick reviews |
| 🔱 Trident | 5-8 | ~8-12k | Features, refactors |
| 🌊 Maelstrom | 7-12 | ~15-20k | Architecture, security |
| ⛈️ Tempest | 8-12 | ~30-50k | Catastrophic risk |

### Analytical Prongs

| Prong | Purpose | Budget |
|:------|:--------|:-------|
| 🍄 Spores | Width / heuristics survey | Lightweight |
| 🍄 Mycelium | Blast radius impact analysis | Medium |
| 🌿 Roots | Root-cause depth investigation | High |
| 🌹 Thorns | Adversarial falsification | High |
| 🪨 Bedrock | Final verification gate | Binary |
| 🍂 Mulch | Learning extraction | Lightweight |

> **Note**: An **escalation sentinel** runs dynamically in the PreInvocation lifecycle to evaluate diff sensitivity and auto-escalate the review mode.

---

## 🧬 Genome

The organism's DNA — 11 genes that define inherited behavior. Always-on genes are loaded every session; conditional genes activate on demand.

| Gene | Trigger | Purpose |
|:-----|:--------|:--------|
| [providence](genome/providence.md) | always_on | Codebase grounding, no hallucinations, diagnose-before-repair |
| [cost-optimization](genome/cost-optimization.md) | always_on | Token efficiency, diffs-only edits, FPSR metric (>80%) |
| [subagent-delegation](genome/subagent-delegation.md) | always_on | Context protection, concurrency limits, delegation floor |
| [architectural-tenets](genome/architectural-tenets.md) | model_decision | Pragmatism, trade-off analysis, scale-to-zero |
| [polyglot-standards](genome/polyglot-standards.md) | model_decision | Unified entrypoints (Makefiles), containerization |
| [feature-specs](genome/feature-specs.md) | model_decision | PRD structure, acceptance criteria, documentation |
| [testing](genome/testing.md) | model_decision | Behavioral testing, sad paths, ast.parse ban |
| [documentation](genome/documentation.md) | model_decision | ADRs, actionable READMEs, Mermaid diagrams |
| [destructive-ops](genome/destructive-ops.md) | model_decision | Dry-run mandates for IaC, database mutations, bulk git |
| [git-workflow](genome/git-workflow.md) | model_decision | Conventional commits, .gitignore verification |
| [desktop-automation](genome/desktop-automation.md) | model_decision | PyAutoGUI/xdotool safety, focus verification |

---

## 🫀 Organs

Complex multi-cell structures — each organ performs a specialized function.

| Organ | Purpose |
|:------|:--------|
| [adaptive-reviewer](organs/adaptive-reviewer/SKILL.md) | Auto-escalating review orchestrator with subagent nesting |
| [domain-researcher](organs/domain-researcher/SKILL.md) | Compiles verified external facts (wikis, API docs) |
| [genesis](organs/genesis/SKILL.md) | 5-stage codebase onboarding: Canopy → Rings → Taproot → Lichen → Cytogenesis |
| [governance-auditor](organs/governance-auditor/SKILL.md) | Mechanical per-gene PASS/FAIL compliance checks |
| [incident-debug](organs/incident-debug/SKILL.md) | SRE: reproduce → isolate → diagnose → fix → verify |
| [performance-audit](organs/performance-audit/SKILL.md) | Hot-path allocations, O(n²) patterns, GC pressure |
| [post-mortem](organs/post-mortem/SKILL.md) | Blameless retrospective analysis, pattern extraction |
| [readme-writer](organs/readme-writer/SKILL.md) | Scannable, copy-pasteable developer READMEs |
| [refactoring-pilot](organs/refactoring-pilot/SKILL.md) | Mikado Method, incremental moves across 4+ files |
| [security-audit](organs/security-audit/SKILL.md) | AppSec Engineer: OWASP Top 10, hardcoded secrets |
| [session-monitor](organs/session-monitor/SKILL.md) | Live waste trajectory tracking, periodic probes |
| [session-preflight](organs/session-preflight/SKILL.md) | Pre-flight: venv health, git state, test suite verification |
| [spec-synthesizer](organs/spec-synthesizer/SKILL.md) | Cross-references multi-lens findings into prioritized plans |
| [staff-review](organs/staff-review/SKILL.md) | Multi-lens fan-out (10 lenses) with staff-level synthesis |
| [visual-analyst](organs/visual-analyst/SKILL.md) | Screen & UI analysis: game state, regressions |

---

## 🌱 Cells

Cells are the adaptive immune system — atomic, dynamically generated invariants that live exclusively inside your repository (`.soma/cells/`).

| Cell Type | Biological Role | What It Does |
|:----------|:----------------|:-------------|
| **Vacuole** | Waste storage / trap | Catches known anti-patterns (e.g., "Don't use raw coordinates") |
| **Chloroplast** | Energy / growth | Injects idiomatic patterns (e.g., "Use async FastAPI conventions") |
| **Cell Wall** | Rigid boundary | Non-negotiable safety gate (e.g., "Never skip GAE truncation") |
| **Membrane** | Selective permeability | Forces elevated review when sensitive areas change |
| **Plasmodesmata** | Inter-cell channels | Governs data shapes and APIs between services |

### Cell Lifecycle

Cells operate on a Darwinian evolutionary lifecycle:

```text
Generate → Score (Telomere Shortening) → Adapt / Crossover → Differentiate → Prune / Apoptosis → Promote
   ↑                                                                                              |
   └──────────────────────── External Fitness Signals (CI/CD, tests, metrics) ─────────────────────┘
```

**Evolutionary operators**: Crossover (merges high-fitness cells), Tournament Selection (diversity-preserving), Differentiation (vacuoles harden into walls), Telomere Shortening (confidence decays unless reinforced), Apoptosis (immediate eviction on excess false positives), Horizontal Gene Transfer (cross-project sharing with probation), Lineage Tracking (phylogenetic provenance).

**Research-grade analysis**: Bayesian Fitness (Beta-Binomial posterior), Quorum Sensing (systemic multi-cell triggers), Coverage Maps, Governance Replay ("would today's cells have caught this bug?"), Counterfactual ROI, Adversarial Testing, Entropy Rate (fossilization detection), Report Card (A+ through F).

**Tiered enforcement**: Cells earn their enforcement tier through demonstrated defect prevention — `advisory` (prompt injection) → `mechanical` (pre-commit block at 85%) → `gate` (runtime assertion at 95%). Escaped Defect Tracking from CI/tests/crashes provides ground truth that breaks the self-evaluation loop.

---

## ⚗️ Enzymes

39 catalytic scripts that drive the organism's reactions. See [SCRIPTS.md](docs/SCRIPTS.md) for full documentation.

| Category | Enzymes |
|:---------|:--------|
| **Cell Lifecycle** | `cell_fitness.py`, `cell_selection.sh`, `cell_adapt.py`, `cell_scan.py`, `cell_signal.sh`, `cell_create.sh`, `cell_crossover.py`, `cell_metamorphose.py`, `cell_promote.py`, `cell_transfer.sh`, `cell_enforce.py` |
| **Analysis** | `cell_quorum.py`, `cell_coverage.py`, `immune_replay.py`, `immune_trends.py`, `immune_grade.py`, `immune_entropy.py`, `cell_adversarial.py`, `cell_deps.py`, `cell_escaped_defects.py` |
| **AI-Assisted** | `cell_create_nl.py` — NL cell creation via any LLM provider or MCP host delegation |
| **Infrastructure** | `immune_init.sh`, `session_close.sh`, `escalation_sentinel.sh`, `soma_resolve.py`, `safety_gate.sh`, `team_sync.sh`, `metrics_snapshot.sh`, `token_census.py` |

---

## Configuration

Copy [`soma.conf.example`](install/soma.conf.example) → `soma.conf` to customize.

| Variable | Default | Description |
|:---------|:--------|:------------|
| `SOMA_PLATFORM` | `gemini` | Target AI platform: `gemini`, `kiro`, `copilot` |
| `SOMA_INFERENCE_PROVIDER` | `auto` | LLM provider: `auto`, `gemini`, `anthropic`, `openai`, `prompt-only` |
| `DEFAULT_REVIEW_MODE` | `gale` | Session default review intensity |
| `CELL_TELOMERE_DAYS` | `30` | Days for fitness confidence to halve |
| `CELL_TELOMERE_WALL` | `null` | Walls (invariants) never decay |
| `TEAM_SIZE` | `solo` | Team topology: `solo`, `small`, `team`, `enterprise` |
| `GEMINI_API_KEY` | (none) | Gemini inference (not needed with MCP) |
| `ANTHROPIC_API_KEY` | (none) | Anthropic inference (not needed with MCP) |
| `OPENAI_API_KEY` | (none) | OpenAI-compatible inference (not needed with MCP) |

### Cross-OS Support

| OS | Shell | Command | Genome | Organs | Hooks |
|:---|:------|:--------|:------:|:------:|:-----:|
| **Linux** | Bash | `make install` | ✅ | ✅ | ✅ |
| **macOS** | Zsh / Bash | `make install` | ✅ | ✅ | ✅ |
| **WSL** | Bash | `make install` | ✅ | ✅ | ✅ |
| **Windows (Git Bash)** | Bash | `make install` | ✅ | ✅ | ✅ |
| **Windows (PowerShell)** | PowerShell | `.\install.ps1` | ✅ | ✅ | ❌ |

### Team Setup

Soma supports team-level governance convergence via shared Git repositories:

```bash
bash enzymes/team_sync.sh push    # Sync local cells + metrics
bash enzymes/team_sync.sh pull    # Pull cells from teammates
```

Configure `TEAM_REPO` and optionally `ORG_REPO` in `soma.conf` for multi-team hierarchies.

---

## How Soma Differs

| | Static Linters | Prompt Files (`.cursorrules`) | Runtime Guardrails | **Soma** |
|:--|:---:|:---:|:---:|:---:|
| **Adaptability** | Static | Manual updates | Static policies | **Self-evolving via Darwinian fitness** |
| **Learns from outcomes** | No | No | No | **Yes — TP/FP scoring + telomere shortening** |
| **Learns from failures** | No | No | Alerts only | **Yes — escaped defect tracking + tier promotion** |
| **Cross-repo learning** | No | Copy-paste | No | **Horizontal gene transfer** |
| **Platform lock-in** | N/A | Platform-specific | Platform-specific | **Any agent via MCP stdio** |
| **Context cost** | Zero | Fixed overhead | Extra inference | **Tiered loading (3.4% idle)** |
| **Failure modes caught** | Syntax/types | Generic guidelines | Unsafe strings | **Rework loops, hallucinations, waste** |
| **SDK** | No | No | Sometimes | **Python + npm + MCP** |

---

## Metrics

- **Total System Idle Overhead**: 4,380 tokens/turn
- **Waste Rate**: ~1.1% in best governed sessions
- **Calibrated Token Ratio**: 1.35 measured directly against models

See [METRICS.md](docs/METRICS.md) for a complete system breakdown. See [BENCHMARK.md](docs/BENCHMARK.md) for the standardized governance effectiveness benchmark.

## Design Principles

1. **Evidence over intuition** — Every gene traces back to observed steps wasted. No gene exists "just in case."
2. **Accuracy over speed** — The agent must never sacrifice correctness to save tokens.
3. **Genes as a system** — Cross-references between genes are intentional. Providence §3 mandates read-before-write; refactoring-pilot operationalizes it as a phased workflow.
4. **Continuous validation** — Genes aren't "done" after review. Governance is a living system that evolves with each session.
5. **Installation completeness** — Governance installed at partial fidelity provides false assurance. Every installer path must deploy genome, organs, and hooks with the same completeness.
6. **Hypothesis-driven governance** — Every extension must carry its own falsifiability criteria. Generated cells (Chloroplasts, Vacuoles) must specify what they predict, how to measure it, and when to prune if unvalidated. The scientific method is not just how we evolve the system — it IS the system.
7. **Independent validation** — Self-evaluated fitness is necessary but not sufficient. Escaped defects from CI, tests, and crashes provide the ground truth that breaks the agent-grades-itself loop.

## Phylogeny

Soma has evolved across 22 measured phases, from manually written logic into a self-adapting organism:

| Phases | Theme |
|:-------|:------|
| 1–5 | Prescriptive logic extraction and optimization |
| 6–10 | Multi-lens scaling and autonomous orchestration |
| 11–12 | Full dataset mapping and token census calibration |
| 13 | **Cytogenesis** — Local governance and cell generation |
| 14 | **Natural Selection** — Evolutionary scaling, cross-repo speciation |
| 15 | Team Topology & Clean Uninstaller |
| 16 | Automated Workflows — CI/CD integration |
| 17 | **Evolutionary Computation** — GA operators, telomere decay, metamorphosis, horizontal gene transfer |
| 18 | **Research Integration** — Bayesian fitness, quorum sensing, coverage maps |
| 19 | **Platform Grade** — Pre-commit hooks, report card, adversarial testing, entropy rate |
| 20 | **SDK & AI-Assisted** — Python/npm SDKs, NL cell creation, counterfactual ROI |
| 21 | **Tiered Enforcement** — Advisory → mechanical → gate promotion lifecycle |
| 22 | **Soma Rebirth** — Biological naming unification, MCP server, multi-provider inference |

Read [PHYLOGENY.md](docs/PHYLOGENY.md) for the complete evolutionary narrative.

## Documentation

| Document | Description |
|:---------|:------------|
| [**Blog Post**](https://dev.to/nseney1/rules-that-cant-prove-themselves-die-adaptive-governance-for-ai-coding-agents-25bn) | "Rules That Can't Prove Themselves Die" — full introduction |
| [CHANGELOG](docs/CHANGELOG.md) | Release history |
| [PHYLOGENY](docs/PHYLOGENY.md) | Phase-by-phase evolutionary narrative |
| [SCRIPTS](docs/SCRIPTS.md) | Full enzyme catalog (39 scripts) |
| [BENCHMARK](docs/BENCHMARK.md) | Reproducible governance effectiveness protocol |
| [METRICS](docs/METRICS.md) | Empirical measurement methodology |
| [ABSTRACT](docs/ABSTRACT.md) | Research paper abstract |
| [CONTRIBUTING](docs/CONTRIBUTING.md) | Contribution guidelines |
| [Templates](templates/README.md) | Domain-specific cell template packs |

## Next Steps

- 🚀 **Try Soma**: `make install` and run Genesis on your repository
- 🔌 **MCP Server**: Add Soma to your agent's MCP config — zero API key needed
- 📦 **Use the SDK**: `pip install soma-steering` or `npm install soma-steering`
- 🔮 **NL Cell Creation**: `cell_create.sh --from-description "your concern here"`
- 📊 **Report Card**: `python3 enzymes/immune_grade.py` for instant governance health
- 🧬 **Explore Templates**: Browse domain packs in [templates/](templates/README.md)
- 📄 **Read the Research**: Review the [Abstract](docs/ABSTRACT.md) and [Phylogeny](docs/PHYLOGENY.md)
- 🤝 **Contribute**: See [CONTRIBUTING.md](docs/CONTRIBUTING.md)

## Uninstalling

```bash
bash install/uninstall.sh gemini           # Remove all Soma files
bash install/uninstall.sh gemini --dry-run  # Preview what will be removed
bash install/uninstall.sh gemini --keep-config  # Preserve soma.conf
```

Existing `.prism/` directories are auto-migrated to `.soma/` on install.

## License

Apache 2.0 — Copyright 2026 Nicholas Seney
See [NOTICE](NOTICE) for Data Privacy details.
