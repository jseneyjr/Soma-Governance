# Metrics & Token Economics

Unified metrics for the AI Steering Rules governance system — token costs, empirical telemetry, and quality benchmarks.

---

## Token Economics

### Rules (Per-File Token Census)

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

### Skills (Idle vs Active)

13 skills — zero cost until auto-activated:

| Skill | Idle Cost | Full Cost (when activated) |
|:------|:----------|:--------------------------|
| `staff-review` | ~55 | ~1,850 |
| `security-audit` | ~62 | ~895 |
| `readme-writer` | ~45 | ~889 |
| `incident-debug` | ~60 | ~847 |
| `code-review` | ~55 | ~820 |
| `refactoring-pilot` | ~65 | ~629 |
| `post-mortem` | ~60 | ~596 |
| `governance-auditor` | ~55 | ~650 |
| `visual-analyst` | ~50 | ~600 |
| `domain-researcher` | ~50 | ~550 |
| `session-monitor` | ~50 | ~500 |
| `performance-audit` | ~65 | ~496 |
| `spec-synthesizer` | ~50 | ~460 |
| **Subtotal** | **~672** | **~9,782** |

### Review Protocol Costs (5 Modes + 6 Prongs)

| Protocol | Dispatches | Token Cost | ROI |
|:---------|:----------:|:-----------|:----|
| **Breeze** | 1–2 Flash | ~3–4k | Fast-tracks known defects; BLOCK auto-escalates to Trident |
| **Gale** | 3–4 Flash | ~4k | ~80k per prevented rework loop (20x ROI) |
| **Trident** | 5–8 Flash | ~8–12k | ~80k per prevented architectural regression (7–10x ROI) |
| **Maelstrom** | 7–12 Flash | ~15–20k | Caught 5 critical bugs in dogfooding (5–7x ROI) |
| **Tempest** | 10–16 Flash | ~30–50k | Highest assurance; human gate before verdict (3–5x ROI) |

| Prong | Cost | Role |
|:------|:-----|:-----|
| 🍄 Spores | ~1k (3–4 scouts) | Width survey, problem identification |
| 🍄 Mycelium | ~2–4k (1–2 Flash) | Blast-radius mapping, 2-hop import chain tracing |
| 🌿 Roots | ~1.5k (1–2 analysts) | Root-cause analysis + concrete fix proposals |
| 🌹 Thorns | ~3–5k (adversarial) | NASA IV&V falsification, 2-cycle revision cap |
| 🪨 Bedrock | ~1k (structural) | SHIP/BLOCK gate (read-only, does NOT run tests) |
| 🍂 Mulch | ~1–2k (1 Flash) | Post-review learning extraction, taxonomy proposals |

**Key cost mechanisms:**

- **Empirical Refutation Gate**: 0 tokens (structural check). Eliminates ~80% false positives (Agarwal 2026); saves 15k–30k tokens per avoided phantom bug chase.
- **Incremental Escalation**: 0 overhead. Preserves completed prongs across 7 upgrade paths, saving ~4k–8k tokens per review upgrade.
- **Mechanical Diff Downgrade**: ~85% token reduction by down-tiering exact diff application to Flash.

### Conditional Loading ROI

| Approach | Tokens/Turn |
|:---------|:------------|
| **Naive** — all 11 rules + 13 skills always loaded | ~17,528 |
| **Optimized** — conditional rules + skills idle | ~4,627 |
| **Savings** | **~12,901 tokens/turn (73.6%)** |

> [!NOTE]
> The 73.6% figure pools rules and skills. Rules-only savings (excluding skills, which are natively deferred by the platform) = **~52%**. Both numbers are valid; the distinction matters for comparing against other governance systems.

**Additional automation savings:**

| Mechanism | Cost | Savings |
|:----------|:-----|:--------|
| Auto-Preflight | 0 tokens (Bash) + ~900 if Flash probe dispatched | Prevents 40–120 steps on venv/git drift (~160k–480k tokens) |
| Context Pre-Seeding | ~200 tokens / dispatch | Eliminates 2–3 exploratory steps (~8k–12k tokens) |
| Governance Sweep | ~500 tokens / run (local Python) | Zero AI model tokens |

