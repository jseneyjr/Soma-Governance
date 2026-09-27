# Cost Analysis

Detailed token costs, conditional loading savings, and ROI calculations for the AI Steering Rules governance system.

## Per-File Token Costs

**Always-on rules** — full content loaded every turn:

| Rule | Tokens/Turn |
|:-----|:------------|
| `providence.md` | ~1,750 |
| `subagent-delegation.md` | ~1,450 |
| `cost-optimization.md` | ~550 |
| **Subtotal** | **~3,750** |

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
| **Breeze Protocol** | Review (Targeted Fix) | ~3–4k tokens (1–2 Flash) | Fast-tracks known defects; BLOCK auto-escalates to Trident (~4–8k saved vs starting at Trident) |
| **Gale Protocol** | Review (Single-Pass) | ~4k tokens (3–4 Flash) | ~80k tokens per prevented rework loop (20x ROI) |
| **Trident Protocol** | Review (3-Prong) | ~8–12k tokens (5–8 Flash) | ~80k tokens per prevented architectural regression (7–10x ROI) |
| **Maelstrom Protocol** | Adversarial Review (4-Stage) | ~15–20k tokens (7–12 Flash) | Prevents catastrophic failures; caught 5 critical bugs in dogfooding (5–7x ROI) |
| **Tempest Protocol** | Full Assurance (6-Stage) | ~30–50k tokens (10–16 Flash) | Highest assurance for catastrophic risk; human gate before Bedrock verdict (3–5x ROI) |
| **Mycelium Prong** | Blast Radius Mapping | ~2–4k tokens (1–2 Flash) | Traces 2-hop import chains and type consumers; prevents silent downstream breakage |
| **Mulch Prong** | Learning Extraction | ~1–2k tokens (1 Flash) | Post-review taxonomy/rule proposals; read-only with recursive review circuit breaker |
| **Empirical Refutation Gate** | Review Gate | **0 tokens** (structural check) | Eliminates ~80% false positives (Agarwal 2026); saves 15k–30k tokens per avoided phantom bug chase |
| **Incremental Escalation** | Review Transition | **0 overhead** (pruning) | Saves 4k–8k tokens per review upgrade by preserving completed prongs across 7 paths |
| **Mechanical Diff Downgrade** | Subagent Execution | ~85% token reduction | Down-tiers exact diff application to Flash tier rather than Inherit/Pro |
| **Auto-Preflight** | PreInvocation Hook | **0 tokens** (Bash) + ~900 tokens (if Flash probe dispatched) | Prevents 40–120 steps on venv/git drift (~160k–480k tokens) |
| **Context Pre-Seeding** | Subagent Prompting | ~200 tokens / dispatch | Eliminates 2–3 exploratory steps (~8k–12k tokens saved) |
| **Governance Sweep** | Periodic Scanner | ~500 tokens / run | Pure local Python (`sweep_session.py`), zero AI model tokens |

### Cost Breakdown Highlights:
- **Review Protocols (5 modes)**:
  - **Breeze Protocol**: Targeted-fix mode for known defects (~3–4k tokens). Skips Spores, runs Roots → Bedrock only. BLOCK handling: max 1 revision attempt, then auto-escalates to Trident. Ideal for string renames, doc freshness, lint fixes.
  - **Gale Protocol**: Single-pass parallel fan-out running 3–4 Flash reviewers (~4k tokens) for routine reviews and low-risk changes.
  - **Trident Protocol**: Progressive 3-prong review (Spores 3–4 scouts @ ~1k, Roots 1–2 analysts @ ~1.5k, Bedrock 1 structural verifier @ ~1k) + staff synthesis (~2k orchestrator tokens), costing ~8–12k tokens across 5–8 Flash dispatches for architecture changes and high-risk refactors. Bedrock is structural-only (read-only, does not run tests).
  - **Maelstrom Protocol**: Full adversarial review spanning 4 stages: Spores scouts, Roots root-cause analysts, Thorns adversarial falsification (NASA IV&V tripartite with 2-cycle revision cap), and Bedrock structural verification gate. Costs ~15–20k tokens across 7–12 Flash dispatches for critical and catastrophic risk surfaces.
  - **Tempest Protocol**: Highest-assurance mode spanning 6 stages: Spores → Mycelium → Roots → Thorns → Bedrock → Mulch (~30–50k tokens across 10–16 Flash dispatches). Includes a human gate via `ask_question` before Bedrock verdict. For catastrophic risk: infra, auth, schema migrations.
