# Soma

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue?style=flat-square)](LICENSE)
[![Core Rules](https://img.shields.io/badge/Core_Rules-15-green?style=flat-square)](#-core-rules)
[![Agent Skills](https://img.shields.io/badge/Agent_Skills-15-purple?style=flat-square)](#-agent-skills)
[![Automation Scripts](https://img.shields.io/badge/Automation_Scripts-58-red?style=flat-square)](#%EF%B8%8F-automation-scripts)
[![Adaptive Rules](https://img.shields.io/badge/Adaptive_Rules-5_Types-orange?style=flat-square)](#-adaptive-rules)
[![Tests](https://img.shields.io/badge/Tests-925%2B-brightgreen?style=flat-square)](#testing--ci)
[![Version](https://img.shields.io/badge/Version-0.60.0-informational?style=flat-square)](docs/CHANGELOG.md)
[![Blog Post](https://img.shields.io/badge/Blog-dev.to-black?style=flat-square&logo=devdotto)](https://dev.to/nseney1/rules-that-cant-prove-themselves-die-adaptive-governance-for-ai-coding-agents-25bn)
[![Blog Post 2](https://img.shields.io/badge/Blog_2-dev.to-black?style=flat-square&logo=devdotto)](https://dev.to/nseney1/your-ai-agents-rules-file-is-a-gentlemans-agreement-heres-what-happens-when-you-make-3df5)

**Governance framework that makes AI coding agents trustworthy.**

Soma makes AI agents trustworthy not by asking them to behave, but by making misbehavior structurally unprofitable. Built on evidence-based selection, adversarial verification, and incentive-compatible rule evolution, it ensures AI coding agents remain grounded, efficient, and safe — then proves it.

> **The Problem**: Ungoverned AI coding agents waste significant portions of tokens in circular rework loops, hallucinated API calls, and broken assumptions ([arXiv:2602.11988](https://arxiv.org/abs/2602.11988), [arXiv:2607.27250](https://arxiv.org/abs/2607.27250)). Static rule files (`.cursorrules`, `CLAUDE.md`) help but never adapt, and the agent can simply ignore them.
>
> **The Solution**: Soma reduces waste to under 1.0% in governed sessions while adding only ~3,800 idle context tokens (measured at v0.50 baseline, stabilized via JIT Context — down 8.6% from Phase 11 baseline despite adding 7 new enzymes). Rules that stop proving themselves expire and are pruned. Rules that keep proving themselves get promoted. Claims that don't match evidence are caught. This is incentive-compatible governance.

> **Internal naming convention**: Soma uses a biological metaphor internally (genome, enzymes, organs, cells) to model rule evolution — see the codebase for details.

See the [NOTICE](NOTICE) file for our full local-only Data Privacy Statement.

---

## Quick Start

### Install

```bash
# Clone
git clone https://github.com/nseney1/Soma-Governance.git && cd Soma-Governance

# Install the CLI
pip install -e .

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
const { Governance } = require('soma-steering');
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
| `soma status` | Show active rules, cell counts, and fitness stats |
| `soma report` | Session report card with compliance metrics |
| `soma doctor` | System health check — verifies installation integrity |
| `soma verify` | Two-layer verification on changed files (`--layer1-only` for fast mode) |
| `soma checkpoint` | Deterministic quality checks (`--pre-commit` for git hooks) |
| `soma oracle` | Cell health classification — healthy, noisy, expired, unobserved |
| `soma promote` | Evaluate cells for promotion (vacuole → wall → genome). `--force --cell <id>` for manual |
| `soma demote` | Evaluate cells for demotion (high FP rate or dormant). `--force --cell <id>` for manual |

```bash
# Quick quality check before committing
soma checkpoint

# Full verification (Layer 1 + Layer 2)
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

Soma's two-layer verification framework eliminates the "trust the agent" problem through deterministic tooling and adversarial information asymmetry.

### Layer 1: Deterministic Tools (Ungameable)

AST-based analysis tools that produce objective evidence — no LLM judgment involved:

| Tool | What It Catches |
|:-----|:----------------|
| `persistence_checker` | Dict mutations missing serialization (the exact bug class that caused v0.30's epoch persistence gap) |
| `call_graph` | Orphan/dead functions defined but never called |
| `mutation_tester` | Tautological tests that pass regardless of code mutations |
| `branch_coverage` | Uncovered branches via `pytest-cov` / stdlib `trace` fallback |
| `import_guard` | Unguarded third-party imports that crash CI (born from its own CI failure) |

All tools return `ToolEvidence` with a boolean verdict — the `runner.py` orchestrator produces a combined gate verdict.

### Layer 2: Adversarial Information-Partitioned Agents

Two agents review the same change but see **different information**:

```text
┌─────────────────┐     ┌──────────────────┐
│   SPEC AGENT    │     │   CODE AGENT     │
│ Sees: task spec │     │ Sees: code + tests│
│ Predicts: risks │     │ Claims: what holds│
└────────┬────────┘     └────────┬─────────┘
         │                       │
         └───────┐   ┌──────────┘
                 ▼   ▼
         ┌───────────────┐
         │    ARBITER     │
         │ (Set Algebra)  │
         │ 14 Risk Cats   │
         │ SHIP/BLOCK/    │
         │ REVISE         │
         └───────────────┘
```

- **No collusion**: Agents can't agree on answers because they don't see the same inputs.
- **Deterministic arbiter**: Uses pure set intersection/difference over a fixed 14-category risk taxonomy — no LLM in the arbitration loop.
- **Verdicts**: `SHIP` (convergence), `BLOCK` (critical divergence), `REVISE` (non-critical divergence).

### Transcript Verifier

Independently verifies subagent self-reported claims against JSONL transcript evidence:

```python
from immune_system.verification.transcript_verifier import extract_metrics, verify_claim

metrics = extract_metrics("path/to/transcript.jsonl")
result = verify_claim(metrics, claimed_first_pass=True, claimed_tests_passed=45, agent_role="coder")
# → ToolEvidence(verdict=False, detail="Agent claimed first-pass but transcript shows 3 fix cycles")
```

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

58 task-specific scripts that drive the system's operations. See [SCRIPTS.md](docs/SCRIPTS.md) for full documentation.

| Category | Scripts |
|:---------|:--------|
| **Rule Lifecycle** | `cell_fitness.py`, `cell_selection.sh`, `cell_adapt.py`, `cell_scan.py`, `cell_signal.sh`, `cell_create.sh`, `cell_create_nl.py`, `cell_crossover.py`, `cell_metamorphose.py`, `cell_promote.py`, `cell_demote.py`, `cell_transfer.sh`, `cell_enforce.py`, `cell_tournament.py` |
| **Analysis** | `cell_quorum.py`, `cell_coverage.py`, `immune_replay.py`, `immune_trends.py`, `immune_grade.py`, `immune_entropy.py`, `cell_adversarial.py`, `cell_deps.py`, `cell_escaped_defects.py`, `fitness_landscape.py`, `bayesian_score.py` |
| **Perception & Homeostasis** | `soma_interoception.py`, `resilience_engine.py`, `soma_coherence.py`, `outcome_engine.py` |
| **AI-Assisted** | `cell_create_nl.py` — NL rule creation via any LLM provider or MCP host delegation |
| **Infrastructure** | `immune_init.sh`, `session_close.sh`, `escalation_sentinel.sh`, `escalation_sentinel.py`, `soma_resolve.py`, `safety_gate.sh`, `liveness_sentinel.sh`, `team_sync.sh`, `metrics_snapshot.sh`, `token_census.py`, `sweep_session.py` |
| **Orchestration** | `soma_cli.py`, `soma_run.py`, `soma_sleep.py`, `hgt_ribosome.py`, `ttc_oracle.py`, `ttc_verifier.py`, `inference_provider.py` |
| **Evidence Pipeline** | `fitness_updater.py`, `cell_expiry.py`, `oracle_checkpoint.py`, `evidence_collector.py`, `post_session_hook.sh` |

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

Recent academic studies ([arXiv:2602.11988](https://arxiv.org/abs/2602.11988), [arXiv:2607.27250](https://arxiv.org/abs/2607.27250), [arXiv:2510.04618](https://arxiv.org/abs/2510.04618)) have exposed the critical flaws in standard agentic coding tools and static context files (like `AGENTS.md` or `CLAUDE.md`). Soma was explicitly architected to solve the fatal traps identified in this research:

### 1. The Context Bloat Trap
**The Research**: Injecting massive repository overviews into the context window does not improve task success, increases inference costs by over 20%, and leads to "brevity bias" or "context collapse" as the agent loses track of details over time.
**Soma's Solution**: **JIT (Just-In-Time) Context Loading**. Soma does not load a monolithic rulebook. It only loads the specific adaptive rules related to the exact files the agent is currently touching. This keeps the token overhead at a flat ~4,380 idle tokens (3.4%), preventing context collapse.

### 2. The Generic Advice Trap
**The Research**: Context files are largely ignored by LLMs when they contain standard coding practices (which the models already know), and are only useful for "non-standard coding practices" or exact wiring/architectural quirks.
**Soma's Solution**: **Repository-Specific Traps**. Soma's adaptive rules (Vacuoles, Chloroplasts) don't exist to tell the LLM to "write clean code." They exist exclusively to map traps the base model couldn't possibly know zero-shot (e.g., "The HUD calibration in the renderer is offset by 4px"). If a rule can't prove it caught a specific defect, it is pruned.

### 3. The "Self-Grading" Trap
**The Critique**: If an AI agent generates rules and then grades its own rules, isn't that just memory with extra steps? How do we know the rules are working, and it's not just the underlying foundation models getting better?
**Soma's Solution**: **Two-Layer Verification**. Layer 1 uses deterministic AST tools (mutation testing, call graph analysis, branch coverage, import guards) that produce objective evidence no LLM can game. Layer 2 uses adversarial information-partitioned agents — a Spec Agent and Code Agent that can't collude because they see different inputs — with a deterministic set-algebra Arbiter. The Transcript Verifier independently checks subagent claims against actual execution logs. Additionally, Escaped Defect Tracking hooks into CI/CD exit codes to establish ground truth.

| Feature | Standard AI Agents | Prompt Files (`.cursorrules`) | **Soma (v0.60)** |
|:--|:---:|:---:|:---:|
| **Rule Enforcement** | Relies on LLM obedience | Relies on LLM obedience | **Mechanistic rejection via TTC Oracles** |
| **Verification** | Self-grading | None | **Two-layer: deterministic tools + adversarial agents** |
| **Context Management** | Pollutes main thread | Fixed 20%+ overhead | **JIT Context Loading (~3,800 tokens idle)** |
| **Adaptability** | Static training | Manual updates | **Self-evolving via evidence-based fitness** |
| **Ground Truth** | N/A | N/A | **Escaped Defect Tracking + Evidence Pipeline** |
| **Failure modes caught** | Syntax errors | Generic guidelines | **Rework loops, lazy reads, and hallucinations** |
| **Rule Staleness** | Rules never expire | Rules never expire | **Time + session-based expiry enforcement** |
| **Platform lock-in** | Vendor specific | Platform specific | **Universal via MCP stdio** |

Instead of pleading with the AI in a system prompt to "think step-by-step," Soma acts as an evolutionary governance system. **Rules that can't prove themselves die. Agents that refuse to research are blocked. Claims that don't match the tape are caught.**

---

## Metrics

- **Total System Idle Overhead**: ~3,800 tokens/turn (measured at v0.50 baseline — down 8.6% from Phase 11 despite 7 new enzymes)
- **Typical Load** (genome + 3 matched cells): ~4,013 tokens/turn
- **Waste Rate**: < 1.0% in governed sessions (via Last Gasp & TTC Oracles)
- **Calibrated Token Ratio**: 1.35 measured directly against Gemini API
- **Verification Framework**: 925+ tests across 30+ test files

See [METRICS.md](docs/METRICS.md) for a complete system breakdown. See [BENCHMARK.md](docs/BENCHMARK.md) for the standardized governance effectiveness benchmark.

## Design Principles

1. **Evidence over intuition** — Every rule traces back to observed steps wasted. No rule exists "just in case."
2. **Accuracy over speed** — The agent must never sacrifice correctness to save tokens.
3. **Convergence as verification** — Independent agents with asymmetric information arriving at the same conclusion is stronger evidence than any single agent's assessment.
4. **Rules as a system** — Cross-references between rules are intentional. Providence §3 mandates read-before-write; refactoring-pilot operationalizes it as a phased workflow.
5. **Continuous validation** — Governance is a living system that evolves with each session. TTC Oracles validate actions before they waste context.
6. **Installation completeness** — Governance installed at partial fidelity provides false assurance. Every installer path must deploy core rules, agent skills, and hooks with the same completeness.
7. **Hypothesis-driven governance** — Every extension must carry its own falsifiability criteria. Generated rules (Chloroplasts, Vacuoles) must specify what they predict, how to measure it, and when to prune if unvalidated. The scientific method is not just how we evolve the system — it IS the system.
8. **Independent validation** — Self-evaluated fitness is necessary but not sufficient. Escaped defects from CI, tests, and crashes provide the ground truth that breaks the agent-grades-itself loop.

## Testing & CI

### Test Suite

```bash
make test       # Full validation + pytest
make validate   # Shell syntax, Python compilation, JSON templates
make doctor     # System health check
```

**515+ tests** across 20 test files covering:

| Suite | Tests | Coverage |
|:------|:-----:|:---------|
| Rule content validation | ~40 | Behavioral content checks, parser agreement |
| Rule metadata validation | ~30 | Frontmatter schema, required fields, type constraints |
| Fitness updater | 26 | Evidence aggregation, platform detection, transcript parsing |
| Static invariants | 23 | AST checks, encoding, backup naming, zero-dep MCP |
| Import guard | 21 | Third-party import detection, stdlib classification |
| Bayesian fitness | 19 | Laplace scoring, monotonicity, wall budgets, JIT stats |
| Critical fixes | 17 | Shared scoring, status classification, decay idempotency |
| Transcript verifier | 13 | Metric extraction from JSONL, claim verification |
| Arbiter | 12 | Set operations on risk taxonomy, convergence/divergence |
| Immune verify | 12 | Information-partitioned prompts, schema validation |
| Install lifecycle | 15 | Multi-platform install/uninstall, manifest integrity, starter pack |
| Layer 1 runner | 11 | Orchestration, persistence gaps, orphan detection, gates |
| Evidence collector | 10 | Rule compliance correlation, read-before-write detection |
| Exponential decay | 10 | Mathematical properties, champion displacement |
| Cell expiry | 8 | Day/session expiry, wall protection, prune mode |
| Oracle checkpoint | 7 | Cell classification, recommendations, evidence pipeline |
| Mutation tester | 6 | AST mutation generation, survival detection |
| Branch coverage | 4 | Trace/pytest-cov branch coverage |
| Decay integration | 4 | End-to-end decay across on-disk YAML |
| Local promotion | 2 | Promotion path applies decay before scoring |

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
| 31–50 | **Incentive-Compatible Governance** — Evidence pipeline, fitness ledger migration, cell expiry enforcement, oracle checkpoint, test hardening (tautological → behavioral), delegation verification, multi-platform support, 515+ tests |

Read [PHYLOGENY.md](docs/PHYLOGENY.md) for the complete evolutionary narrative.

## Documentation

| Document | Description |
|:---------|:------------|
| [**Blog Post**](https://dev.to/nseney1/rules-that-cant-prove-themselves-die-adaptive-governance-for-ai-coding-agents-25bn) | "Rules That Can't Prove Themselves Die" — full introduction |
| [CHANGELOG](docs/CHANGELOG.md) | Release history |
| [PHYLOGENY](docs/PHYLOGENY.md) | Phase-by-phase evolutionary narrative |
| [SCRIPTS](docs/SCRIPTS.md) | Full automation script catalog (51 scripts) |
| [BENCHMARK](docs/BENCHMARK.md) | Reproducible governance effectiveness protocol |
| [METRICS](docs/METRICS.md) | Empirical measurement methodology |
| [ABSTRACT](docs/ABSTRACT.md) | Research paper abstract |
| [CONTRIBUTING](docs/CONTRIBUTING.md) | Contribution guidelines |
| [Templates](templates/README.md) | Domain-specific rule template packs |

## Next Steps

- 🚀 **Try Soma**: `make install` and run Genesis on your repository
- 🔌 **MCP Server**: Add Soma to your agent's MCP config — zero API key needed
- 📦 **Use the SDK**: `pip install soma-steering` or `npm install soma-steering`
- 🔮 **NL Rule Creation**: `cell_create.sh --from-description "your concern here"`
- 📊 **Report Card**: `python3 enzymes/immune_grade.py` for instant governance health
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
