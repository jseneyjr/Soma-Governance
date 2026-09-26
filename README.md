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
| `providence.md` | always_on | **Highest priority.** Codebase grounding, claim verification, no hallucinations, no silent workarounds, external evidence priority, plan adherence. |
| `cost-optimization.md` | always_on | Token efficiency, subagent model tiering, task hygiene, heavy model concurrency cap. |
| `polyglot-standards.md` | always_on | Unified entrypoints (Makefiles), containerization with carve-outs for scripts/serverless. |
| `subagent-delegation.md` | always_on | Context window protection, parallel execution, coding task boundaries, structured reporting, workspace conflict prevention. |
| `architectural-tenets.md` | model_decision | Pragmatism over purity, trade-off analysis, scale-to-zero, artifact existence verification. |
| `feature-specs.md` | model_decision | PRD structure, acceptance criteria, documentation deliverables. |
| `testing.md` | model_decision | Behavioral testing, sad paths, minimal mocking, CLI/script testing. |
| `documentation.md` | model_decision | ADRs, actionable READMEs, Mermaid diagrams, high-signal comments. |
| `destructive-ops.md` | model_decision | Dry-run mandates for IaC, database mutations, and destructive git/filesystem ops. |

**Trigger types:**
- **`always_on`** — Loaded every turn. Non-negotiable governance. (~2,815 tokens)
- **`model_decision`** — Model sees the name/description and loads full content only when relevant. (~15 tokens idle)

### Skills (7 expert personas)

Skills auto-activate based on your task. Zero tokens until invoked.

| Skill | Activates When... |
|:------|:------------------|
| `code-review` | You ask to review or critique code. Staff Engineer persona: architectural flaws, race conditions, SOLID violations. |
| `security-audit` | You ask to check security or audit endpoints. AppSec Engineer persona: OWASP Top 10 baseline. |
| `incident-debug` | You report a crash, hang, or error. SRE persona: reproduce → isolate → diagnose → fix → verify. |
| `readme-writer` | You ask to write or improve a README. Technical Writer persona: scannable structure, copy-pasteable quick-starts. |
| `performance-audit` | You ask to optimize or profile code. Performance Engineer persona: hot-path allocations, O(n²), GC pressure, resource utilization. |
| `post-mortem` | You ask to review a past session or do a retrospective. SRE Facilitator persona: blameless analysis, pattern extraction, actionable recommendations. |
| `refactoring-pilot` | You ask to refactor or restructure 4+ files. Refactoring Specialist persona: Mikado Method, incremental moves, safety nets. |

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
| `providence.md` | ~1,130 |
| `subagent-delegation.md` | ~753 |
| `cost-optimization.md` | ~635 |
| `polyglot-standards.md` | ~295 |
| **Subtotal** | **~2,813** |

**Conditional rules** — only name + description loaded unless activated:

| Rule | Idle Cost | Full Cost (when activated) |
|:-----|:----------|:--------------------------|
| `feature-specs.md` | ~29 | ~463 |
| `testing.md` | ~29 | ~441 |
| `documentation.md` | ~18 | ~414 |
| `destructive-ops.md` | ~25 | ~350 |
| `architectural-tenets.md` | ~29 | ~416 |
| **Subtotal** | **~130** | **~2,084** |

**Skills** — zero cost until auto-activated:

| Skill | Idle Cost | Full Cost (when activated) |
|:------|:----------|:--------------------------|
| `readme-writer` | ~45 | ~689 |
| `refactoring-pilot` | ~65 | ~629 |
| `post-mortem` | ~60 | ~596 |
| `performance-audit` | ~65 | ~496 |
| `incident-debug` | ~60 | ~493 |
| `security-audit` | ~62 | ~417 |
| `code-review` | ~55 | ~376 |
| **Subtotal** | **~412** | **~3,696** |

### Conditional Loading Savings

| Approach | Tokens/Turn |
|:---------|:------------|
| **Naive** — all 9 rules + 7 skills always loaded | ~9,046 |
| **Optimized** — conditional rules + skills idle | ~3,355 |
| **Savings** | **~5,691 tokens/turn (63%)** |

