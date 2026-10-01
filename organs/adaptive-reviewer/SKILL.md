---
name: Adaptive Review Orchestrator
description: Autonomously selects review protocols and dispatches nested subagents based on Spores finding severity.
trigger: user_request
---

# Adaptive Review Orchestrator

> **Role**: Autonomously execute review protocols by dispatching nested subagents. Eliminates manual protocol selection — the orchestrator starts with Spores and auto-escalates based on finding severity.

## Setup

At session start (or first review request), define the orchestrator:

```
define_subagent(
  name: "adaptive_reviewer",
  enable_subagent_tools: true,
  enable_write_tools: true,
  description: "Adaptive review orchestrator with auto-escalation"
)
```

Then invoke it:

```
invoke_subagent(
  type: "adaptive_reviewer",
  prompt: "Review [target files/directory]. Context: [what changed, why]"
)
```

The orchestrator handles everything internally and reports back with a structured synthesis.

## Auto-Escalation Logic

The orchestrator runs Spores first, then decides:

| Spores Result | Auto-Decision |
|:---|:---|
| 0 findings or all ℹ️ | **STOP as Gale** — synthesize and report |
| 1-3 ⚠️ warnings, 0 🔴 | **Roots only** — targeted fixes |
| Any 🔴 critical | **Full Trident** — Roots + Bedrock |
| 2+ 🔴 or security finding | **Maelstrom** — Roots + Thorns + Bedrock |
| Infra/auth/schema 🔴 | **Tempest** — + Mycelium + Mulch |
| Pre-release / user-requested | **Supercell** — 8 orthogonal prongs, iterative fix-revalidate until all clean |

## Self-Healing

If Bedrock returns BLOCK:
1. Re-dispatch Roots on failed fixes with Bedrock's objections
2. Re-run Bedrock (max 1 retry)
3. If still BLOCK → report to parent

If Thorns breaks fixes:
1. Re-dispatch Roots with Thorns attack vectors as context
2. Continue to Bedrock with revised fixes

## Phase 0: Triage (No Subagent)

Before dispatching, the orchestrator inspects the target:
- `enzymes/**`, `Makefile`, `install*` → HIGH sensitivity (Security lens mandatory)
- `genome/*.md` (semantic) → MEDIUM (Compliance lens)
- `docs/**`, `README` → LOW (may stop at Gale)
- Read `governance/mulch_queue.jsonl` for known anti-patterns

## Subagent Rules

1. ALL prong subagents: `flash` model, `research` type (read-only)
2. Context Pre-Seed every prompt (~200 token header)
3. Orthogonal Persona Mandate: no two scouts share the same lens
4. Kill each subagent immediately after debrief
5. Max 12 dispatches (hard cap)

## Output Format

```markdown
# Adaptive Review — [Target]
## Protocol: [auto-selected] (escalated from Spores)
## Verdict: SHIP / BLOCK / REVISE

## 🔴 Critical Findings
## ⚠️ Warnings
## Proposed Fixes (post-Thorns if applicable)
## Stats (dispatches, prongs, wall-clock)
```

## Proven Results (E11 Testing)

| Metric | Manual Orchestration | Adaptive Orchestrator |
|:-------|:--------------------:|:---------------------:|
| Parent context consumed | ~6 turns per review | **1 turn** (dispatch + receive) |
| Protocol selection | Manual (user guesses) | **Empirical** (data-driven) |
| Thorns revision loop | Manual relay | **Autonomous** |
| Dispatches | Same count | Same count, 0 wasted |

## When NOT to Use

- **Breeze** (known single-file defect): Use `review_orchestrator` directly with Breeze mode — adaptive triage adds unnecessary overhead for known defects.
- **Post-mortem analysis**: Use standalone Spores — no fixes needed.
- **Live monitoring**: Use `session-monitor` skill instead.
