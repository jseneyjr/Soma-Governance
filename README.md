# 🧬 Soma

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue?style=flat-square)](LICENSE)
[![Version](https://img.shields.io/badge/Version-0.25.0-informational?style=flat-square)](docs/CHANGELOG.md)

**Your codebase is a living organism. Soma gives it an immune system that evolves.**

Soma is an adaptive governance framework for AI coding agents. It dynamically enforces repository-specific rules using **Just-in-Time (JIT) context** and **Test-Time Compute (TTC)** via the Model Context Protocol (MCP).

Unlike static context files (`AGENTS.md`, `.cursorrules`) which just hope the agent listens, Soma physically verifies every proposed code change against active rules *before* it touches your disk, drastically reducing costly rework.

---

## 🚀 The Soma Architecture (v0.25)

The new architecture moves away from zero-shot cowboy edits and implements a rigorous **Proposer-Verifier Loop** driven entirely by MCP tools.

### 1. Test-Time Compute (TTC) Intercepts
Instead of editing files directly, agents must use the `soma_propose_change` MCP tool. 
When a change is proposed, the TTC Verifier intercepts it and cross-references the diff against the JIT rules currently active for that file.
- If the diff violates an active constraint (e.g., using a forbidden class component, missing truncation), the Verifier **hard-blocks** the action and returns a specific `REJECTED` error.
- Getting it right the first time is cheaper than cleaning up the rework later.

### 2. "Tempest" Mode (Multi-Organ via MCP)
For catastrophic risk changes (e.g., modifying Core Infrastructure or Auth paths), the `escalation_sentinel` triggers **Tempest Mode**.
- `soma_propose_change` halts execution and requires a Multi-Organ Review.
- The agent is instructed to run specialized MCP audit tools: `soma_audit_security` and `soma_audit_performance`.
- Once the agent verifies the diff against those lenses and fixes any issues, it can submit the change using a `# TEMPEST_OVERRIDE` flag.

### 3. True Fitness Scoring (The Reflector)
Rules that can't prove themselves die. Soma uses an ACE-aligned (Agentic Context Engineering) Reflector:
- **Ground Truth**: The Outcome Engine automatically scores rules based on verifiable execution feedback (e.g., test suite exit codes, build failures, git reverts).
- **TTC True Positives**: Every time the TTC Verifier successfully intercepts and blocks a bad proposal, the rule that caught the error gets its `true_positive` score incremented. Rules earn their keep.

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
| `soma_audit_security` | Specialized Security Organ. Checks for OWASP flaws and secrets. Required during Tempest escalations. |
| `soma_audit_performance`| Specialized Performance Organ. Checks for hot-path inefficiencies. Required during Tempest escalations. |
| `soma_scan` | Returns 2-3 focused governance rules relevant to your current diff, ranked by fitness. |
| `soma_report_outcome` | Reports success/failure for fitness scoring. |
| `soma_create_cell` | Create governance cells from natural language descriptions. |

---

## 🔬 Anatomy of the Organism

Soma models your codebase as biology:

- **🧬 Genome (`genome/`)**: Base invariants and core project safety guidelines.
- **🌱 Cells (`.soma/cells/`)**: Adaptive, dynamic rules (Vacuoles, Chloroplasts, Walls, Membranes). Generated, tested, and evolved based on fitness.
- **🫀 Organs (`organs/`)**: Specialized skill definitions. Exposed via MCP tools for heavy-duty auditing.
- **⚗️ Enzymes (`enzymes/`)**: Catalytic scripts powering the TTC Verifier, Outcome Engine, and Escalation Sentinel.

## 📚 Research Foundations

Soma v0.25 is built on peer-reviewed research for AI agents:
- **TTC & Verification**: Intercepting and verifying changes pre-execution significantly boosts agent reliability without unbounded reasoning loops.
- **Agentic Context Engineering (ACE)**: Evolving, curated context improves agents by +10.6% using natural execution feedback. ([arXiv:2510.04618](https://arxiv.org/abs/2510.04618))
- **Static Files Don't Work**: Dumping rules into `.cursorrules` increases token costs by 20% with zero improvement in task success. ([Gloaguen et al., 2026](https://arxiv.org/abs/2602.11988))

---

## License
Apache 2.0 — Copyright 2026 Nicholas Seney
