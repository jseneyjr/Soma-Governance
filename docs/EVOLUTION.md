# How This Approach Evolved

These rules weren't designed in a vacuum. They were extracted from real failures, refined through staff-level review, and continuously validated against live coding sessions.

## Phase 1: Prescriptive Rules ("Write what sounds right")

The first version was 4 `always_on` rules and 4 flat-checklist skills, written from best practices and intuition. Providence said "don't hallucinate." Cost-optimization said "use Flash for research." Testing said "test sad paths."

**What we learned:** Prescriptive rules are necessary but insufficient. The agent followed the letter of the rules while violating the spirit — it would "verify" by re-reading the same file 4 times, or "delegate" by spawning a Pro-tier subagent for a 3-line edit.

**Impact on rules:** Led to the **3 formal review iterations** (21 findings), which caught contradictions between rules, missing coverage, and ambiguous terminology.

## Phase 2: Evidence-Based Evolution ("Extract rules from real failures")

The turning point was running a **1,339-step post-mortem** on a real project session. Instead of guessing what rules were needed, we analyzed what actually went wrong:

- **749 steps (~56%) were wasted** on rework
- **180 steps** lost to hallucinated game hotkeys the agent invented without checking
- **110 steps** lost to venv confusion (host Python vs. project venv)
- **103 steps** lost to an infinite polling loop in tests with no timeout
- **50 steps** lost to method shadowing (`action_masks()` silently overridden)

Each failure pattern mapped directly to a missing rule:

| Failure (steps wasted) | Rule Created |
|:-----------------------|:-------------|
| Hallucinated hotkeys (180) | UI Grounding Gate — verify via screenshots, never guess |
| Venv confusion (110) | Makefile Venv Guard — bind `$(VENV)/bin/python` explicitly |
| Infinite test polling (103) | Mock-First Mandate — hardware boundaries always mocked |
| Method shadowing (50) | Symbol Collision Guard — grep before defining in large files |
| Stale references after rename (30) | Refactoring Sweep — global grep confirms zero orphans |

**Impact on rules:** This phase added 6 rules to providence.md and testing.md. More importantly, it shifted the methodology: rules are now derived from **observed waste**, not assumed best practices.

## Phase 3: Cross-Conversation Discovery ("Same failures, different projects")

Analyzing a single session was revealing. Analyzing **all sessions** showed which patterns are systemic:

| Pattern | Dwarf Fortress (1,579 steps) | TAB AI (1,551 steps) | Steering (856 steps) |
|:--------|:---:|:---:|:---:|
| Hallucinated controls | ✅ 160 steps | ✅ 180 steps | — |
| Venv/path confusion | ✅ | ✅ | — |
| Zero subagent delegation | ✅ 0 subagents, 17 compactions | Improved | Heavy use |
| Bulk media context pollution | — | ✅ 127 files in brain | — |
| Desktop automation safety breach | ✅ clicked through Steam | — | — |
| Premature framework extraction | ✅ 150 steps on unused SDK | — | — |

The Dwarf Fortress session was the most catastrophic: **1,579 steps, 8 architectural pivots, 2 safety incidents, and zero subagent delegation.** It burned an estimated 8M tokens and produced zero working autonomous runs.

**Impact on rules:** This phase added 5 entirely new governance areas — desktop automation safety, premature abstraction bans, pivot discipline, delegation floors, and real-time loop budgets.

## Phase 4: Continuous Governance ("Rules that improve themselves")

The final shift was from periodic review to continuous monitoring:

```
Session analyzed → waste classified by 23-pattern taxonomy (v2.1) → metrics stored
    ↓
effectiveness.json updated with before/after waste rates
    ↓
IF post_adoption_rate >= pre_adoption_rate → rule flagged INEFFECTIVE
IF post_adoption_rate < 30% of pre → rule flagged EFFECTIVE
IF new pattern with no rule → flagged UNCOVERED, priority = wasted steps
```

This caught 7 additional findings that manual review missed — including the insight that copying files into Antigravity's brain scratch directory pollutes checkpoint metadata.

## Phase 5: Divide & Conquer Optimization ("Work smarter, not harder")

After achieving 5% waste in governance sessions, the focus shifted from *preventing mistakes* to *maximizing throughput*:

- **Session Pre-flight Probe**: A Flash subagent checks venv health, test suite, git state, and display environment at session start — eliminating the #2 and #3 waste categories before any code is written (~500 tokens, <10s).
- **Review Sentinel**: Lightweight Flash reviewer dispatched every ~50 coding steps catches regressions before they compound. In `5dd84eed`, a hallucinated `total_mem` survived 188 steps; with sentinels, it would have been caught at step 73.
- **Disjoint Lane Protocol**: When approved changes touch separate files, parallel subagents execute simultaneously with explicit file ownership. Wall-clock time reduced 2-3x with zero merge conflicts.
- **Configurable Team Profiles**: `steering.conf` lets teams customize rules for their stack, team size, git strategy, and approval chains — making the system distributable without forking.

**Impact on rules:** Added `session-preflight` skill, Continuous Review to `staff-review`, Disjoint Lane Protocol to `subagent-delegation §2`, and Makefile-based installation with `steering.conf`.

## Phase 6: Multi-Lens Synthesis & Mechanized Guardrails ("Scale depth and automation")

With low baseline waste established, Phase 6 addressed review depth, context efficiency, and proactive mechanical detection:

