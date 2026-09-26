# AI Steering Rules

Battle-tested governance rules and expert persona skills for AI coding assistants.

## Why Use This?

- **Stop AI from guessing** — Rules force the agent to verify claims against your actual codebase before acting
- **Cut token costs ~64%** — Conditional loading, smart subagent delegation, and task hygiene eliminate wasted steps
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
| `providence.md` | always_on | **Highest priority.** Codebase grounding, claim verification, no hallucinations, no silent workarounds, external evidence priority, plan adherence, symbol collision guard, UI grounding gate, desktop automation safety. |
| `cost-optimization.md` | always_on | Token efficiency, subagent model tiering, task hygiene, heavy model concurrency cap. |
| `polyglot-standards.md` | always_on | Unified entrypoints (Makefiles), containerization with carve-outs for scripts/serverless. |
| `subagent-delegation.md` | always_on | Context window protection, parallel execution, coding task boundaries, structured reporting, workspace conflict prevention. |
| `architectural-tenets.md` | model_decision | Pragmatism, trade-off analysis, scale-to-zero, premature abstraction ban, pivot discipline, real-time loop budgets. |
| `feature-specs.md` | model_decision | PRD structure, acceptance criteria, documentation deliverables. |
| `testing.md` | model_decision | Behavioral testing, sad paths, minimal mocking, CLI/script testing, hardware mock mandate. |
| `documentation.md` | model_decision | ADRs, actionable READMEs, Mermaid diagrams, high-signal comments. |
| `destructive-ops.md` | model_decision | Dry-run mandates for IaC, database mutations, and destructive git/filesystem ops. |

**Trigger types:**
- **`always_on`** — Loaded every turn. Non-negotiable governance. (~3,665 tokens)
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
| `providence.md` | ~1,661 |
| `subagent-delegation.md` | ~944 |
| `cost-optimization.md` | ~715 |
| `polyglot-standards.md` | ~345 |
| **Subtotal** | **~3,665** |

**Conditional rules** — only name + description loaded unless activated:

| Rule | Idle Cost | Full Cost (when activated) |
|:-----|:----------|:--------------------------|
| `testing.md` | ~29 | ~739 |
| `architectural-tenets.md` | ~29 | ~612 |
| `feature-specs.md` | ~29 | ~463 |
| `documentation.md` | ~18 | ~439 |
| `destructive-ops.md` | ~25 | ~361 |
| **Subtotal** | **~130** | **~2,614** |

**Skills** — zero cost until auto-activated:

| Skill | Idle Cost | Full Cost (when activated) |
|:------|:----------|:--------------------------|
| `security-audit` | ~62 | ~895 |
| `readme-writer` | ~45 | ~889 |
| `incident-debug` | ~60 | ~847 |
| `code-review` | ~55 | ~820 |
| `refactoring-pilot` | ~65 | ~629 |
| `post-mortem` | ~60 | ~596 |
| `performance-audit` | ~65 | ~496 |
| **Subtotal** | **~412** | **~5,172** |

### Conditional Loading Savings

| Approach | Tokens/Turn |
|:---------|:------------|
| **Naive** — all 9 rules + 7 skills always loaded | ~11,451 |
| **Optimized** — conditional rules + skills idle | ~4,207 |
| **Savings** | **~7,244 tokens/turn (63%)** |

The optimized setup delivers the same governance coverage at 37% of the naive token cost. Conditional rules and skills only expand to full cost on the specific turns where they're relevant.

### Observed Savings (Real Session Post-Mortem)

Based on a 1,339-step coding session before and after optimization:

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

> **The governance rules cost ~4,207 tokens/turn to maintain. A single prevented rework loop saves ~20 steps × ~4,000 tokens/step = ~80,000 tokens. The rules pay for themselves within the first prevented mistake.**

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

This rule set has been through **3 formal review iterations**, a **1,339-step session post-mortem**, a **skills modernization pass**, and **continuous live monitoring** — each performed by independent AI reviewers.

### Compliance Score (tested against a live 1,339-step coding session)

| Dimension | Before | After | Key Fixes |
|:----------|:------:|:-----:|:----------|
| Providence & Governance | 6.5 | 9.5 | External evidence, plan adherence, fail-fast validation, assumption surfacing, UI grounding gate, symbol collision guard, refactoring sweep, data ingestion filter |
| Cost Optimization | 9.5 | 10 | Concurrency cap, tier consolidation, scratch hygiene, bulk media delegation |
| Subagent Delegation | 8.5 | 9.5 | Read-only awareness, workspace conflict prevention, destructive delegation, media triage offload |
| Root Cause Resolution | 9.5 | 9.5 | No changes needed — agent fixed all 6 code review findings |
| Execution Discipline | 6.0 | 9.5 | Phase gates, checkpoint testing, mock-first mandate, venv binding |
| **Overall** | **7.8** | **9.7** | **45 findings fixed across all phases** |

