# 🧬 Soma

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue?style=flat-square)](LICENSE)
[![Genome](https://img.shields.io/badge/Genome-5_Active_Genes-green?style=flat-square)](#-genome)
[![Organs](https://img.shields.io/badge/Organs-15-purple?style=flat-square)](#-organs)
[![Enzymes](https://img.shields.io/badge/Enzymes-42-red?style=flat-square)](#%EF%B8%8F-enzymes)
[![Cells](https://img.shields.io/badge/Cells-5_Types-orange?style=flat-square)](#-cells)
[![Version](https://img.shields.io/badge/Version-0.23.0-informational?style=flat-square)](docs/CHANGELOG.md)
[![Blog Post](https://img.shields.io/badge/Blog-dev.to-black?style=flat-square&logo=devdotto)](https://dev.to/nseney1/rules-that-cant-prove-themselves-die-adaptive-governance-for-ai-coding-agents-25bn)

**Your codebase is a living organism. Soma gives it an immune system that evolves.**

Soma is an adaptive governance framework that generates, measures, and evolves its own rules based on observed agent behavior. Unlike static context files (`AGENTS.md`, `CLAUDE.md`, `.cursorrules`) — which research shows [don't improve task success rates](#-research-foundations) — Soma delivers the *minimum effective context* just-in-time via MCP tools, then evolves based on real execution outcomes.

> **The Problem**: Static rule files cost 20%+ more tokens with no measurable improvement in task success ([Gloaguen et al., 2026](https://arxiv.org/abs/2602.11988)). Agents fail on implementation skill, not missing repository knowledge ([arXiv:2607.27250](https://arxiv.org/abs/2607.27250)). More rules = exponentially worse compliance ([Harada et al., 2025](https://arxiv.org/abs/2504.12329)).
>
> **The Organism**: Soma solves this with JIT cell expression — only 2-3 proven rules delivered per change via MCP, ranked by Bayesian fitness, evolving through natural selection. Rules that can't prove themselves die. Rules that prove themselves get promoted. This is Darwinian governance.

See the [NOTICE](NOTICE) file for our full local-only Data Privacy Statement.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  SESSION START                                              │
│  Agent reads 1 meta-rule: "call soma_scan before changes"   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  1. EXPRESS: Agent calls soma_scan via MCP                   │
│     → Reads git diff, matches cells by target_paths          │
│     → Ranks by Bayesian fitness score                        │
│     → Returns top 2-3 cells (configurable budget)            │
│     → ~90% compliance (vs ~57% with 11 rules)                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  2. EXECUTE: Agent works with focused, relevant guidance     │
│     → Only non-standard rules (the only type that helps)     │
│     → Minimal token cost (<5% overhead)                      │
│     → Safety gates, anti-pattern traps, project conventions  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  3. EVALUATE: Automated outcome capture                      │
│     → Test pass/fail signals                                 │
│     → Git revert/rework detection                            │
│     → Agent-reported outcomes (soma_report_outcome)           │
│     → No interactive prompts — fully automated               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  4. EVOLVE: Cell lifecycle runs                              │
│     → Bayesian fitness scoring with telomere decay           │
│     → Tournament selection, crossover, metamorphosis         │
│     → Aggressive pruning — no-signal cells archived          │
│     → Stochastic genesis for diversity injection             │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Install

```bash
# Clone
git clone https://github.com/nseney1/soma.git && cd soma

# Recommended: MCP-first mode (v0.23)
bash install/install.sh gemini --jit

# Classic mode (all genome rules installed)
bash install/install.sh gemini

# Other platforms
bash install/install.sh kiro       # AWS Kiro
bash install/install.sh copilot    # GitHub Copilot
bash install/install.sh claude     # Claude Code
bash install/install.sh mcp        # MCP-only (any agent)

# Project-local install
bash install/install.sh gemini --local --jit
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

Works with Gemini Antigravity, Claude Code, Cursor, and any MCP-compatible agent.

**MCP Tools:**

| Tool | Purpose |
|:-----|:--------|
| `soma_scan` | **Call before making changes.** Returns 2-3 focused governance rules relevant to your current diff, ranked by fitness. |
| `soma_report_outcome` | **Call after completing work.** Reports success/failure for fitness scoring. |
| `soma_create_cell` | Create governance cells from natural language descriptions. |
| `soma_grade` | Returns governance report card with fitness grades. |
| `soma_coverage` | Shows which files are governed by cells. |
| `soma_fitness` | Returns fitness landscape with Bayesian scoring. |
| `soma_list_cells` | Lists all cells with type, hypothesis, and fitness data. |

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

### Onboarding

After installation, open your AI assistant in your project and prompt:

> *Run the genesis organ to inspect this repository and seed governance cells.*

Genesis scans your stack (languages, frameworks, dependencies) and creates tailored `.soma/cells/` in seconds. Domain templates (`templates/`) are auto-detected based on your project type.

---

## Anatomy of the Organism

Soma models your codebase as a living organism. Every component maps to biology:

```text
┌─────────────────────────────────────────────────────────────┐
│  🧬 GENOME (genome/)          5 Active Genes (non-standard) │
│     + 6 archived (standard practices models already know)   │
│  🫀 ORGANS (organs/)          15 Organs — complex skills     │
│  ⚗️  ENZYMES (enzymes/)       42 Enzymes — catalytic scripts │
├─────────────────────────────────────────────────────────────┤
│  🔬 JIT ENGINE (soma_mcp/)  → Just-in-time cell expression  │
│     Express only what's relevant. Budget: 2-3 cells/scan.   │
│  🌲 BIOME (Global)           → Environmental Pressure Levels│
│     Breeze → Gale → Trident → Maelstrom → Tempest           │
│  🍄 FOREST FLOOR             → Analytical Prongs            │
│     Spores → Mycelium → Roots → Thorns → Bedrock → Mulch    │
│  🌱 CELLS (.soma/cells/)     → Adaptive Immune Response     │
│     Vacuoles · Chloroplasts · Walls · Membranes              │
└─────────────────────────────────────────────────────────────┘
```

| Biological Layer | Directory | What It Contains |
|:-----------------|:----------|:-----------------|
| **Genome** | `genome/` | 5 active genes (non-standard practices only) + 6 archived. The organism's DNA. |
| **JIT Engine** | `soma_mcp/` | Just-in-time expression engine. Matches cells to diffs, ranks by fitness, enforces context budget. |
| **Organs** | `organs/` | 15 Organs — complex multi-cell structures. Skills like adaptive-reviewer, genesis, security-audit. |
| **Enzymes** | `enzymes/` | 42 Enzymes — small catalysts. Scripts that drive specific reactions (fitness scoring, cell creation, outcome capture). |
| **Immune System** | `immune_system/` | Mulch queue, immune data. The organism's self-defense memory. |
| **Cells** | `.soma/cells/` | Per-repo adaptive invariants. Generated, tested, evolved, or driven to extinction. |

---

## 🧬 Genome

The organism's DNA — **5 active genes** encoding non-standard practices. Standard practices (testing, documentation, git workflow) are [archived](genome/.archive/) because [research shows](https://arxiv.org/abs/2602.11988) models already know them, and loading them wastes tokens.

### Active Genes

| Gene | Purpose | Why It's Non-Standard |
|:-----|:--------|:---------------------|
| [destructive-ops](genome/destructive-ops.md) | Dry-run mandates for IaC, database mutations, bulk git | Project-specific safety gates |
| [providence](genome/providence.md) | Codebase grounding, no hallucinations, diagnose-before-repair | Attribution tracking models don't do by default |
| [cost-optimization](genome/cost-optimization.md) | Token efficiency, diffs-only edits, FPSR metric (>80%) | Project-specific budget constraints |
| [desktop-automation](genome/desktop-automation.md) | PyAutoGUI/xdotool safety, focus verification | Non-standard automation patterns |
| [subagent-delegation](genome/subagent-delegation.md) | Context protection, concurrency limits, delegation floor | Platform-specific orchestration |

### Archived Genes (in `genome/.archive/`)

These were removed from active context because peer-reviewed research shows they increase token cost by 20%+ with no measurable improvement in task success:

| Gene | Why Archived |
|:-----|:------------|
| testing.md | Models already write tests without being told |
| documentation.md | Models already document without being told |
| git-workflow.md | Models already follow git conventions |
| polyglot-standards.md | Models already follow language conventions |
| architectural-tenets.md | "Repository overviews are not helpful" ([Paper 1](https://arxiv.org/abs/2602.11988)) |
| feature-specs.md | Generic process — not non-standard |

> **Note**: Archived genes aren't deleted. They remain available if a team specifically needs them — they're just not injected into context by default.

---

## 🌱 Cells

Cells are the adaptive immune system — atomic, dynamically generated invariants that live in your repository (`.soma/cells/`). They are delivered **just-in-time** via the `soma_scan` MCP tool based on what files you're actually changing.

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
Generate → Express (JIT) → Score (Outcome Feedback) → Adapt / Crossover → Differentiate → Prune → Promote
   ↑                                                                                                  |
   └──────────────────── Execution Outcomes (tests, git signals, rework detection) ───────────────────┘
```

**Evolutionary operators**: Crossover (merges high-fitness cells), Tournament Selection (diversity-preserving), Differentiation (vacuoles harden into walls), Telomere Shortening (confidence decays unless reinforced), Apoptosis (immediate eviction on excess false positives), Horizontal Gene Transfer (cross-project sharing with probation), Lineage Tracking (phylogenetic provenance).

**Research-grade analysis**: Bayesian Fitness (Beta-Binomial posterior), Quorum Sensing (systemic multi-cell triggers), Coverage Maps, Governance Replay ("would today's cells have caught this bug?"), Counterfactual ROI, Adversarial Testing, Entropy Rate (fossilization detection), Report Card (A+ through F).

**Tiered enforcement**: Cells earn their enforcement tier through demonstrated defect prevention — `advisory` (prompt injection) → `mechanical` (pre-commit block at 85%) → `gate` (runtime assertion at 95%).

### JIT Expression Engine

The `soma_scan` MCP tool implements **just-in-time cell expression** — the core innovation of v0.23:

```python
# What happens when an agent calls soma_scan:

1. Read git diff → ["install/install.sh", "soma_mcp/tools.py"]
2. Match cells by target_paths → 8 of 10 cells match
3. Rank by Bayesian fitness → trap-stale-rename-refs (1.0), persona-cross-platform-qa (0.5), ...
4. Apply context budget → Return top 3 (configurable via SOMA_CONTEXT_BUDGET)
5. Include non-standard genome rules if relevant

# Result: 3 focused rules instead of 11
# Compliance: ~90% (vs ~57% with all rules loaded)
# Token cost: <5% overhead (vs +20% with static dump)
```

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

> **Note**: An **escalation sentinel** runs dynamically to evaluate diff sensitivity and auto-escalate the review mode.

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

## ⚗️ Enzymes

42 catalytic scripts that drive the organism's reactions. See [SCRIPTS.md](docs/SCRIPTS.md) for full documentation.

| Category | Enzymes |
|:---------|:--------|
| **Cell Lifecycle** | `cell_fitness.py`, `cell_selection.sh`, `cell_adapt.py`, `cell_scan.py`, `cell_signal.sh`, `cell_create.sh`, `cell_crossover.py`, `cell_metamorphose.py`, `cell_promote.py`, `cell_transfer.sh`, `cell_enforce.py` |
| **JIT & Feedback** | `jit_engine.py` — JIT cell expression, `outcome_engine.py` — automated fitness signals |
| **Analysis** | `cell_quorum.py`, `cell_coverage.py`, `immune_replay.py`, `immune_trends.py`, `immune_grade.py`, `immune_entropy.py`, `cell_adversarial.py`, `cell_deps.py`, `cell_escaped_defects.py` |
| **AI-Assisted** | `cell_create_nl.py` — NL cell creation via any LLM provider or MCP host delegation |
| **Infrastructure** | `immune_init.sh`, `session_close.sh`, `escalation_sentinel.sh`, `soma_resolve.py`, `safety_gate.sh`, `team_sync.sh`, `metrics_snapshot.sh`, `token_census.py` |

---

## 📚 Research Foundations

Soma v0.23 is designed around peer-reviewed research on context engineering for AI agents:

| Paper | Finding | How Soma Addresses It |
|:------|:--------|:---------------------|
| [**Evaluating AGENTS.md**](https://arxiv.org/abs/2602.11988) (Gloaguen et al., 2026) | Context files don't improve task success; +20% cost. Only non-standard rules help. | Only non-standard genome rules are active. Standard practices archived. |
| [**Do Context Files Help?**](https://arxiv.org/abs/2607.27250) (2026) | Agents fail on implementation skill, not missing repo knowledge. Context doesn't convert near-misses. | JIT expression loads only what's relevant to the current diff, not everything. |
| [**ACE: Agentic Context Engineering**](https://arxiv.org/abs/2510.04618) (2025) | Evolving, curated context improves agents by +10.6%. Uses natural execution feedback. | Cell lifecycle: Generate → Express → Evaluate → Evolve with automated outcome capture. |
| **Curse of Instructions** (Harada et al., 2025) | Compliance decays exponentially: 11 rules → ~57% all-followed. | Context budget of 3 cells → ~90% compliance. |
| **Lost in the Middle** (Liu et al., 2024) | Models ignore rules in the middle of long contexts. | 2-3 rules = no "middle." Every rule gets full attention. |

### What Soma Does That Static Files Don't

| | Static Files (`.cursorrules`, `AGENTS.md`) | **Soma v0.23** |
|:--|:---:|:---:|
| **Delivery** | Dump all rules into system prompt | JIT: 2-3 rules via MCP, matched to current diff |
| **Learns from outcomes** | No | Yes — automated outcome engine + Bayesian fitness |
| **Self-prunes** | No — rules accumulate forever | Yes — telomere decay + aggressive archival |
| **Token cost** | +20% (measured) | <5% overhead |
| **Compliance rate** | ~57% at 11 rules | ~90% at 2-3 rules |
| **Cross-repo learning** | Copy-paste | Horizontal gene transfer with probation |
| **Platform lock-in** | Platform-specific | Any agent via MCP stdio |
| **Evidence base** | "Best practice" (untested) | Peer-reviewed research + empirical fitness data |

---

## Configuration

Copy [`soma.conf.example`](install/soma.conf.example) → `soma.conf` to customize.

| Variable | Default | Description |
|:---------|:--------|:------------|
| `SOMA_PLATFORM` | `gemini` | Target AI platform: `gemini`, `kiro`, `copilot`, `claude`, `mcp` |
| `SOMA_INFERENCE_PROVIDER` | `auto` | LLM provider: `auto`, `gemini`, `anthropic`, `openai`, `prompt-only` |
| `SOMA_CONTEXT_BUDGET` | `3` | Max cells expressed per `soma_scan` call. Research-backed default. |
| `DEFAULT_REVIEW_MODE` | `gale` | Session default review intensity |
| `CELL_TELOMERE_DAYS` | `30` | Days for fitness confidence to halve |
| `CELL_TELOMERE_WALL` | `null` | Walls (invariants) never decay |
| `TEAM_SIZE` | `solo` | Team topology: `solo`, `small`, `team`, `enterprise` |
| `GEMINI_API_KEY` | (none) | Gemini inference (not needed with MCP) |
| `ANTHROPIC_API_KEY` | (none) | Anthropic inference (not needed with MCP) |
| `OPENAI_API_KEY` | (none) | OpenAI-compatible inference (not needed with MCP) |

### Cross-OS Support

| OS | Shell | Command | Install | MCP | Hooks |
|:---|:------|:--------|:-------:|:---:|:-----:|
| **Linux** | Bash | `make install` | ✅ | ✅ | ✅ |
| **macOS** | Zsh / Bash | `make install` | ✅ | ✅ | ✅ |
| **WSL** | Bash | `make install` | ✅ | ✅ | ✅ |
| **Windows (Git Bash)** | Bash | `make install` | ✅ | ✅ | ✅ |
| **Windows (PowerShell)** | PowerShell | `.\install.ps1` | ✅ | ✅ | ❌ |
| **Claude Code** | Bash / PS | `make install-claude` | ✅ | ✅ | ❌ |

### Team Setup

Soma supports team-level governance convergence via shared Git repositories:

```bash
bash enzymes/team_sync.sh push    # Sync local cells + metrics
bash enzymes/team_sync.sh pull    # Pull cells from teammates
```

Configure `TEAM_REPO` and optionally `ORG_REPO` in `soma.conf` for multi-team hierarchies.

---

## Design Principles

1. **Evidence over intuition** — Every gene traces back to observed steps wasted. No gene exists "just in case."
2. **Minimum effective context** — Load the fewest rules that produce measurable improvement. Based on [Gloaguen et al.](https://arxiv.org/abs/2602.11988) and the [Curse of Instructions](https://arxiv.org/abs/2504.12329).
3. **Hypothesis-driven governance** — Every cell carries its own falsifiability criteria. Generated cells must specify what they predict, how to measure it, and when to prune if unvalidated.
4. **Execution feedback, not self-evaluation** — Fitness signals come from test outcomes, git signals, and rework detection — not the agent grading itself.
5. **Just-in-time expression** — Rules are expressed like genes: only when the environment demands them. The genome is the gene pool; the MCP server is the expression mechanism.
6. **Continuous validation** — Governance is a living system. Cells that stop proving themselves face telomere decay and eventual apoptosis.
7. **Independent validation** — Escaped defects from CI, tests, and crashes provide ground truth that breaks the agent-grades-itself loop.

## Phylogeny

Soma has evolved across 23 measured phases, from manually written logic into a self-adapting organism:

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
| 23 | **ACE Pivot** — JIT cell expression, outcome engine, genome archival, research-aligned architecture |

Read [PHYLOGENY.md](docs/PHYLOGENY.md) for the complete evolutionary narrative.

## Documentation

| Document | Description |
|:---------|:------------|
| [**Blog Post**](https://dev.to/nseney1/rules-that-cant-prove-themselves-die-adaptive-governance-for-ai-coding-agents-25bn) | "Rules That Can't Prove Themselves Die" — full introduction |
| [CHANGELOG](docs/CHANGELOG.md) | Release history |
| [PHYLOGENY](docs/PHYLOGENY.md) | Phase-by-phase evolutionary narrative |
| [SCRIPTS](docs/SCRIPTS.md) | Full enzyme catalog (42 scripts) |
| [BENCHMARK](docs/BENCHMARK.md) | Reproducible governance effectiveness protocol |
| [METRICS](docs/METRICS.md) | Empirical measurement methodology |
| [ABSTRACT](docs/ABSTRACT.md) | Research paper abstract |
| [CONTRIBUTING](docs/CONTRIBUTING.md) | Contribution guidelines |
| [Templates](templates/README.md) | Domain-specific cell template packs |

## Next Steps

- 🚀 **Try Soma**: `bash install/install.sh gemini --jit` and run Genesis
- 🔌 **MCP Server**: Add Soma to your agent's MCP config — zero API key needed
- 📦 **Use the SDK**: `pip install soma-steering` or `npm install soma-steering`
- 🔮 **NL Cell Creation**: `cell_create.sh --from-description "your concern here"`
- 📊 **Report Card**: `python3 enzymes/immune_grade.py` for instant governance health
- 🧬 **Explore Templates**: Browse domain packs in [templates/](templates/README.md)
- 📄 **Read the Research**: Review the [Abstract](docs/ABSTRACT.md) and [research foundations](#-research-foundations)
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