The optimized setup delivers the same governance coverage at 46% of the naive token cost. Conditional rules and skills only expand to full cost on the specific turns where they're relevant.

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

### Accuracy-Driven Savings Over Time

The biggest cost driver in AI coding sessions isn't token consumption — it's **rework loops**. When the agent makes a wrong claim, applies a bad fix, or silently works around a problem, the resulting debug cycle costs far more than getting it right the first time.

**Anatomy of a rework loop** (observed from real session data):

```
Agent claims "fixed" → User tests → Same error → Agent re-investigates → Finds real cause → Applies correct fix
```

Each loop costs **~20–25 steps** of wasted context. From the 611-step session:

| Rework Incident | Steps Wasted | Rule That Prevents It |
|:----------------|:-------------|:----------------------|
| False "NCCL is fixed" claim | ~20 | Providence §1 (Evidence-Based Claims) |
| Silent try/except workaround rejected by user | ~15 | Providence §7 (No Silent Workarounds) |
| Fixed wrong venv, broke again | ~25 | Providence §8 (Environment Verification) |
| Hallucinated files from subagent | ~15 | Subagent §5 (Structured Reporting) |
| 100-step blind retry loop (pytest hang) | ~60 | Incident-debug skill (systematic triage) |

**Compound effect:** Rework loops don't just waste steps — they fill the context window with noise, degrading model accuracy on subsequent turns. This creates a vicious cycle: mistakes → rework → context pollution → more mistakes.

**Projected savings at scale:**

| Timeframe | Without Governance | With Governance | Savings |
|:----------|:-------------------|:----------------|:--------|
| Per incident | ~22 rework steps | ~3 steps (first-time-right) | ~19 steps |
| Per session (~600 steps) | ~5 incidents × 22 = 110 steps | ~1 incident × 22 = 22 steps | ~88 steps |
| Per week (5 sessions) | ~550 wasted steps | ~110 wasted steps | ~440 steps |
| Per month (20 sessions) | ~2,200 wasted steps | ~440 wasted steps | **~1,760 steps** |

> **The governance rules cost ~2,833 tokens/turn to maintain. A single prevented rework loop saves ~20 steps × ~4,000 tokens/step = ~80,000 tokens. The rules pay for themselves within the first prevented mistake.**

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

## Staff Review Scorecard

This rule set has been through **3 iterations of staff-level review**, each performed by independent AI reviewers auditing for contradictions, gaps, and clarity issues.

### Compliance Score (tested against a live 1,042-step coding session)

| Dimension | Score | Notes |
|:----------|:-----:|:------|
| Providence & Governance | 6.5 → 9.0 | Fixed: external evidence priority, plan adherence gates |
| Cost Optimization | 9.5 → 10 | Fixed: concurrency cap, tier consolidation |
| Subagent Delegation | 8.5 → 9.5 | Fixed: read-only awareness, workspace conflict prevention, destructive delegation |
| Root Cause Resolution | 9.5 | No changes needed — agent fixed all 6 code review findings |
| Execution Discipline | 6.0 → 9.0 | Fixed: phase gate enforcement rule added |
| **Overall** | **7.8 → 9.4** | |

### Review Iteration History

| Iteration | Findings | Fixed | Skipped | Key Changes |
|:----------|:---------|:------|:--------|:------------|
| **1** | 7 | 5 | 2 | Trade-off clarification, broadened destructive-ops, serverless carve-out, deduplicated docs, disambiguated `inherit` |
| **2** | 7 | 6 | 1 | External evidence priority, YAGNI migration gate, read-only awareness, phase gates, concurrency cap, workspace lock |
| **3** | 7 | 6 | 1 | Stale frontmatter, fan-out alignment, tier consolidation, destructive delegation, README split, env verification |
| **Total** | **21** | **17** | **4** | 4 skipped were intentional design decisions (severity scales, polyglot trigger) |

## License

MIT