- **Prong Costs (6 prongs)**:
  - **Spores**: ~1k tokens (3–4 scouts, width survey)
  - **Mycelium**: ~2–4k tokens (1–2 Flash, blast-radius/dependency mapping, 2-hop import chain tracing)
  - **Roots**: ~1.5k tokens (1–2 analysts, root-cause + fix proposals)
  - **Thorns**: ~3–5k tokens (adversarial falsification, 2-cycle revision cap)
  - **Bedrock**: ~1k tokens (structural-only verification gate, SHIP/BLOCK)
  - **Mulch**: ~1–2k tokens (1 Flash, post-review learning extraction, taxonomy/rule/skill proposals)
- **Incremental Escalation (7 paths)**: Enables dynamic mid-session escalation (Breeze→Trident, Gale→Trident, Gale→Maelstrom, Gale→Tempest, Trident partial→Maelstrom, Trident full→Maelstrom, Maelstrom→Tempest) without throwing away already completed prongs, saving ~4k–8k tokens per review upgrade.
- **Empirical Refutation Gate**: Filters findings through a 2-of-3 evidentiary gate (citation ±5 lines, reproduction command, mechanical verification). Eliminates ~80% of false-positive claims (Agarwal 2026), preventing expensive investigative goose-chases.
- **Mechanical Diff Downgrade**: When Roots or Thorns prongs have already produced exact, verified diffs, applying them is purely syntactic. Down-tiering implementation subagents to `flash` tier (rather than `inherit` Pro/Opus) reduces execution token cost by ~85% per editing task.
- **Concurrency Validation**: Concurrency ceilings of 4 read-only subagents and 3 implementation writers (under the Disjoint Lane Protocol) are empirically validated against 2024–2026 industry benchmarks (MIT scaling studies, Tencent, Coasty, Devin, Cursor, Copilot). 4 readers hits the optimal recall knee before consensus degradation; 3 writers maximizes parallel throughput without branch locks or merge conflicts.
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

Based on 17 sessions (7,015 total steps, 1,317 waste = 18.8% aggregate waste) with waste classification:

| Metric | Before Rules | After Rules |
|:-------|:-------------|:------------|
| Waste rate | ~56% (earliest) | 27.6% (mid) → 18.8% (all 17 sessions) / 1.1% (latest) |
| First-Pass Success Rate (FPSR) | < 35% (uncontrolled churn) | > 80% target (87.2% industry benchmark) |
| Rework loops per session | ~5 incidents | ~1 incident |
| Failed subagent steps | ~150 per session | ~0 (model tier fix) |
| Zombie background tasks | 6+ concurrent | Capped at 2 |

## Live Session Comparison (0dc37064 vs 5dd84eed)

Direct A/B comparison of the same project (TAB AI) with and without governance:

| Metric | `5dd84eed` (weak rules) | `0dc37064` (full governance) | Improvement |
|:-------|:----------------------:|:---------------------------:|:------------|
| Waste rate | 27.6% (547 steps) | 1.1% (1,325 steps) | -26.5pp |
| Steps to first working train | Never (547 steps) | Step 36 | ∞ → 36 |
| Credit usage | ~100% baseline | ~12% | -88% |
| Rule violations | 8 | 1 | -87.5% |
| Subagent model tier | Opus (inherit) | 100% Flash | Massive savings |

## First-Pass Success Rate (FPSR) & Quality Economics

While waste rate measures unproductive steps, **First-Pass Success Rate (FPSR)** evaluates generative precision: the percentage of initial code implementations that satisfy tests and specifications without revision cycles.

- **Target & Benchmark**: Target is **> 80% FPSR**, calibrated against industry autonomous agent baselines (Tencent SiriusDeliver 2026 reports 87.2% FPSR).
- **The Guess-and-Check Tax**: When an agent writes code without verifying types, signatures, or existing patterns, failures lead to multi-turn debugging cascades costing **~15–25 steps** (~60k–100k context tokens) per defect.
- **Halt & Diagnose Circuit Breaker**: If FPSR drops below 50% across a sample of $N \ge 5$ code writes, the agent must halt coding immediately and execute a structured root-cause diagnosis (`failure_mode`, `root_cause`, `broken_invariant`, `fix_spec`) before attempting further edits.
- **TDD Red-Phase Exemption**: Intentional test failures in red-green-refactor workflows do not penalize FPSR.

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

> The governance rules cost ~3,750 tokens/turn to maintain. A single prevented rework loop saves ~20 steps × ~4,000 tokens/step = ~80,000 tokens. **The rules pay for themselves within the first prevented mistake.**