- **Trident Protocol**: Added progressive 3-prong deep review (RECON → Roots → Bedrock) to `staff-review`. Separating reconnaissance scouts (problems only) from root-cause analysts (concrete fixes) and structural verifiers (Bedrock SHIP/BLOCK gate; read-only, does NOT run tests) prevents confirmation bias and scope creep (~8–12k tokens vs ~80k for prevented rework).
- **Maelstrom Protocol & Thorns (Adversarial Falsification)**: Introduced a full 4-stage adversarial review workflow (RECON → Roots → Thorns → Bedrock, ~15–20k tokens) for critical and catastrophic risk surfaces. Incorporates the **Thorns** prong (NASA IV&V tripartite falsification), where an adversarial falsification team actively attempts to break proposed fixes with a strict 2-cycle revision cap before passing to Bedrock.
- **Nature-Themed Naming**: Unified review protocols and prongs under natural phenomena metaphors:
  - Protocols: **Gale** (single-pass fan-out, was Salvo/Standard), **Trident** (progressive 3-prong), and **Maelstrom** (full adversarial, was Siege).
  - Prongs: **RECON** (broad survey), **Roots** (root cause analysis, was STRIKE), **Thorns** (adversarial falsification, was BREACH), and **Bedrock** (structural-only verification gate, was FORTIFY).
- **Risk-Based Protocol Selection**: Codified automated risk-tiered protocol routing: Low risk → Gale (~4k tokens), Medium/High risk → Trident (~8–12k tokens), and Critical/Catastrophic risk → Maelstrom (~15–20k tokens).
- **First Successful Maelstrom Dogfood Run**: In its initial dogfood run, the Maelstrom protocol completed successfully; the Thorns adversarial prong caught 5 critical bugs that would have shipped broken under traditional review.
- **Schema Bifurcation Fix in `governance_sweep.sh`**: Resolved schema bifurcation in `scripts/governance_sweep.sh`, reconciling disparate transcript field structures to accurately aggregate metrics across 17 sessions (7,015 total steps, 1,317 waste = 18.8% aggregate waste) under the 23-pattern taxonomy.
- **5 Specialist Skills**: Expanded domain capabilities with `domain-researcher` (grounded external fact compilation), `spec-synthesizer` (cross-referencing multi-lens findings into prioritized plans), `session-monitor` (live trajectory and waste tracking), `governance-auditor` (transcript-level per-rule PASS/FAIL checks), and `visual-analyst` (screen and UI state calibration), bringing the suite to 13 skills total.
- **10-Lens Staff Protocol**: Staff review expanded from ad-hoc analysis to 10 formal lenses covering Architecture, Performance, Security, Compliance, Behavioral, Domain Research, Spec Synthesis, Visual, Governance Audit, and Live Monitor.
- **Auto-Preflight & Domain Detection**: Embedded automated project scanning into `governance_init.sh` hooks. Invocation 1 automatically identifies coding project markers (`venv`, `package.json`, `Makefile`, `tests/`) and domain patterns (game automation, ML/RL), injecting targeted prompts with 0 model tokens consumed.
- **Context Pre-Seeding Protocol**: Standardized subagent dispatches with compact ~200-token headers (`[PROJECT]`, `[STACK]`, `[LAYOUT]`, `[CONSTRAINTS]`, `[OUTPUT]`), eliminating 2–3 cold-start exploratory steps per subagent.
- **Experiment Framework (E1–E10)**: Created `docs/EXPERIMENTS.md` with an active/backlog registry to systematically test governance hypotheses (concurrency, pre-seeding, preflight, gate triggers) with quantifiable metrics before graduating changes to rules.
- **Concurrency Expansion**: Raised read-only concurrency limits from 3 to 4 subagents and implementation writers from 2 to 3 under the Disjoint Lane Protocol, lowering the delegation floor from 100 to 75 steps.
- **Governance Sweep**: Introduced `scripts/governance_sweep.sh` to run periodic, non-blocking sweeps for unreviewed sessions (>100 steps), warning trend aggregation, and real-time session tracking without burning AI tokens (~500 tokens / local run).

**Impact on rules:** Upgraded `skills/staff-review` to support Gale, Trident, & Maelstrom modes across 10 lenses; added 5 specialist skills (13 total); updated `subagent-delegation.md` with §2.1 Context Pre-Seeding, higher concurrency (4 readers, 3 writers), and a 75-step delegation floor; automated hooks in `scripts/governance_init.sh`; and established `scripts/governance_sweep.sh` and `docs/EXPERIMENTS.md`.

## The Compound Effect

```
Prescriptive Rules → caught obvious gaps but missed real failure modes
    ↓
Evidence-Based → extracted rules from 1,339 steps of real waste
    ↓
Cross-Conversation → proved patterns are systemic, not one-off
    ↓
Continuous Monitor → catches new patterns as they emerge
    ↓
Divide & Conquer → parallel lanes, preflight probe, review sentinels
    ↓
Trident, Maelstrom & Mechanized Guardrails → Gale/Trident/Maelstrom, 10 lenses, 13 skills, auto-hooks
```

Compliance went from **7.8/10 to 9.8/10**, waste rate dropped from **~56% to 18.8% across 17 sessions (7,015 steps)**, with best-governed sessions reaching **1.1% waste** (`0dc37064` across 1,325 steps), and the rules now cover failure modes that no amount of upfront design would have predicted.

## Design Principles (Emerged, Not Prescribed)

1. **Evidence over intuition** — Every rule traces back to observed steps wasted. No rule exists "just in case."
2. **Accuracy over speed** — The agent must never sacrifice correctness to save tokens.
3. **Rules as a system** — Cross-references between rules are intentional. Providence §3 mandates read-before-write; refactoring-pilot operationalizes it as a phased workflow.
4. **Continuous validation** — Rules aren't "done" after review. Governance is a living system that evolves with each session.
