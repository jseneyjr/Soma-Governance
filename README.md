# Soma

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue?style=flat-square)](LICENSE)
[![Core Rules](https://img.shields.io/badge/Core_Rules-15-green?style=flat-square)](#-core-rules)
[![Agent Skills](https://img.shields.io/badge/Agent_Skills-15-purple?style=flat-square)](#-agent-skills)
[![Automation Scripts](https://img.shields.io/badge/Automation_Scripts-57-red?style=flat-square)](#%EF%B8%8F-automation-scripts)
[![Adaptive Rules](https://img.shields.io/badge/Adaptive_Rules-5_Types-orange?style=flat-square)](#-adaptive-rules)
[![Tests](https://img.shields.io/badge/Tests-1278-brightgreen?style=flat-square)](#testing--ci)
[![Version](https://img.shields.io/badge/Version-0.70-informational?style=flat-square)](docs/CHANGELOG.md)
[![Blog Post](https://img.shields.io/badge/Blog-dev.to-black?style=flat-square&logo=devdotto)](https://dev.to/nseney1/rules-that-cant-prove-themselves-die-adaptive-governance-for-ai-coding-agents-25bn)
[![Blog Post 2](https://img.shields.io/badge/Blog_2-dev.to-black?style=flat-square&logo=devdotto)](https://dev.to/nseney1/your-ai-agents-rules-file-is-a-gentlemans-agreement-heres-what-happens-when-you-make-3df5)

**Governance framework that makes AI coding agents trustworthy.**

Soma makes AI agents trustworthy not by asking them to behave, but by making misbehavior structurally unprofitable. Built on evidence-based selection, adversarial verification, and adaptive rule evolution, it ensures AI coding agents remain grounded, efficient, and safe — then proves it.

> **The Problem**: Ungoverned AI coding agents waste significant portions of tokens in circular rework loops, hallucinated API calls, and broken assumptions. Static rule files (`.cursorrules`, `CLAUDE.md`) help but never adapt, and the agent can simply ignore them.
>
> **The Solution**: Soma reduces waste to under 1.0% in governed sessions while adding only ~4,380 tokens/turn idle overhead. Rules that stop proving themselves expire and are pruned. Rules that keep proving themselves get promoted. Claims that don't match evidence are caught.

> **Internal naming convention**: Soma uses a biological metaphor internally (genome, enzymes, organs, cells) to model rule evolution — see the codebase for details.

See the [NOTICE](NOTICE) file for our full local-only Data Privacy Statement.

---

## Quick Start

### Install

```bash
# Clone
git clone https://github.com/nseney1/Soma-Governance.git && cd Soma-Governance

# Install the CLI (Python 3.9+)
pip install -e .

# Or install from PyPI
pip install soma-governance

# Set up governance (auto-detects your platform)
soma init --yes

# See what's active
soma status
```

<details>
<summary>Alternative install methods</summary>

```bash
# Global install via Makefile (Gemini / Antigravity)
make install

# Shell installer for specific platforms
bash install/install.sh gemini     # Google Gemini
bash install/install.sh copilot    # GitHub Copilot
bash install/install.sh claude     # Claude Code
bash install/install.sh kiro       # AWS Kiro
bash install/install.sh mcp        # Any MCP-compatible agent
```

</details>

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

Works with Gemini Antigravity, Claude Code, Cursor, and any MCP-compatible agent. Tools exposed: `soma_create_cell`, `soma_scan`, `soma_grade`, `soma_coverage`, `soma_fitness`, `soma_list_cells`, `soma_report_outcome`, `soma_propose_change`, `soma_audit_security`, `soma_audit_performance`, `soma_verify_changes`, `soma_checkpoint`.

### SDK

```bash
pip install soma-governance        # Python
npm install soma-governance        # JavaScript / TypeScript
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
const { Governance } = require('soma-governance');
const gov = new Governance('.');
const grade = await gov.grade();
const entropy = await gov.entropy();
```

### Onboarding

After installation, open your AI assistant in your project and prompt:

> *Run the genesis organ to inspect this repository and seed governance cells.*

Genesis scans your stack (languages, frameworks, dependencies) and creates tailored `.soma/cells/` in seconds. Domain templates (`templates/`) are auto-detected based on your project type.

### Natural Language Rule Creation

Create adaptive rules by describing your concern in plain English:

```bash
bash enzymes/cell_create.sh --from-description "PPO clip ratio must stay between 0.1 and 0.3"
```

Works with **any AI provider** — Gemini, Anthropic, OpenAI — or via MCP stdio (zero API key needed when running inside an AI agent). Set `--provider gemini|anthropic|openai|prompt-only` or configure `SOMA_INFERENCE_PROVIDER` in `soma.conf`.

---

## CLI Commands

All governance workflows are available via the `soma` CLI:

| Command | Description |
|:--------|:------------|
| `soma init` | Set up governance — auto-detects platform, installs rules + pre-commit hook |
| `soma genesis` | Scan codebase architecture, generate governance cells |
| `soma status` | Show active rules, cell counts, and fitness stats |
| `soma report` | Session report card with compliance metrics |
| `soma doctor` | System health check — verifies installation integrity |
| `soma verify` | Layer 1 deterministic verification on changed files (`--layer1-only` available) |
| `soma checkpoint` | Deterministic quality checks (`--pre-commit` for git hooks) |
| `soma sync` | Reconcile evidence JSONL with cell frontmatter (`--dry-run`, `--json`) |
| `soma oracle` | Cell health classification — healthy, noisy, expired, unobserved |
| `soma promote` | Evaluate cells for promotion (vacuole → wall → genome). `--force --cell <id>` for manual |
| `soma demote` | Evaluate cells for demotion (high FP rate or dormant). `--force --cell <id>` for manual |

```bash
# Quick quality check before committing
soma checkpoint

# Deterministic verification (Layer 1)
soma verify

# Cell health dashboard
soma oracle --json

# See what cells earned promotion
soma promote --dry-run
```

---

## Architecture

Soma models governance as a layered system of rules, skills, and automation. Every component maps to a specific role:

```text
┌──────────────────────────────────────────────────────────────────────┐
│  📐 CORE RULES (genome/)          15 Rules — inherited defaults      │
│  🔧 AGENT SKILLS (organs/)       15 Skills — complex behaviors       │
│  ⚙️  AUTOMATION (enzymes/)        58 Scripts — task automation        │
├──────────────────────────────────────────────────────────────────────┤
│  🛡️ REVIEW PROTOCOL              Two-Layer Verification              │
│     Layer 1: Deterministic AST tools (ungameable)                    │
│     Layer 2: Adversarial information-partitioned agents              │
├──────────────────────────────────────────────────────────────────────┤
│  🌲 REVIEW INTENSITY (Global) → Environmental Pressure Levels       │
│     Breeze → Gale → Trident → Maelstrom → Tempest → Supercell       │
│  🔍 ANALYTICAL PRONGS         → Multi-Perspective Analysis          │
│     Spores → Mycelium → Roots → Thorns → Bedrock → Mulch            │
│  📋 ADAPTIVE RULES (.soma/cells/) → Per-Repo Governance             │
│     Vacuoles · Chloroplasts · Walls · Membranes · Plasmodesmata      │
└──────────────────────────────────────────────────────────────────────┘
```

| Layer | Directory | What It Contains |
|:------|:----------|:-----------------|
| **Core Rules** | `genome/` | 15 rules — inherited behavioral defaults, rarely changed. |
| **Agent Skills** | `organs/` | 15 skills — complex multi-step behaviors like adaptive-reviewer, genesis, security-audit. |
| **Automation Scripts** | `enzymes/` | 58 scripts — task-specific automation (fitness scoring, rule creation, team sync, evidence pipeline). |
| **Review Protocol** | `immune_system/` | Two-layer verification framework + mulch queue. The system's trust-but-verify layer. |
| **Adaptive Rules** | `.soma/cells/` | Per-repo adaptive invariants. Generated, tested, evolved, or retired. |

---

## 🛡️ Review Protocol — Two-Layer Verification

Soma eliminates the "trust the agent" problem through deterministic tooling and adversarial information asymmetry. Layer 1 executes ungameable AST-based verification (persistence checks, call graph analysis, mutation testing, branch coverage, import guards), while Layer 2 deploys information-partitioned agents evaluated by a deterministic set-algebra arbiter. Execution logs are independently audited via the Transcript Verifier.

For full architectural details and formal mechanism design analysis, see [MECHANISM_DESIGN.md](docs/MECHANISM_DESIGN.md).

---

## 🛡️ Review Protocol (Review Modes)

When code changes, the system mounts a review response. The intensity scales with risk:

### Review Intensity Levels

| Mode | Dispatches | Cost | Best For |
|:-----|:----------:|:----:|:---------|
| 🌱 Breeze | 2 | ~3-4k | Known bugs, renames |
| 🌬️ Gale | 3-4 | ~4k | Quick reviews |
| 🔱 Trident | 5-8 | ~8-12k | Features, refactors |
| 🌊 Maelstrom | 7-12 | ~15-20k | Architecture, security |
| ⛈️ Tempest | 8-12 | ~30-50k | Catastrophic risk |
| 🌪️ Supercell | 8×N | iterative | Pre-release clean ship — adversarial Prosecutor/Defender pairs per prong, iterative until zero findings |

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

## 📐 Core Rules

The system's foundational rules — 15 rules that define inherited behavior. Always-on rules are loaded every session; conditional rules activate on demand.

| Rule | Trigger | Purpose |
|:-----|:--------|:--------|
| [providence](genome/providence.md) | always_on | Codebase grounding, no hallucinations, diagnose-before-repair |
| [cost-optimization](genome/cost-optimization.md) | always_on | Token efficiency, diffs-only edits, FPSR metric (>80%) |
| [subagent-delegation](genome/subagent-delegation.md) | always_on | Context protection, concurrency limits, delegation floor |
| [architectural-tenets](genome/.oracles/architectural-tenets.md) | model_decision | Pragmatism, trade-off analysis, scale-to-zero |
| [polyglot-standards](genome/.oracles/polyglot-standards.md) | model_decision | Unified entrypoints (Makefiles), containerization |
| [feature-specs](genome/.oracles/feature-specs.md) | model_decision | PRD structure, acceptance criteria, documentation |
| [testing](genome/.oracles/testing.md) | model_decision | Behavioral testing, sad paths, ast.parse ban |
| [documentation](genome/.oracles/documentation.md) | model_decision | ADRs, actionable READMEs, Mermaid diagrams |
| [destructive-ops](genome/destructive-ops.md) | model_decision | Dry-run mandates for IaC, database mutations, bulk git |
| [git-workflow](genome/.oracles/git-workflow.md) | model_decision | Conventional commits, .gitignore verification |
| [desktop-automation](genome/desktop-automation.md) | model_decision | PyAutoGUI/xdotool safety, focus verification |
| [core-change-protocol](genome/core-change-protocol.md) | model_decision | Approval gates for genome/enzyme modifications |
| [tdd-protocol](genome/.oracles/tdd-protocol.md) | model_decision | Test-driven development with sequential phase gates |
| [optional-import-guard](genome/.oracles/optional-import-guard.md) | model_decision | try/except guards on optional dependencies |
| [hgt-resource-consolidation](genome/hgt-resource-consolidation-hgt.md) | model_decision | Cross-project rule sharing governance |

---

## 🔧 Agent Skills

Complex multi-step behaviors — each skill performs a specialized function.

| Skill | Purpose |
|:------|:--------|
| [adaptive-reviewer](organs/adaptive-reviewer/SKILL.md) | Auto-escalating review orchestrator with subagent nesting |
| [domain-researcher](organs/domain-researcher/SKILL.md) | Compiles verified external facts (wikis, API docs) |
| [genesis](organs/genesis/SKILL.md) | 5-stage codebase onboarding: Canopy → Rings → Taproot → Lichen → Rule Generation |
| [governance-auditor](organs/governance-auditor/SKILL.md) | Mechanical per-rule PASS/FAIL compliance checks |
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

## 📋 Adaptive Rules

Adaptive rules are the per-repository governance layer — atomic, dynamically generated invariants that live exclusively inside your repository (`.soma/cells/`).

| Rule Type | Role | What It Does |
|:----------|:-----|:-------------|
| **Vacuole** | Anti-pattern trap | Catches known anti-patterns (e.g., "Don't use raw coordinates") |
| **Chloroplast** | Best-practice injector | Injects idiomatic patterns (e.g., "Use async FastAPI conventions") |
| **Cell Wall** | Non-negotiable boundary | Non-negotiable safety gate (e.g., "Never skip GAE truncation") |
| **Membrane** | Selective review trigger | Forces elevated review when sensitive areas change |
| **Plasmodesmata** | Cross-service contract | Governs data shapes and APIs between services |

### Rule Lifecycle

Adaptive rules operate on an evidence-based evolutionary lifecycle:

```text
Generate → Score (Confidence Decay) → Adapt / Crossover → Differentiate → Prune / Retire → Promote
   ↑                                                                                          |
   └──────────────────────── External Fitness Signals (CI/CD, tests, metrics) ────────────────┘
```

**Evolutionary operators**: Crossover (merges high-fitness rules), Tournament Selection (diversity-preserving), Differentiation (vacuoles harden into walls), Confidence Decay (confidence decays unless reinforced), Retirement (immediate eviction on excess false positives), Horizontal Transfer (cross-project sharing with probation), Version History (provenance tracking).

**Research-grade analysis**: Bayesian Fitness (Beta-Binomial posterior with Laplace smoothing), Quorum Sensing (systemic multi-rule triggers), Coverage Maps, Governance Replay ("would today's rules have caught this bug?"), Counterfactual ROI, Adversarial Testing, Entropy Rate (fossilization detection), Report Card (A+ through F).

**Tiered enforcement**: Rules earn their enforcement tier through demonstrated defect prevention — `advisory` (prompt injection) → `mechanical` (pre-commit block at 85%) → `gate` (runtime assertion at 95%). Escaped Defect Tracking from CI/tests/crashes provides ground truth that breaks the self-evaluation loop.

---

## ⚙️ Automation Scripts

Soma includes 87 task-specific scripts driving rule lifecycles, verification, and evidence pipelines. See [SCRIPTS.md](docs/SCRIPTS.md) for full documentation.

---

## Configuration

Copy [`soma.conf.example`](install/soma.conf.example) → `soma.conf` to customize.

| Variable | Default | Description |
|:---------|:--------|:------------|
| `SOMA_PLATFORM` | `gemini` | Target AI platform: `gemini`, `kiro`, `copilot`, `claude`, `mcp` |
| `SOMA_INFERENCE_PROVIDER` | `auto` | LLM provider: `auto`, `gemini`, `anthropic`, `openai`, `prompt-only` |
| `DEFAULT_REVIEW_MODE` | `gale` | Session default review intensity |
| `CELL_TELOMERE_DAYS` | `30` | Days for fitness confidence to halve |
| `CELL_TELOMERE_WALL` | `null` | Walls (invariants) never decay |
| `TEAM_SIZE` | `solo` | Team topology: `solo`, `small`, `team`, `enterprise` |
| `GEMINI_API_KEY` | (none) | Gemini inference (not needed with MCP) |
| `ANTHROPIC_API_KEY` | (none) | Anthropic inference (not needed with MCP) |
| `OPENAI_API_KEY` | (none) | OpenAI-compatible inference (not needed with MCP) |

### Cross-OS Support

| OS | Shell | Install | Uninstall | Core Rules | Agent Skills | Hooks |
|:---|:------|:--------|:----------|:----------:|:------------:|:-----:|
| **Linux** | Bash | `make install` | `bash install/uninstall.sh` | ✅ | ✅ | ✅ |
| **macOS** | Zsh / Bash | `make install` | `bash install/uninstall.sh` | ✅ | ✅ | ✅ |
| **WSL** | Bash | `make install` | `bash install/uninstall.sh` | ✅ | ✅ | ✅ |
| **Windows (Git Bash)** | Bash | `make install` | `bash install/uninstall.sh` | ✅ | ✅ | ✅ |
| **Windows (PowerShell)** | PowerShell | `.\\install.ps1` | `.\\install\\uninstall.ps1` | ✅ | ✅ | ❌ |

### Team Setup

Soma supports team-level governance convergence via shared Git repositories:

```bash
bash enzymes/team_sync.sh push    # Sync local rules + metrics
bash enzymes/team_sync.sh pull    # Pull rules from teammates
```

Configure `TEAM_REPO` and optionally `ORG_REPO` in `soma.conf` for multi-team hierarchies.

---

## How Soma Differs

Soma replaces passive prompt files with active evolutionary governance: JIT context loading prevents bloat, adaptive cells trap repo-specific bugs, and two-layer verification eliminates self-grading.

For academic research analysis and empirical findings, see [ABSTRACT.md](docs/ABSTRACT.md).

---

## Metrics

- **Total System Idle Overhead**: ~4,380 tokens/turn
- **Typical Load** (genome + 3 matched cells): ~4,013 tokens/turn
- **Waste Rate**: < 1.0% in governed sessions (via Last Gasp & TTC Oracles)
- **Calibrated Token Ratio**: 1.35 measured directly against Gemini API
- **Verification Framework**: 1,278 tests across 30+ test files

See [METRICS.md](docs/METRICS.md) for a complete system breakdown. See [BENCHMARK.md](docs/BENCHMARK.md) for the standardized governance effectiveness benchmark.

## Design Principles

Soma is built on empirical grounding, adversarial convergence, continuous validation, and hypothesis-driven governance. See [PHYLOGENY.md](docs/PHYLOGENY.md) for foundational design principles and evolutionary narrative.

## Testing & CI

### Test Suite

```bash
make test       # Full validation + pytest
make validate   # Shell syntax, Python compilation, JSON templates
make doctor     # System health check
```

The test suite contains **1,278 tests** across 30+ test files covering rule validation, Bayesian fitness scoring, AST invariants, and two-layer verification. See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for test guidelines and execution instructions.

### CI/CD Pipeline

GitHub Actions runs on `ubuntu-latest`, `macos-latest`, and `windows-latest`:
- **Linux/macOS**: Shell syntax validation → Python compilation → pytest → hardcoded path audit → script count invariant (≥16) → privacy audit → dry-run install sweep (all 5 platforms)
- **Windows**: PowerShell AST parsing → dry-run install with rule count assertion

## Version History

Soma has evolved across 50 measured phases, from manually written logic into a self-adapting governance framework:

| Phases | Theme |
|:-------|:------|
| 1–5 | Prescriptive logic extraction and optimization |
| 6–10 | Multi-lens scaling and autonomous orchestration |
| 11–12 | Full dataset mapping and token census calibration |
| 13 | **Rule Generation** — Local governance and adaptive rule creation |
| 14 | **Natural Selection** — Evolutionary scaling, cross-repo speciation |
| 15 | Team Topology & Clean Uninstaller |
| 16 | Automated Workflows — CI/CD integration |
| 17 | **Evolutionary Computation** — GA operators, confidence decay, metamorphosis, horizontal transfer |
| 18 | **Research Integration** — Bayesian fitness, quorum sensing, coverage maps |
| 19 | **Platform Grade** — Pre-commit hooks, report card, adversarial testing, entropy rate |
| 20 | **SDK & AI-Assisted** — Python/npm SDKs, NL rule creation, counterfactual ROI |
| 21 | **Tiered Enforcement** — Advisory → mechanical → gate promotion lifecycle |
| 22 | **Soma Rebirth** — Naming unification, subagent scaling |
| 23–25 | **TTC & JIT Context** — Last Gasp, TTC Oracles, zero-waste validation |
| 26–29 | **Perception & Homeostasis** — Interoception, resilience engine, signal coherence |
| 30 | **Two-Layer Verification** — Deterministic tools, adversarial pairing, transcript verification |
| 31–50 | **Evidence-Based Governance** — Evidence pipeline, fitness ledger migration, cell expiry enforcement, oracle checkpoint, test hardening (tautological → behavioral), delegation verification, multi-platform support, 1,278 tests |

Read [PHYLOGENY.md](docs/PHYLOGENY.md) for the complete evolutionary narrative.

## Documentation

| Document | Description |
|:---------|:------------|
| [**Blog Post**](https://dev.to/nseney1/rules-that-cant-prove-themselves-die-adaptive-governance-for-ai-coding-agents-25bn) | "Rules That Can't Prove Themselves Die" — full introduction |
| [CHANGELOG](docs/CHANGELOG.md) | Release history |
| [PHYLOGENY](docs/PHYLOGENY.md) | Phase-by-phase evolutionary narrative |
| [MECHANISM_DESIGN](docs/MECHANISM_DESIGN.md) | Formal mechanism design mapping |
| [SCRIPTS](docs/SCRIPTS.md) | Full automation script catalog (87 scripts) |
| [BENCHMARK](docs/BENCHMARK.md) | Reproducible governance effectiveness protocol |
| [METRICS](docs/METRICS.md) | Empirical measurement methodology |
| [ABSTRACT](docs/ABSTRACT.md) | Research paper abstract |
| [CONTRIBUTING](docs/CONTRIBUTING.md) | Contribution guidelines |
| [Templates](templates/README.md) | Domain-specific rule template packs |

## Next Steps

- 🚀 **Try Soma**: `soma init --yes` and run `soma genesis` on your repository
- 🔌 **MCP Server**: Add Soma to your agent's MCP config — zero API key needed
- 📦 **Use the SDK**: `pip install soma-governance` or `npm install soma-governance`
- 🔮 **NL Rule Creation**: `cell_create.sh --from-description "your concern here"`
- 📊 **Report Card**: `soma report` for instant governance health
- 📐 **Explore Templates**: Browse domain packs in [templates/](templates/README.md)
- 📄 **Read the Research**: Review the [Abstract](docs/ABSTRACT.md) and [Phylogeny](docs/PHYLOGENY.md)
- 🤝 **Contribute**: See [CONTRIBUTING.md](docs/CONTRIBUTING.md)

## Uninstalling

```bash
bash install/uninstall.sh gemini                # Remove Soma files, restore backups
bash install/uninstall.sh gemini --dry-run       # Preview what will be removed
bash install/uninstall.sh gemini --keep-config   # Preserve soma.conf
bash install/uninstall.sh gemini --no-restore    # Skip backup restoration
bash install/uninstall.sh gemini --force         # Skip confirmation prompt
bash install/uninstall.sh gemini --purge-data    # Also remove cells, fitness history
```

On Windows (PowerShell):

```powershell
pwsh install\uninstall.ps1 -Platform gemini
pwsh install\uninstall.ps1 -Platform gemini -DryRun
```

Existing `.prism/` directories are auto-migrated to `.soma/` on install.

## License

Apache 2.0 — Copyright 2026 Nicholas Seney
See [NOTICE](NOTICE) for Data Privacy details.