---

## Empirical Telemetry

### Aggregate Stats (17 Sessions, 7,015 Steps)

| Metric | Value |
|:-------|:------|
| Total steps analyzed | 7,015 |
| Sessions analyzed | 17 (8 deep, 9 sweep) |
| Overall waste rate | 18.8% (1,317 / 7,015 steps) |
| Waste patterns tracked | 23 (taxonomy v2.1) |
| Schema extraction | Polymorphic (handles both flat and nested) |
| Rule sections monitored | 13 |
| Rules with EFFECTIVE verdict | 2 (providence §11, §8) |
| Rules with INEFFECTIVE verdict | 3 (needs mechanical enforcement) |

### Top Waste Sources (Ranked)

| Rank | Rule | Target Pattern | Waste (steps) | % of Total |
|:-----|:-----|:---------------|:--------------|:-----------|
| 1 | providence §10 | Desktop automation guessing | 255 | 19% |
| 2 | providence §3 | Rework loops (no read-before-write) | 230 | 18% |
| 3 | providence §11 | Scope inversion + micro-prototyping | 222 | 17% |
| 4 | providence §8 | Environment blindness / venv drift | 120 | 9% |
| 5 | providence §13 | Metric rationalization | 70 | 5% |
| 6 | providence §1 | Hallucination (APIs, keybindings) | 55 | 4% |
| 7 | testing §6 | Syntax-only verification (ast.parse) | 55 | 4% |
| 8 | cost-optimization §4 | Zombie accumulation | 50 | 4% |

> [!IMPORTANT]
> Top 3 rules target **54% of all waste**. Providence dominates because most waste stems from acting without verification.

### Rule Effectiveness Verdicts

| Metric | Before Rules | After Rules |
|:-------|:-------------|:------------|
| Waste rate | ~56% (earliest) | 27.6% (mid) → 18.8% (all 17) / 1.1% (latest) |
| First-Pass Success Rate | < 35% (uncontrolled) | > 80% target (87.2% benchmark) |
| Rework loops per session | ~5 incidents | ~1 incident |
| Failed subagent steps | ~150 per session | ~0 (model tier fix) |
| Zombie background tasks | 6+ concurrent | Capped at 2 |

### Review & Improvement History

| Phase | Source | Findings | Fixed | Key Changes |
|:------|:-------|:---------|:------|:------------|
| **Review 1** | Staff cross-rule audit | 7 | 5 | Trade-off clarity, broadened destructive-ops, serverless carve-out |
| **Review 2** | Compliance audit (1,042 steps) | 7 | 6 | External evidence priority, YAGNI migration gate, phase gates, concurrency cap |
| **Review 3** | Third iteration audit | 7 | 6 | Stale frontmatter, tier consolidation, destructive delegation, env verification |
| **Post-Mortem** | 1,339-step session analysis | 6 | 6 | UI grounding gate, symbol collision guard, refactoring sweep, mock mandate |
| **Skills Mod** | Original 4 skills audit | 10 | 10 | Phased workflows, anti-patterns, output formats, Providence cross-refs |
| **Live Monitor** | Continuous (10-min cycles) | 7 | 7 | Bulk media delegation, scratch hygiene, disjoint file ownership |
| **Backfill 1** | f7cf2179 (1,579 steps) | 5 | 5 | Desktop automation safety, premature abstraction ban, pivot discipline |
| **Hooks Redesign** | Architectural review | 8 | 8 | PreInvocation governance, PreToolUse safety gate, Stop log export |
| **Backfill 2** | 7 sessions (5,800+ steps) | 5 | 5 | No collateral kills, deliverable-first, micro-prototyping cap |
| **Staff Review** | Architecture + Performance fan-out | 15 | 10 | Circular symlink fix, polyglot conditional, cost-opt dedup, git add gate, async export |
| **Post-Mortem 11** | bdb02985 + 5dd84eed (4 Flash analysts) | 9 | 9 | Pre-push test gate, coordinate grounding, taxonomy v2.1, hook testing |
| **Total** | | **86** | **77** | 9 deferred as intentional design decisions or P2/P3 |

