# AI Steering Rules

Battle-tested governance rules and expert persona skills for AI coding assistants.

## Why Use This?

- **Stop AI from guessing** — Rules force the agent to verify claims against your actual codebase before acting
- **Cut token costs ~45%** — Conditional loading, smart subagent delegation, and task hygiene eliminate wasted steps
- **Cross-platform** — Works with Gemini/Antigravity (Google), Kiro (AWS), and GitHub Copilot (Microsoft)

## Quick Start

> **Prerequisites:** `git` and one of: [Gemini/Antigravity](https://github.com/google-gemini/antigravity), [Kiro](https://kiro.dev), or [GitHub Copilot](https://github.com/features/copilot)

```bash
git clone https://github.com/nseney1/ai-steering-rules.git
cd ai-steering-rules

# Pick your platform:
./install-gemini.sh     # Gemini / Antigravity
./install-kiro.sh       # Kiro
./install-copilot.sh    # GitHub Copilot (run with 'global' or 'project')
```

Rules take effect on your next conversation turn. No restart needed.

## What's Included

### Rules (9 files)

| Rule | Trigger | Purpose |
|:-----|:--------|:--------|
| `providence.md` | always_on | **Highest priority.** Codebase grounding, claim verification, no hallucinations, no silent workarounds, venv safety. |
| `cost-optimization.md` | always_on | Token efficiency, subagent model tier selection, task hygiene. |
| `polyglot-standards.md` | always_on | Unified entrypoints (Makefiles), containerization with carve-outs for scripts/serverless. |
| `subagent-delegation.md` | always_on | Context window protection, parallel execution, coding task boundaries, structured reporting. |
| `architectural-tenets.md` | model_decision | Pragmatism over purity, explicit trade-off analysis, scale-to-zero preferences. |
| `feature-specs.md` | model_decision | PRD structure, acceptance criteria, documentation deliverables. |
| `testing.md` | model_decision | Behavioral testing, sad paths, minimal mocking, CLI/script testing. |
| `documentation.md` | model_decision | ADRs, actionable READMEs, Mermaid diagrams, high-signal comments. |
| `destructive-ops.md` | model_decision | Dry-run mandates for IaC, database mutations, and destructive git/filesystem ops. |

**Trigger types:**
- **`always_on`** — Loaded every turn. Non-negotiable governance. (~1,200 tokens)
- **`model_decision`** — Model sees the name/description and loads full content only when relevant. (~15 tokens idle)

### Skills (4 expert personas)

Skills auto-activate based on your task. Zero tokens until invoked.

| Skill | Activates When... |
|:------|:------------------|
| `code-review` | You ask to review or critique code. Staff Engineer persona: architectural flaws, race conditions, SOLID violations. |
| `security-audit` | You ask to check security or audit endpoints. AppSec Engineer persona: OWASP Top 10 baseline. |
| `incident-debug` | You report a crash, hang, or error. SRE persona: reproduce → isolate → diagnose → fix → verify. |
| `readme-writer` | You ask to write or improve a README. Technical Writer persona: scannable structure, copy-pasteable quick-starts. |

## Installation Details

### Gemini / Antigravity (Google Cloud)

**Option A: Copy** (simple, manual updates)
```bash
mkdir -p ~/.gemini/config/rules ~/.gemini/config/skills
cp rules/*.md ~/.gemini/config/rules/
cp -r skills/* ~/.gemini/config/skills/
```

**Option B: Symlink** (stays synced with `git pull`)
```bash
ln -sf "$(pwd)/rules" ~/.gemini/config/rules
ln -sf "$(pwd)/skills" ~/.gemini/config/skills
```

### Kiro (AWS)

The install script converts trigger syntax automatically:

| Gemini | Kiro | Behavior |
|:-------|:-----|:---------|
| `trigger: always_on` | `inclusion: always` | Active on every interaction |
| `trigger: model_decision` | `inclusion: manual` | Reference in chat via `#rulename` |

```bash
./install-kiro.sh
```

Activate manual rules by typing `#testing`, `#documentation`, `#feature-specs`, etc.

### GitHub Copilot (Microsoft / Azure)

Copilot doesn't support conditional triggers — all rules are always active.

```bash
# Global — merges all rules into ~/copilot-instructions.md
./install-copilot.sh global

# Per-project — creates .github/instructions/*.instructions.md files
./install-copilot.sh project
```

> **Note:** Ensure "Enable custom instructions" is checked in your IDE's Copilot settings.

## Cost Analysis

### Per-File Token Costs

**Always-on rules** — full content loaded every turn:

| Rule | Tokens/Turn |
|:-----|:------------|
| `providence.md` | ~996 |
| `subagent-delegation.md` | ~633 |
| `cost-optimization.md` | ~557 |
| `polyglot-standards.md` | ~295 |
| **Subtotal** | **~2,481** |

**Conditional rules** — only name + description loaded unless activated:

| Rule | Idle Cost | Full Cost (when activated) |
|:-----|:----------|:--------------------------|
| `feature-specs.md` | ~29 | ~463 |
| `testing.md` | ~29 | ~441 |
| `documentation.md` | ~18 | ~414 |
| `destructive-ops.md` | ~25 | ~350 |
| `architectural-tenets.md` | ~29 | ~318 |
| **Subtotal** | **~130** | **~1,986** |

**Skills** — zero cost until auto-activated:

| Skill | Idle Cost | Full Cost (when activated) |
|:------|:----------|:--------------------------|
| `readme-writer` | ~45 | ~689 |
| `incident-debug` | ~60 | ~469 |
| `security-audit` | ~62 | ~417 |
| `code-review` | ~55 | ~376 |
| **Subtotal** | **~222** | **~1,951** |

### Conditional Loading Savings

| Approach | Tokens/Turn |
|:---------|:------------|
| **Naive** — all 9 rules + 4 skills always loaded | ~6,418 |
| **Optimized** — conditional rules + skills idle | ~2,833 |
| **Savings** | **~3,585 tokens/turn (56%)** |

The optimized setup delivers the same governance coverage at 44% of the naive token cost. Conditional rules and skills only expand to full cost on the specific turns where they're relevant.

### Observed Savings (Real Session Post-Mortem)

Based on a 611-step coding session before and after optimization:

| Metric | Before | After |
|:-------|:-------|:------|
| Wasted steps per session | ~362 (59%) | ~60–90 (est.) |
| Duplicate context tokens/turn | ~400 | 0 |
| Failed subagent steps | ~150 | 0 (model tier fix) |
| Zombie background tasks | 6 concurrent | Capped at 2 |
| False "it's fixed" claims | 3 incidents | Blocked by verification rules |

**Estimated session cost reduction: ~45%**

## Customization

These rules are opinionated. Fork and adjust to your preferences:

| What to Change | File to Edit |
|:---------------|:-------------|
| Token limits, subagent model tiers | `cost-optimization.md` |
| Entrypoint format (Makefile vs Justfile) | `polyglot-standards.md` |
| Infrastructure preferences | `architectural-tenets.md` |
| Priority hierarchy | `providence.md` (declared highest-priority; all others defer) |

## Design Philosophy

1. **Accuracy over speed** — The agent must never sacrifice correctness to save tokens.
2. **Cost-aware** — Minimize token consumption through precise edits, smart delegation, and conditional loading.
3. **Battle-tested** — Every rule was derived from real failure patterns observed in production coding sessions.

## License

MIT
