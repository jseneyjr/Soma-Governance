# 🔮 Prism AI Steering

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue?style=flat-square)](LICENSE)
[![Rules](https://img.shields.io/badge/Rules-11-green?style=flat-square)](#rules)
[![Skills](https://img.shields.io/badge/Skills-15-purple?style=flat-square)](#skills)
[![Review Modes](https://img.shields.io/badge/Review_Modes-5-orange?style=flat-square)](#review-protocols)
[![Phases](https://img.shields.io/badge/Phases-14-blue?style=flat-square)](docs/EVOLUTION.md)
[![Platforms](https://img.shields.io/badge/Gemini_%7C_Kiro_%7C_Copilot-black?style=flat-square)](#quick-start)

> **7,015+** steps analyzed · **~65%** token savings · **80%** fewer false positives · **5** review modes · **6** prongs

Battle-tested governance rules for AI coding assistants — forged from 17+ real sessions and validated across 66 production sessions. Enforced via lifecycle hooks.

## Quick Start

> **Prerequisites:** `git`, and one of: [Gemini/Antigravity](https://github.com/google-gemini/antigravity), [Kiro](https://kiro.dev), or [GitHub Copilot](https://github.com/features/copilot)

```bash
git clone https://github.com/nseney1/prism-ai-steering.git
cd prism-ai-steering
cp steering.conf.example steering.conf   # Optional: customize for your team

# Linux, macOS, WSL, Windows (Git Bash):
make install                              # Gemini / Antigravity (default)
# make install-kiro                       # Kiro alternative
# make install-copilot                    # GitHub Copilot alternative

# Windows (Native PowerShell):
.\install.ps1                             # Rules + skills only (hooks require bash)
```

Rules take effect on your next conversation turn. No restart needed.

### Cross-OS Support Matrix

| OS / Environment | Shell | Command | Rules | Skills | Hooks | Notes |
|:-----------------|:------|:--------|:-----:|:------:|:-----:|:------|
| **Linux** | Bash | `make install` or `bash install.sh` | ✅ | ✅ | ✅ | Full support |
| **macOS** | Zsh / Bash | `make install` or `bash install.sh` | ✅ | ✅ | ✅ | Full support |
| **WSL** | Bash | `make install` or `bash install.sh` | ✅ | ✅ | ✅ | Auto-resolves Windows user profile |
| **Windows (Git Bash)** | Bash | `make install` or `bash install.sh` | ✅ | ✅ | ✅ | Full support via bash runtime |
| **Windows (PowerShell)** | PowerShell | `.\install.ps1` or `make install-windows` | ✅ | ✅ | ❌ | Rules + skills only; hooks require bash |

> [!NOTE]
> **Windows Hook Limitations**: Native PowerShell deploys rules and skills only. Hook scripts (`governance_init.sh`, `safety_gate.sh`, `session_close.sh`) require bash (Git Bash, WSL, or MSYS2).

## How It Works

```mermaid
flowchart LR
    subgraph SLC ["Session Lifecycle"]
        A[User Prompt] --> B{PreInvocation}
        B --> C[Agent Processing]
        C --> D{PreToolUse}
        D -->|Safe| E[Tool Execution]
        D -->|Dangerous| F[BLOCKED]
        E --> G[Response]
    end
    subgraph AA ["Always Active"]
        H["providence.md"] -.-> B
        I["cost-optimization.md"] -.-> B
        J["subagent-delegation.md"] -.-> B
    end
```

**Text fallback:** Every user prompt passes through a PreInvocation hook that injects always-on governance rules. Each tool call is screened by a PreToolUse safety gate — dangerous operations (e.g., `rm -rf /`, `git push -f`) are blocked automatically.

## 📜 Rules

| Rule | Trigger | Purpose |
|:-----|:--------|:--------|
| [providence.md](rules/providence.md) | always_on | **Highest priority.** Codebase grounding, claim verification, no hallucinations, diagnose-before-repair. |
| [cost-optimization.md](rules/cost-optimization.md) | always_on | Token efficiency, diffs-only edits, model tiering, FPSR metric (>80%). |
| [subagent-delegation.md](rules/subagent-delegation.md) | always_on | Context protection, concurrency limits (4 readers / 3 writers), delegation floor. |
| [architectural-tenets.md](rules/architectural-tenets.md) | model_decision | Pragmatism, trade-off analysis, scale-to-zero. |
| [polyglot-standards.md](rules/polyglot-standards.md) | model_decision | Unified entrypoints (Makefiles), containerization. |
| [feature-specs.md](rules/feature-specs.md) | model_decision | PRD structure, acceptance criteria, documentation. |
| [testing.md](rules/testing.md) | model_decision | Behavioral testing, sad paths, ast.parse ban. |
| [documentation.md](rules/documentation.md) | model_decision | ADRs, actionable READMEs, Mermaid diagrams. |
| [destructive-ops.md](rules/destructive-ops.md) | model_decision | Dry-run mandates for IaC, database mutations, bulk git. |
| [git-workflow.md](rules/git-workflow.md) | model_decision | Conventional commits, .gitignore verification, pre-push test gate. |
| [desktop-automation.md](rules/desktop-automation.md) | model_decision | PyAutoGUI/xdotool safety: focus verification, coordinate clamping. |

> [!TIP]
> `always_on` rules load every turn. Total measured system idle overhead is 4,378 tokens/turn (rules + skills). `model_decision` rules load full content only when relevant. See [METRICS.md](docs/METRICS.md) for per-file token costs.

## 🧠 Skills

| Skill | Purpose |
|:------|:--------|
| [adaptive-reviewer](skills/adaptive-reviewer/SKILL.md) | 🔬 Auto-escalating review orchestrator with subagent nesting (E11 — TESTING). |
| [domain-researcher](skills/domain-researcher/SKILL.md) | Compiles verified external facts (wikis, API docs, papers). |
| [genesis](skills/genesis/SKILL.md) | 4-stage codebase onboarding: Canopy → Rings → Taproot → Lichen. |
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
| [visual-analyst](skills/visual-analyst/SKILL.md) | Screen & UI analysis: game state, coordinates, regressions. |

## 🔍 Review Protocols

| Mode | Dispatches | Cost | Best For |
|:-----|:----------:|:----:|:---------|
| 🌱 Breeze | 2 | ~3-4k | Known bugs, renames |
| 🌬️ Gale | 3-4 | ~4k | Quick reviews |
| 🔱 Trident | 5-8 | ~8-12k | Features, refactors |
| 🌊 Maelstrom | 7-12 | ~15-20k | Architecture, security |
| ⛈️ Tempest | 8-12 | ~30-50k | Catastrophic risk |

> [!NOTE]
> Reviews use a biological naming hierarchy (Biome → Forest Floor → Cell) with 6 prongs: 🍄 Spores (width), 🍄 Mycelium (blast radius), 🌿 Roots (depth), 🌹 Thorns (adversarial), 🪨 Bedrock (verification gate), 🍂 Mulch (learning). See [staff-review SKILL.md](skills/staff-review/SKILL.md) for full prong details and escalation paths.

## Configuration

Copy [`steering.conf.example`](steering.conf.example) → `steering.conf` to customize platform, team size, git strategy, and approval chains.

```bash
make info     # Show current configuration
make doctor   # Verify installation health
```

> [!IMPORTANT]
> Run `make doctor` after installation to verify symlinks, hook registration, rule loading, and skill deployment.

<details>
<summary>Advanced Installation & Options</summary>

### Dry-Run Mode
Preview changes without copying or modifying any files:
```bash
bash install.sh --dry-run
# Windows PowerShell:
.\install.ps1 -DryRun
```

### Symlink Method (Gemini / Linux & macOS)

```bash
ln -sf "$(pwd)/rules" "$HOME/.gemini/config/rules"
ln -sf "$(pwd)/skills" "$HOME/.gemini/config/skills"
```

### Kiro

```bash
make install-kiro
# Windows PowerShell:
.\install.ps1 -Platform kiro
```

Activate manual rules by typing `#testing`, `#documentation`, `#feature-specs`, etc.

### GitHub Copilot

```bash
make install-copilot MODE=global    # Merges all rules into ~/copilot-instructions.md
make install-copilot MODE=project   # Creates .github/instructions/*.instructions.md
# Windows PowerShell:
# .\install.ps1 -Platform copilot -Mode global
# .\install.ps1 -Platform copilot -Mode project
```

Ensure "Enable custom instructions" is checked in your IDE's Copilot settings.

</details>

## Deep Dives

| Document | Contents |
|:---------|:---------|
| [Metrics & Token Economics](docs/METRICS.md) | Per-file token costs, compliance scores, waste analysis, ROI calculations |
| [Evolution](docs/EVOLUTION.md) | How the approach evolved across 14 phases, from prescriptive to autonomous orchestration, dataset analysis, and adaptive governance |
| [Experiments](docs/EXPERIMENTS.md) | A/B testing framework (E1–E22) for data-driven governance evolution |
| [Work Sessions Postmortem](docs/postmortem-work-sessions.md) | Comparative analysis of 66 production sessions vs. 17 governed development sessions |

## License

Apache 2.0 — Copyright 2026 Nicholas Seney

> See the [NOTICE](NOTICE) file for our full local-only Data Privacy Statement.