---

## Quality Benchmarks

### First-Pass Success Rate (FPSR)

- **Target & Benchmark**: > 80% FPSR, calibrated against Tencent SiriusDeliver 2026 (87.2% FPSR).
- **The Guess-and-Check Tax**: Failures without type/signature verification lead to multi-turn debugging cascades costing **~15–25 steps** (~60k–100k tokens) per defect.
- **Halt & Diagnose Circuit Breaker**: FPSR < 50% across N ≥ 5 code writes → immediate coding halt + structured diagnosis (`failure_mode`, `root_cause`, `broken_invariant`, `fix_spec`).
- **TDD Red-Phase Exemption**: Intentional test failures in red-green-refactor workflows do not penalize FPSR.

### Live A/B Validation

Direct comparison of the same project (TAB AI) with and without governance:

| Metric | `5dd84eed` (weak rules) | `0dc37064` (full governance) | Improvement |
|:-------|:----------------------:|:---------------------------:|:------------|
| Waste rate | 27.6% (547 steps) | 1.1% (1,325 steps) | -26.5pp |
| Steps to first working train | Never (547 steps) | Step 36 | ∞ → 36 |
| Credit usage | ~100% baseline | ~12% | -88% |
| Rule violations | 8 | 1 | -87.5% |
| Subagent model tier | Opus (inherit) | 100% Flash | Massive savings |

### 5-Dimension Compliance Scores (7.8 → 9.8)

| Dimension | Before | After | Key Fixes |
|:----------|:------:|:-----:|:----------|
| Providence & Governance | 6.5 | 9.5 | External evidence, plan adherence, fail-fast validation, UI grounding gate |
| Cost Optimization | 9.5 | 10 | Concurrency cap, tier consolidation, scratch hygiene |
| Subagent Delegation | 8.5 | 9.5 | Read-only awareness, workspace conflict prevention, no collateral kills |
| Root Cause Resolution | 9.5 | 9.5 | No changes needed — agent fixed all 6 code review findings |
| Execution Discipline | 6.0 | 9.5 | Phase gates, checkpoint testing, ast.parse ban, mock-first mandate |
| **Overall** | **7.8** | **9.8** | **62 findings fixed across all phases** |

### Accuracy-Driven Savings Over Time

The biggest cost driver isn't token consumption — it's **rework loops**:

```
Agent claims "fixed" → User tests → Same error → Agent re-investigates → Finds real cause → Applies correct fix
```

Each loop costs **~20–25 steps** of wasted context. Compound effect: rework fills the context window with noise, degrading accuracy on subsequent turns.

| Timeframe | Without Governance | With Governance | Savings |
|:----------|:-------------------|:----------------|:--------|
| Per incident | ~22 rework steps | ~3 steps (first-time-right) | ~19 steps |
| Per session (~600 steps) | ~5 incidents × 22 = 110 steps | ~1 incident × 22 = 22 steps | ~88 steps |
| Per month (20 sessions) | ~2,200 wasted steps | ~440 wasted steps | **~1,760 steps** |

> [!TIP]
> The governance rules cost ~3,750 tokens/turn to maintain. A single prevented rework loop saves ~80,000 tokens. **The rules pay for themselves within the first prevented mistake.**

### Staff Review Impact

- **Maelstrom #1** — Caught 5 bugs pre-ship (circular symlink, polyglot conditional, cost-opt dedup, git add gate, async export)
- **Maelstrom #2** — Added 6 research-backed governance upgrades (Empirical Refutation Gate, Incremental Escalation, Boundary Verification Protocol, Orthogonal Persona Mandate, Validated Concurrency Limits, Spores rename)
- **Maelstrom #3** — Added Breeze, Tempest, Mycelium, Mulch modes. 4-prong verification.
- **Tempest #1** — Build system overhaul (16 files, 1080 insertions). Unified installer, shared library, safety gate hardening.
- **Tempest #2** — Documentation modernization. README rewrite (242→150 lines), METRICS.md merge, EVOLUTION dedup.
