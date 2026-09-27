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

- **Trident Protocol**: Added progressive 3-prong deep review (Spores → Roots → Bedrock) to `staff-review`. Separating reconnaissance scouts (problems only) from root-cause analysts (concrete fixes) and structural verifiers (Bedrock SHIP/BLOCK gate; read-only, does NOT run tests) prevents confirmation bias and scope creep (~8–12k tokens vs ~80k for prevented rework).
- **Maelstrom Protocol & Thorns (Adversarial Falsification)**: Introduced a full 4-stage adversarial review workflow (Spores → Roots → Thorns → Bedrock, ~15–20k tokens) for critical and catastrophic risk surfaces. Incorporates the **Thorns** prong (NASA IV&V tripartite falsification), where an adversarial falsification team actively attempts to break proposed fixes with a strict 2-cycle revision cap before passing to Bedrock.
- **Nature-Themed Naming**: Unified review protocols and prongs under natural phenomena metaphors:
  - Protocols: **Gale** (single-pass fan-out, was Salvo/Standard), **Trident** (progressive 3-prong), and **Maelstrom** (full adversarial, was Siege).
  - Prongs: **Spores** (broad survey, was RECON), **Roots** (root cause analysis, was STRIKE), **Thorns** (adversarial falsification, was BREACH), and **Bedrock** (structural-only verification gate, was FORTIFY).
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

## Phase 7: Empirical Falsification & Research-Backed Grounding ("Prove it or lose it")

While Phase 6 established multi-stage reviews and baseline automation, real-world execution revealed that multi-agent systems suffer from subtle failure modes: false-positive findings chasing nonexistent bugs, consensus bias among homogeneous subagents, symptom-patching retry loops, and unverified subagent drift. 

In **Maelstrom #2**, we incorporated state-of-the-art 2026 academic research and live post-mortem lessons into the governance engine:

1. **Empirical Refutation Gate (`staff-review` SKILL.md)**:
   - Before accepting any critical review finding, require at least **2 of 3 empirical criteria**: (1) verified `file:line` citation (±5 lines), (2) executable reproduction command or test case, and (3) independent mechanical verification (grep check or arithmetic validation).
   - Omission findings (e.g., missing middleware, missing rate-limiting) satisfy criterion 3 via grep-confirmed absence without penalizing missing line citations.
   - Enforces graduated demotion: findings meeting 0 criteria become ℹ️ info, 1 criterion becomes ⚠️ warning, and only 2+ criteria reach 🔴 critical.
   - **Academic Source**: Agarwal et al. (2026), eliminating ~80% of false-positive claims in multi-agent code analysis.

2. **Boundary Verification Protocol (`subagent-delegation.md §6`)**:
   - The orchestrator must spot-check subagent assertions before acting on them, incorporating a **fuzzy ±5 line locality tolerance** to accommodate natural 1–3 line drifts common in LLM context representations.
   - Enforces a strict *demote-not-discard* policy: findings failing locality search are downgraded to ℹ️ info rather than silently suppressed, preserving visibility while preventing ungrounded hallucination compounding across agent boundaries.
   - Omission claims are validated through negative grep scans.
   - **Academic Source**: IEEE GLOBECOM 2026 (Verification Protocols in Multi-Agent Orchestration).

3. **Orthogonal Persona Mandate (`subagent-delegation.md §7`)**:
   - Explicitly bans homogeneous reviewer fan-outs (e.g., 3 subagents identically prompted to "find bugs"), which waste tokens by converging on identical surface-level findings via consensus bias.
   - Mandates assigning conflicting analytical incentives across concurrent reviewers (e.g., correctness verifier vs. performance minimalist vs. adversarial red-team).
   - Permits same-domain depth audits only as an exception for high-assurance single-domain subsystems (e.g., cryptography, auth pipelines).
   - **Academic Source**: MAR (Multi-Agent Review) / ICML 2026.

4. **Diagnose Before Repair (`providence.md §7`)**:
   - Prohibits writing fix code until root-cause analysis is formalized.
   - Mandates an explicit structured diagnostic schema before drafting fixes:
     ```
     failure_mode: <observable symptom>
     root_cause: <underlying defect>
     broken_invariant: <system contract violated>
     fix_spec: <concrete modification requirements>
     ```
   - Eliminates blind symptom-patching loops where agents repeatedly wrap broken code in defensive `try/except` blocks, null checks, or retries.
   - **Academic Source**: REFLEX / ICML 2026.

5. **First-Pass Success Rate (FPSR) Metric (`cost-optimization.md §5`)**:
   - Introduces FPSR (percentage of initial code writes passing tests without revision) alongside waste rate, setting a target of **>80%**.
   - Triggers an immediate coding halt and root-cause diagnostic if FPSR drops below 50% after a minimum sample of $N \ge 5$ code writes.
   - Explicitly excludes intentional red-phase failures in Test-Driven Development (TDD).
   - **Industry/Academic Source**: Tencent SiriusDeliver (2026 benchmark achieving 87.2% FPSR).

6. **Incremental Escalation (`staff-review` SKILL.md)**:
   - Eliminates redundant work when upgrading review intensity mid-session across 4 transition paths:
     - Gale (fan-out) → Trident (maps fan-out to Spores, then runs Roots + Bedrock)
     - Gale (fan-out) → Maelstrom (adds security lens Spores, then full Roots → Thorns → Bedrock)
     - Trident (Spores + Roots) → Maelstrom (injects Thorns adversarial testing on existing Roots, then Bedrock)
     - Trident (full) → Maelstrom (injects Thorns, re-verifies via Bedrock with adversarial context)
   - Incorporates a **dirty-tree caveat** (`git status` check) to guarantee that code has not drifted before running subsequent adversarial prongs.
   - **Source**: Extracted from live session post-mortem `f8b82d61`.

