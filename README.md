# 🧬 Soma

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue?style=flat-square)](LICENSE)
[![Genome](https://img.shields.io/badge/Genome-11_Genes-green?style=flat-square)](#-genome)
[![Organs](https://img.shields.io/badge/Organs-15-purple?style=flat-square)](#-organs)
[![Enzymes](https://img.shields.io/badge/Enzymes-39-red?style=flat-square)](#%EF%B8%8F-enzymes)
[![Version](https://img.shields.io/badge/Version-0.25.0-informational?style=flat-square)](docs/CHANGELOG.md)

**Your codebase is a living organism. Soma gives it an immune system that evolves.**

Soma is an adaptive governance framework for AI coding agents. It dynamically enforces repository-specific rules using **Just-in-Time (JIT) context** and **Test-Time Compute (TTC)** via the Model Context Protocol (MCP). Built on biological natural selection, it ensures AI coding agents remain grounded, efficient, and safe — then gets out of the way.

> **The Problem**: Ungoverned AI coding agents waste 25–56% of tokens in circular rework loops, hallucinated API calls, and broken assumptions. Static rule files (`.cursorrules`, `CLAUDE.md`) help but never adapt.
>
> **The Organism**: Soma reduces waste to under 5% (1.1% best-case). Genes that stop proving themselves die. Genes that keep proving themselves get promoted. This is Darwinian governance.

---

## 🚀 The Soma Architecture (v0.25)

The modern architecture implements a rigorous **Proposer-Verifier Loop** driven entirely by MCP tools to achieve our 95.8%+ First Pass Success Rate (FPSR).

### 1. Test-Time Compute (TTC) Oracles
Instead of editing files directly, agents must use the `soma_propose_change` MCP tool. 
When a change is proposed, the TTC Oracle intercepts it and cross-references the diff against the JIT rules currently active for that file.
- If the diff violates an active constraint (e.g., polyglot standards, architectural tenets), the Oracle **hard-blocks** the action and returns a specific `REJECTED` error.
- Getting it right the first time is cheaper than cleaning up the rework later.

### 2. "Tempest" Mode (Multi-Organ via MCP)
For catastrophic risk changes, the `escalation_sentinel` triggers **Tempest Mode**.
- `soma_propose_change` halts execution and requires a Multi-Organ Review.
- The agent is instructed to run specialized MCP audit tools: `soma_audit_security` and `soma_audit_performance`.
- Once the agent verifies the diff against those lenses, it can submit the change using a `# TEMPEST_OVERRIDE` flag.

### 3. Last Gasp Auto-Escalation
When a governance rule (Cell) begins failing too often, it signals for `APOPTOSIS` (cell death). Instead of instant deletion, it enters the **Last Gasp Queue**. The `escalation_sentinel` triggers a domain-specific Organ to audit the cell's failures. If the Organ proves the cell was right, the repository escalates its review mode, and the cell's fitness is restored.

---

## 🛠️ Quick Start

### Install

```bash
# Clone
git clone https://github.com/nseney1/Soma-Governance.git soma && cd soma

# Install for your platform
bash install/install.sh mcp
```

### Configure MCP Server

Add Soma as an MCP server in your AI agent's config (e.g., Claude Code, Cursor, Gemini). **No API keys needed**.

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

### Core MCP Tools

| Tool | Purpose |
|:-----|:--------|
| `soma_propose_change` | **The Gateway.** Propose file changes here. Triggers TTC Verification before writing. |
| `soma_audit_security` | Specialized Security Organ. Checks for OWASP flaws and secrets. Required during Tempest. |
| `soma_audit_performance`| Specialized Performance Organ. Checks for hot-path inefficiencies. Required during Tempest. |
| `soma_scan` | Returns 2-3 focused governance rules relevant to your current diff, ranked by fitness. |
| `soma_report_outcome` | Reports success/failure for fitness scoring. |
| `soma_create_cell` | Create governance cells from natural language descriptions. |

---

## 🔬 Anatomy of the Organism

Soma models your codebase as biology:

```text
┌─────────────────────────────────────────────────────────────┐
│  🧬 GENOME (genome/.oracles) 11 Genes — TTC hard-blocks    │
│  🫀 ORGANS (organs/)          15 Organs — MCP audit skills  │
│  ⚗️  ENZYMES (enzymes/)       39 Enzymes — TTC Verifiers    │
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
| **Genome** | `genome/.oracles/` | 11 Genes — the organism's DNA. Hidden TTC Oracles like `architectural-tenets` and `subagent-delegation`. |
| **Organs** | `organs/` | 15 Organs — complex multi-cell structures. Skills like `security-audit` exposed as MCP tools. |
| **Enzymes** | `enzymes/` | 39 Enzymes — small catalysts. Scripts that drive TTC validation (`ttc_oracle.py`, `escalation_sentinel.py`). |
| **Immune System** | `immune_system/` | The organism's self-defense memory, last gasp queues, and escaped defect tracking. |
| **Cells** | `.soma/cells/` | Per-repo adaptive invariants. Generated, tested, evolved, or driven to extinction. |

---

## 🛡️ Immune Response (Review Protocol)

When code changes, the organism mounts an immune response. The intensity scales with risk:

| Mode | Triggered By | Best For |
|:-----|:-------------|:---------|
| 🌱 Breeze | `escalation_sentinel` | Known bugs, renames |
| 🌬️ Gale | Standard / Default | Quick reviews |
| 🔱 Trident | `escalation_sentinel` | Features, refactors |
| 🌊 Maelstrom | `escalation_sentinel` | Architecture, security |
| ⛈️ Tempest | Extreme Risk / Overrides | Catastrophic risk |

---

## 📊 Metrics & Performance

Our latest **Dogfeeding Audit** across 9 massive integration sessions yielding over 4,800 steps demonstrated the following real-world capabilities:

- **Baseline FPSR (First Pass Success Rate)**: 95.8% across thousands of tool calls.
- **Peak FPSR**: 97.3% on complex 1,766-step sessions involving experimental codebase expansion.
- **Aggressive Delegation**: Verified ability to safely dispatch **61+ independent subagents** and **55+ background schedule timers** synchronously to fan out broad codebase research without polluting the orchestrator's main context window.
- **Context Overhead**: Maintained near 0-token idle context overhead by successfully hiding foundational rules in `.oracles/` and evaluating them purely via TTC Inference.

---

## 🧬 Phylogeny

Soma has evolved across 25 measured phases, from manually written logic into a self-adapting MCP organism:

| Phases | Theme |
|:-------|:------|
| 1–5 | Prescriptive logic extraction and optimization |
| 6–10 | Multi-lens scaling and autonomous orchestration |
| 11–12 | Full dataset mapping and token census calibration |
| 13 | **Cytogenesis** — Local governance and cell generation |
| 14 | **Natural Selection** — Evolutionary scaling, cross-repo speciation |
| 15 | Team Topology & Clean Uninstaller |
| 16 | Automated Workflows — CI/CD integration |
| 17 | **Evolutionary Computation** — GA operators, telomere decay, metamorphosis |
| 18 | **Research Integration** — Bayesian fitness, quorum sensing, coverage maps |
| 19 | **Platform Grade** — Pre-commit hooks, report card, adversarial testing |
| 20 | **SDK & AI-Assisted** — Python/npm SDKs, NL cell creation |
| 21 | **Tiered Enforcement** — Advisory → mechanical → gate promotion lifecycle |
| 22 | **Soma Rebirth** — Biological naming unification, multi-provider inference |
| 23 | **JIT & MCP Paradigm** — Transition to Model Context Protocol, removing static rules |
| 24 | **Dogfeeding Extinction** — Sweeping audit proving 95.8% FPSR baseline |
| 25 | **TTC Oracles & Last Gasp** — Re-integrating foundational tenets as hidden TTC-gates |

Read [PHYLOGENY.md](docs/PHYLOGENY.md) for the complete evolutionary narrative.

---

## 📚 Research Foundations

Soma is built on peer-reviewed research for AI agents:
- **TTC & Verification**: Intercepting and verifying changes pre-execution significantly boosts agent reliability without unbounded reasoning loops.
- **Agentic Context Engineering (ACE)**: Evolving, curated context improves agents by +10.6% using natural execution feedback. ([arXiv:2510.04618](https://arxiv.org/abs/2510.04618))
- **Static Files Don't Work**: Dumping rules into `.cursorrules` increases token costs by 20% with zero improvement in task success. ([Gloaguen et al., 2026](https://arxiv.org/abs/2602.11988))

---

## License
Apache 2.0 — Copyright 2026 Nicholas Seney
