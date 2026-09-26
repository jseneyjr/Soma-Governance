# Cost Analysis

Detailed token costs, conditional loading savings, and ROI calculations for the AI Steering Rules governance system.

## Per-File Token Costs

**Always-on rules** — full content loaded every turn:

| Rule | Tokens/Turn |
|:-----|:------------|
| `providence.md` | ~1,661 |
| `subagent-delegation.md` | ~944 |
| `cost-optimization.md` | ~475 |
| **Subtotal** | **~3,080** |

**Conditional rules** — only name + description loaded unless activated:

| Rule | Idle Cost | Full Cost (when activated) |
|:-----|:----------|:--------------------------|
| `testing.md` | ~29 | ~739 |
| `architectural-tenets.md` | ~29 | ~612 |
| `git-workflow.md` | ~25 | ~527 |
| `feature-specs.md` | ~29 | ~463 |
| `documentation.md` | ~18 | ~439 |
| `destructive-ops.md` | ~25 | ~361 |
| `polyglot-standards.md` | ~25 | ~345 |
| **Subtotal** | **~180** | **~3,486** |

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
| `staff-review` | ~55 | ~480 |
| **Subtotal** | **~467** | **~5,652** |

## Conditional Loading Savings

| Approach | Tokens/Turn |
|:---------|:------------|
| **Naive** — all 10 rules + 8 skills always loaded | ~12,218 |
| **Optimized** — conditional rules + skills idle | ~3,727 |
| **Savings** | **~8,491 tokens/turn (69%)** |

> **Methodology note**: The 69% figure pools rules and skills. Rules-only savings (excluding skills, which are natively deferred by the platform) = **~47%**. Both numbers are valid; the distinction matters for comparing against other governance systems.

## Observed Savings (Real Session Data)

Based on 8 sessions (5,361 steps) with waste classification:

| Metric | Before Rules | After Rules |
|:-------|:-------------|:------------|
| Waste rate | ~56% (1,339-step session) | ~7-10% (post-optimization) |
| Rework loops per session | ~5 incidents | ~1 incident |
| Failed subagent steps | ~150 per session | ~0 (model tier fix) |
| Zombie background tasks | 6+ concurrent | Capped at 2 |

## Accuracy-Driven Savings Over Time

The biggest cost driver isn't token consumption — it's **rework loops**:

```
Agent claims "fixed" → User tests → Same error → Agent re-investigates → Finds real cause → Applies correct fix
```

Each loop costs **~20–25 steps** of wasted context.

**Compound effect:** Rework loops fill the context window with noise, degrading model accuracy on subsequent turns. This creates a vicious cycle: mistakes → rework → context pollution → more mistakes.

**Projected savings at scale:**

| Timeframe | Without Governance | With Governance | Savings |
|:----------|:-------------------|:----------------|:--------|
| Per incident | ~22 rework steps | ~3 steps (first-time-right) | ~19 steps |
| Per session (~600 steps) | ~5 incidents × 22 = 110 steps | ~1 incident × 22 = 22 steps | ~88 steps |
| Per month (20 sessions) | ~2,200 wasted steps | ~440 wasted steps | **~1,760 steps** |

> The governance rules cost ~3,727 tokens/turn to maintain. A single prevented rework loop saves ~20 steps × ~4,000 tokens/step = ~80,000 tokens. **The rules pay for themselves within the first prevented mistake.**