7. **Mechanical Diff Downgrade (`cost-optimization.md §3`)**:
   - When deep review prongs (Roots or Thorns) have already produced exact, line-numbered before/after diffs, applying those diffs is purely syntactic.
   - Mandates down-tiering subagent dispatches to the lightweight `flash` tier, banning expensive `inherit` or `pro` token consumption for mechanical diff applications.

8. **Validated Concurrency Ceilings**:
   - Empirically validated the existing limits (4 read-only subagents, 3 disjoint writers) against 2024–2026 multi-agent scaling literature:
     - 4 read-only subagents marks the optimal recall knee before diminishing returns and consensus degradation set in.
     - 3 implementation writers under the Disjoint Lane Protocol represents the industry sweet spot for parallel writes without branch thrashing or interface lock contention.
   - **Sources**: MIT multi-agent scaling study, Tencent, Coasty, and commercial agent baselines (Devin, Cursor, Copilot).

**Impact on rules:** Enforced empirical falsification in `staff-review`, codified Boundary Verification and Orthogonal Personas in `subagent-delegation.md`, established structured diagnosis in `providence.md`, added FPSR and mechanical diff tiering to `cost-optimization.md`, and validated subagent concurrency against top-tier 2026 benchmarks.

## Phase 8: Spectrum Completion & Lifecycle Extraction ("Cover every risk tier, learn from every review")

Maelstrom #3 expanded the review system in two dimensions: **breadth** (adding protocols at both ends of the risk spectrum) and **depth** (adding prongs for dependency mapping and post-review learning). Triple convergence from 3 Spores scouts, Thorns-verified (0/4 survived, all fixed), Bedrock SHIP.

1. **Breeze Protocol (`staff-review` SKILL.md)**:
   - Lightweight targeted-fix mode for known defects (~3–4k tokens). Skips Spores reconnaissance entirely, running only Roots → Bedrock.
   - BLOCK handling: max 1 revision attempt; if unresolved, auto-escalates to Trident.
   - Use cases: known bugs, string renames, doc freshness, lint fixes.
   - Fills the gap below Gale for changes where the problem is already identified and only the fix needs verification.

2. **Tempest Protocol (`staff-review` SKILL.md)**:
   - Highest-assurance mode (~30–50k tokens). Full 6-prong pipeline: Spores → Mycelium → Roots → Thorns → Bedrock → Mulch.
   - Introduces a **human gate** via `ask_question` before Bedrock issues its SHIP/BLOCK verdict, ensuring explicit human oversight for catastrophic-risk changes.
   - Use cases: infrastructure changes, auth pipeline modifications, database schema migrations, cryptographic subsystems.
   - Fills the gap above Maelstrom for changes where automated review alone is insufficient.

3. **🍄 Mycelium Prong (`staff-review` SKILL.md)**:
   - Blast-radius and dependency mapping stage inserted after Spores and before Roots.
   - Traces import chains (max 2 hops), cross-repo state, and type consumers to build a dependency graph around affected code.
   - Receives Spores findings as input and passes enriched dependency context to Roots, enabling more precise root-cause analysis.
   - Prevents fixes that silently break downstream consumers.

4. **🍂 Mulch Prong (`staff-review` SKILL.md)**:
   - Post-review learning extraction stage that runs on both SHIP and BLOCK outcomes.
   - Proposes taxonomy patterns, rule updates, and skill recipes based on review findings.
   - Read-only with a circuit breaker preventing recursive governance reviews (Mulch never triggers a new review cycle).
   - Proposals are queued for the next session, not applied immediately.
   - Closes the feedback loop: reviews generate actionable governance improvements.

5. **7 Escalation Paths (up from 4)**:
   - Breeze → Trident (BLOCK escalation)
   - Gale → Trident
   - Gale → Maelstrom
   - Gale → Tempest
   - Trident partial → Maelstrom
   - Trident full → Maelstrom
   - Maelstrom → Tempest

6. **5 Review Modes (up from 3)**: Breeze < Gale < Trident < Maelstrom < Tempest.

7. **6 Prongs (up from 4)**: Spores, Mycelium, Roots, Thorns, Bedrock, Mulch.

**Impact on rules:** Upgraded `staff-review` SKILL.md with Breeze and Tempest protocols, Mycelium and Mulch prongs, 7 escalation paths, and the Tempest human gate. Updated documentation across README.md, COST_ANALYSIS.md, and EVOLUTION.md.

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
```

Compliance went from **7.8/10 to 9.8/10**, waste rate dropped from **~56% to 18.8% across 17 sessions (7,015 steps)**, with best-governed sessions reaching **1.1% waste** (`0dc37064` across 1,325 steps), and the rules now cover failure modes that no amount of upfront design would have predicted.

## Design Principles (Emerged, Not Prescribed)

1. **Evidence over intuition** — Every rule traces back to observed steps wasted. No rule exists "just in case."
2. **Accuracy over speed** — The agent must never sacrifice correctness to save tokens.
3. **Rules as a system** — Cross-references between rules are intentional. Providence §3 mandates read-before-write; refactoring-pilot operationalizes it as a phased workflow.
4. **Continuous validation** — Rules aren't "done" after review. Governance is a living system that evolves with each session.
