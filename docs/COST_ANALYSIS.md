# Cost Analysis

Detailed token costs, conditional loading savings, and ROI calculations for the AI Steering Rules governance system.

## Per-File Token Costs

**Always-on rules** — full content loaded every turn:

| Rule | Tokens/Turn |
|:-----|:------------|
| `providence.md` | ~1,661 |
| `subagent-delegation.md` | ~1,200 |
| `cost-optimization.md` | ~475 |
| **Subtotal** | **~3,336** |

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
| `desktop-automation.md` | ~25 | ~510 |
| **Subtotal** | **~205** | **~3,996** |

**Skills (13 total)** — zero cost until auto-activated:

| Skill | Idle Cost | Full Cost (when activated) |
|:------|:----------|:--------------------------|
| `security-audit` | ~62 | ~895 |
| `readme-writer` | ~45 | ~889 |
| `incident-debug` | ~60 | ~847 |
| `code-review` | ~55 | ~820 |
| `refactoring-pilot` | ~65 | ~629 |
| `post-mortem` | ~60 | ~596 |
| `performance-audit` | ~65 | ~496 |
| `staff-review` | ~55 | ~1,850 |
| `domain-researcher` | ~50 | ~550 |
| `spec-synthesizer` | ~50 | ~460 |
| `session-monitor` | ~50 | ~500 |
| `governance-auditor` | ~55 | ~650 |
| `visual-analyst` | ~50 | ~600 |
| **Subtotal** | **~672** | **~9,782** |

## Protocol & Automation Cost Profiles

| Protocol / Component | Type | Token Cost | Savings / ROI |
|:---------------------|:-----|:-----------|:--------------|
| **Standard Protocol** | Review (Single-Pass) | ~4k tokens | ~80k tokens per prevented rework loop (20x ROI) |
| **Trident Protocol** | Review (3-Prong) | ~8–12k tokens | ~80k tokens per prevented architectural regression (7–10x ROI) |
| **Auto-Preflight** | PreInvocation Hook | **0 tokens** (Bash) + ~900 tokens (if Flash probe dispatched) | Prevents 40–120 steps on venv/git drift (~160k–480k tokens) |
| **Context Pre-Seeding** | Subagent Prompting | ~200 tokens / dispatch | Eliminates 2–3 exploratory steps (~8k–12k tokens saved) |
| **Governance Sweep** | Periodic Scanner | ~500 tokens / run | Pure local Python (`sweep_session.py`), zero AI model tokens |

### Cost Breakdown Highlights:
- **Trident Protocol**: Standard protocol runs 3–4 Flash reviewers in a single pass (~4k tokens). Trident runs progressive prongs (RECON 3–4 scouts @ ~1k, STRIKE 1–2 analysts @ ~1.5k, optional FORTIFY 1 verifier @ ~1k) + staff synthesis (~2k orchestrator tokens), costing ~8–12k tokens for comprehensive deep reviews.
- **Auto-Preflight**: Zero-cost detection runs via bash/JSON inspection in `governance_init.sh` on Invocation 1. If project markers (`venv`, `package.json`, `Makefile`, `tests/`) are found, the agent dispatches a ~900-token Flash probe, preventing 40–120 steps of environment defects.
- **Context Pre-Seeding**: Prepends a ~200-token compact header (`[PROJECT]`, `[STACK]`, `[LAYOUT]`, `[CONSTRAINTS]`, `[OUTPUT]`) to subagent prompts, saving 2–3 exploratory file/search steps (~8k–12k tokens) per subagent.
- **Governance Sweep**: `scripts/governance_sweep.sh` scans unreviewed transcripts (>100 steps) and recalculates metrics locally at ~500 tokens equivalent per execution, incurring zero LLM API costs.
- **Updated Skills Count**: 13 skills total (up from 8 originally; idle cost ~672 tokens across all 13).

## Conditional Loading Savings

| Approach | Tokens/Turn |
|:---------|:------------|
| **Naive** — all 11 rules + 13 skills always loaded | ~17,114 |
| **Optimized** — conditional rules + skills idle | ~4,213 |
| **Savings** | **~12,901 tokens/turn (75%)** |

> **Methodology note**: The 75% figure pools rules and skills. Rules-only savings (excluding skills, which are natively deferred by the platform) = **~52%**. Both numbers are valid; the distinction matters for comparing against other governance systems.

## Observed Savings (Real Session Data)

Based on 9 sessions (5,561 steps) with waste classification:

| Metric | Before Rules | After Rules |
|:-------|:-------------|:------------|
| Waste rate | ~56% (earliest) | 27.6% (mid) → 5.0% (latest) |
| Rework loops per session | ~5 incidents | ~1 incident |
| Failed subagent steps | ~150 per session | ~0 (model tier fix) |
| Zombie background tasks | 6+ concurrent | Capped at 2 |

## Live Session Comparison (0dc37064 vs 5dd84eed)

Direct A/B comparison of the same project (TAB AI) with and without governance:

| Metric | `5dd84eed` (weak rules) | `0dc37064` (full governance) | Improvement |
|:-------|:----------------------:|:---------------------------:|:------------|
| Waste rate | 27.6% | 3.2% (at step 92) | -24.4pp |
| Steps to first working train | Never (547 steps) | Step 36 | ∞ → 36 |
| Credit usage | ~100% baseline | ~12% | -88% |
| Rule violations | 8 | 1 | -87.5% |
| Subagent model tier | Opus (inherit) | 100% Flash | Massive savings |

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
