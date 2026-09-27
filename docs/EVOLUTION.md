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
- **Configurable Team Profiles**: `steering.conf` lets teams customize rules for their team size, git strategy, and approval chain — making the system distributable without forking.

**Impact on rules:** Added `session-preflight` skill, Continuous Review to `staff-review`, Disjoint Lane Protocol to `subagent-delegation §2`, and Makefile-based installation with `steering.conf`.

## Phase 6: Multi-Lens Synthesis & Mechanized Guardrails ("Scale depth and automation")

With low baseline waste established, Phase 6 addressed review depth, context efficiency, and proactive mechanical detection:

- **Trident Protocol**: Progressive 3-prong deep review (Spores → Roots → Bedrock) separating reconnaissance from root-cause analysis and structural verification. Prevents confirmation bias and scope creep.
- **Maelstrom Protocol & Thorns**: Full 4-stage adversarial workflow incorporating NASA IV&V tripartite falsification with a 2-cycle revision cap.
- **Nature-Themed Naming**: Unified protocols (Gale, Trident, Maelstrom) and prongs (Spores, Roots, Thorns, Bedrock) under natural phenomena metaphors.
- **Risk-Based Protocol Selection**: Automated risk-tiered routing — see [METRICS.md](METRICS.md#review-protocol-costs-5-modes--6-prongs) for cost details.
- **First Successful Maelstrom Dogfood**: Thorns adversarial prong caught 5 critical bugs that would have shipped broken under traditional review.
- **Schema Bifurcation Fix**: Reconciled disparate transcript field structures in `governance_sweep.sh` — see [METRICS.md](METRICS.md#aggregate-stats-17-sessions-7015-steps) for aggregate numbers.
- **13 Skills**: Added 5 specialist skills (domain-researcher, spec-synthesizer, session-monitor, governance-auditor, visual-analyst) alongside the original 8.
- **10-Lens Staff Protocol**: Architecture, Performance, Security, Compliance, Behavioral, Domain Research, Spec Synthesis, Visual, Governance Audit, Live Monitor.
- **Auto-Preflight & Domain Detection**: Zero-token project scanning in `governance_init.sh` hooks.
- **Context Pre-Seeding**: ~200-token compact headers eliminating 2–3 cold-start steps per subagent.
- **Experiment Framework (E1–E10)**: Active/backlog registry in [EXPERIMENTS.md](EXPERIMENTS.md).
- **Concurrency Expansion**: 4 readers / 3 writers under Disjoint Lane Protocol; delegation floor lowered from 100 to 75 steps.
- **Governance Sweep**: Local periodic scanning at ~500 tokens / run, zero LLM cost.

**Impact on rules:** Upgraded `staff-review` to support Gale, Trident, & Maelstrom across 10 lenses; 13 skills total; Context Pre-Seeding and higher concurrency in `subagent-delegation.md`; automated hooks; and `docs/EXPERIMENTS.md`.

## Phase 7: Empirical Falsification & Research-Backed Grounding ("Prove it or lose it")

While Phase 6 established multi-stage reviews and baseline automation, real-world execution revealed subtle multi-agent failure modes: false-positive findings, consensus bias, symptom-patching loops, and unverified subagent drift.

In **Maelstrom #2**, state-of-the-art 2026 academic research was incorporated:

1. **Empirical Refutation Gate** — 2-of-3 evidentiary criteria before accepting critical findings. Eliminates ~80% false positives (Agarwal 2026). See [METRICS.md](METRICS.md#review-protocol-costs-5-modes--6-prongs).
2. **Boundary Verification Protocol** — Orchestrator spot-checks with ±5 line locality tolerance. Demote-not-discard policy (IEEE GLOBECOM 2026).
3. **Orthogonal Persona Mandate** — Bans homogeneous reviewer fan-outs; mandates conflicting analytical incentives (MAR/ICML 2026).
4. **Diagnose Before Repair** — Structured diagnostic schema (`failure_mode`, `root_cause`, `broken_invariant`, `fix_spec`) required before any fix code (REFLEX/ICML 2026).
5. **First-Pass Success Rate (FPSR)** — Target >80%, halt at <50% (N≥5). Calibrated against Tencent SiriusDeliver 2026 (87.2%). See [METRICS.md](METRICS.md#first-pass-success-rate-fpsr).
6. **Incremental Escalation** — 4 upgrade paths preserving completed prongs with dirty-tree caveat. Extracted from live post-mortem `f8b82d61`.
7. **Mechanical Diff Downgrade** — Flash-tier for syntactic diff application (~85% reduction).
8. **Validated Concurrency Ceilings** — 4 readers / 3 writers empirically validated against MIT, Tencent, Coasty, Devin, Cursor, Copilot benchmarks.

**Impact on rules:** Empirical falsification in `staff-review`, Boundary Verification and Orthogonal Personas in `subagent-delegation.md`, structured diagnosis in `providence.md`, FPSR and mechanical diff tiering in `cost-optimization.md`.

## Phase 8: Spectrum Completion & Lifecycle Extraction ("Cover every risk tier, learn from every review")

Maelstrom #3 expanded the review system in two dimensions: **breadth** (Breeze and Tempest at both ends of the risk spectrum) and **depth** (Mycelium and Mulch prongs). Triple convergence from 3 Spores scouts, Thorns-verified (0/4 survived, all fixed), Bedrock SHIP.

1. **Breeze Protocol** — Lightweight targeted-fix mode for known defects. Skips Spores; BLOCK auto-escalates to Trident.
2. **Tempest Protocol** — Highest-assurance 6-prong pipeline with human gate via `ask_question` before Bedrock verdict.
3. **🍄 Mycelium Prong** — Blast-radius and dependency mapping (2-hop import chains) inserted between Spores and Roots.
4. **🍂 Mulch Prong** — Post-review learning extraction with circuit breaker preventing recursive reviews.
5. **7 Escalation Paths** (up from 4) and **5 Modes / 6 Prongs** — see [staff-review SKILL.md](../skills/staff-review/SKILL.md) for full details and [METRICS.md](METRICS.md#review-protocol-costs-5-modes--6-prongs) for costs.

**Impact on rules:** Upgraded `staff-review` with Breeze, Tempest, Mycelium, and Mulch. Updated documentation across README.md and METRICS.md.

## Phase 9: Tempest Hardening — Portability, Security & Documentation

Tempest #1 and #2 overhauled the build system, security gate, and documentation to make the governance framework portable and self-verifying:

- **Unified installer** replacing 3 duplicated platform scripts with a single `scripts/common.sh`-backed `install.sh`
- **Shared library** (`scripts/common.sh`) eliminating ~95 lines of duplicated path resolution, error handling, and color output
- **Dynamic `hooks.json.template`** replacing hardcoded scratch paths with `{{RULES_DIR}}` placeholders resolved at install time
- **6 new Make targets**: `uninstall`, `doctor`, `validate`, `update`, `status` (plus existing `install`, `test`)
- **Safety gate hardened**: fail-closed default, 15+ dangerous patterns, regex bypass fixes for edge cases
- **Documentation consolidated**: METRICS.md merge (token economics + telemetry + benchmarks), README rewrite (242→150 lines), EVOLUTION dedup

**Impact on rules:** No rule text changes — this phase improved the delivery and verification infrastructure around the rules.

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
    ↓
Empirical Falsification & Research Grounding → Refutation Gate, Boundary Verification, Orthogonal Personas, FPSR, Structured Diagnosis
    ↓
Spectrum Completion & Lifecycle Extraction → Breeze/Tempest, Mycelium/Mulch, 5 modes, 6 prongs, 7 escalation paths
    ↓
Tempest Hardening → Unified installer, shared library, dynamic hooks, safety gate hardening, docs consolidation
```

Compliance went from **7.8/10 to 9.8/10** and waste dropped from **~56% to 1.1%** in best-governed sessions — see [METRICS.md](METRICS.md) for the full breakdown. The rules now cover failure modes that no amount of upfront design would have predicted.

## Design Principles (Emerged, Not Prescribed)

1. **Evidence over intuition** — Every rule traces back to observed steps wasted. No rule exists "just in case."
2. **Accuracy over speed** — The agent must never sacrifice correctness to save tokens.
3. **Rules as a system** — Cross-references between rules are intentional. Providence §3 mandates read-before-write; refactoring-pilot operationalizes it as a phased workflow.
4. **Continuous validation** — Rules aren't "done" after review. Governance is a living system that evolves with each session.