### Review & Improvement History

| Phase | Source | Findings | Fixed | Key Changes |
|:------|:-------|:---------|:------|:------------|
| **Review 1** | Staff cross-rule audit | 7 | 5 | Trade-off clarity, broadened destructive-ops, serverless carve-out, dedup docs, disambiguated `inherit` |
| **Review 2** | Compliance audit (1,042 steps) | 7 | 6 | External evidence priority, YAGNI migration gate, read-only awareness, phase gates, concurrency cap, workspace lock |
| **Review 3** | Third iteration audit | 7 | 6 | Stale frontmatter, fan-out alignment, tier consolidation, destructive delegation, README split, env verification |
| **Post-Mortem** | 1,339-step session analysis | 6 | 6 | UI grounding gate, symbol collision guard, refactoring sweep, mock mandate, venv binding, data ingestion filter |
| **Skills Modernization** | Original 4 skills audit | 10 | 10 | Phased workflows, anti-patterns, output formats, Providence cross-refs, full OWASP checklist |
| **Live Monitor** | Continuous (10-min cycles) | 7 | 7 | Bulk media delegation, scratch hygiene, disjoint file ownership, zombie cleanup, pipefail guard, mock clarity, tracker race fix |
| **Backfill** | f7cf2179 (1,579-step Dwarf Fortress) | 5 | 5 | Desktop automation safety, premature abstraction ban, pivot discipline, delegation floor, real-time loop budgets |
| **Total** | | **49** | **45** | 4 skipped were intentional design decisions |

## Development Post-Mortem

This governance suite was built and refined over a single 642-step session. Here's what the process revealed.

### Process Metrics

| Metric | Value |
|:-------|:------|
| Total development steps | 642 |
| Review iterations | 3 formal + 2 focused |
| Subagents used | 7 (all Flash tier, ~$0.05 total) |
| Findings surfaced | 21 (🔴 6 Critical, 🟡 11 Warning, 🔵 4 Nit) |
| Findings fixed | 17 (4 skipped as intentional design decisions) |
| Git pushes | 14 (should have been ~4 milestone releases) |

### What Worked

- **Flash subagents for reviews**: 6 reviewers at ~$0.05 total saved the main context from 350K+ tokens of file reading
- **Dual reviewer fan-out**: Dispatching a compliance auditor + gap analyst concurrently — each caught findings the other missed
- **Incremental user approval**: Implementation plan → approve → execute prevented over-building

### What We'd Do Differently

| Lesson | Detail |
|:-------|:-------|
| **Design as a system** | Rules were created one-at-a-time, causing cross-rule contradictions (e.g., fan-out vs concurrency cap). Design the dependency graph first. |
| **Define templates before instances** | Original 4 skills were flat checklists. After creating 3 new skills with phased workflows, all 4 originals needed full rewrites. |
| **Add shift-left rules first** | Fail-Fast Validation and Assumption Surfacing are the highest-ROI rules but were created last. They should be in v1. |
| **Batch deployments** | 14 git pushes should have been 4 milestones: Core → Standards → Skills → Final Audit. |

### Optimal Creation Order

If starting from scratch, follow this dependency graph:

```
Tier 1 (Epistemic Foundation)  →  providence.md
Tier 2 (Agent Operating System) →  cost-optimization.md, subagent-delegation.md
Tier 3 (Safety Nets)           →  destructive-ops.md
Tier 4 (Engineering Standards)  →  architectural-tenets.md, polyglot-standards.md, documentation.md, testing.md
Tier 5 (Specialized Workflows)  →  feature-specs.md + Skills (using 4-phase template)
```

### Minimum Viable Governance

For small projects or token-constrained environments, load only 3 files (~2,000 tokens):

1. `providence.md` — grounding, anti-hallucination, no workarounds
2. `subagent-delegation.md` — context protection + cost tiering
3. `destructive-ops.md` — safety net for destructive operations

### ROI

The review process cost ~1M tokens. It permanently prevents ~1,760 wasted steps/month (~14M tokens/month) across active development. **Pays for itself within the first week.**

## License

MIT
