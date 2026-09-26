# AI Steering Rules

Battle-tested governance rules for AI coding assistants — forged from 5,800+ steps of real failures across 7 sessions, refined through 9 review phases, and enforced via lifecycle hooks.

## Why Use This?

- **Stop AI from guessing** — Rules force the agent to verify claims against your actual codebase before acting
- **Cut token costs ~63%** — Conditional loading, smart subagent delegation, and task hygiene eliminate wasted steps
- **Mechanically enforced** — Lifecycle hooks gate destructive operations, inject governance context, and capture logs automatically
- **Cross-platform** — Works with Gemini/Antigravity (Google), Kiro (AWS), and GitHub Copilot (Microsoft)
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

### Hooks (3 lifecycle hooks)

Hooks enforce governance mechanically — they don't rely on the model remembering rules.

| Hook | Event | What It Does |
|:-----|:------|:-------------|
| `governance-monitor` | `PreInvocation` | On session start (and every 100th turn): exports logs, checks for pending governance proposals, injects reminder if found. |
| `safety-gate` | `PreToolUse` | Gates destructive `run_command` calls (`rm -rf /`, `git push -f`, `DROP TABLE`). Returns `force_ask` for dangerous patterns. |
| `session-close` | `Stop` | Exports conversation logs and syncs both repos when any session ends. No data loss even on crashes. |

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

## How This Approach Evolved

These rules weren't designed in a vacuum. They were extracted from real failures, refined through staff-level review, and continuously validated against live coding sessions. Here's how the approach changed — and how each shift reshaped the rules.

### Phase 1: Prescriptive Rules ("Write what sounds right")

The first version was 4 `always_on` rules and 4 flat-checklist skills, written from best practices and intuition. Providence said "don't hallucinate." Cost-optimization said "use Flash for research." Testing said "test sad paths."

**What we learned:** Prescriptive rules are necessary but insufficient. The agent followed the letter of the rules while violating the spirit — it would "verify" by re-reading the same file 4 times, or "delegate" by spawning a Pro-tier subagent for a 3-line edit.

**Impact on rules:** Led to the **3 formal review iterations** (21 findings), which caught contradictions between rules (cost-optimization vs. providence on trade-off analysis), missing coverage (destructive-ops only covered IaC, not git/filesystem), and ambiguous terminology (`inherit` meant both model tier and workspace mode).

### Phase 2: Evidence-Based Evolution ("Extract rules from real failures")

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

### Phase 3: Cross-Conversation Discovery ("Same failures, different projects")

Analyzing a single session was revealing. Analyzing **all sessions** showed which patterns are systemic:

| Pattern | Dwarf Fortress (1,579 steps) | TAB AI (1,551 steps) | Steering (856 steps) |
|:--------|:---:|:---:|:---:|
| Hallucinated controls | ✅ 160 steps | ✅ 180 steps | — |
| Venv/path confusion | ✅ | ✅ | — |
| Zero subagent delegation | ✅ 0 subagents, 17 compactions | Improved | Heavy use |
| Bulk media context pollution | — | ✅ 127 files in brain | — |
| Open-loop state desync | ✅ spacebar seizure | — | — |
| Desktop automation safety breach | ✅ clicked through Steam | — | — |
| Premature framework extraction | ✅ 150 steps on unused SDK | — | — |
| Architectural pivot churn | ✅ 8 paradigm shifts | — | — |

The Dwarf Fortress session was the most catastrophic: **1,579 steps, 8 architectural pivots, 2 safety incidents (blind desktop clicking + PyAutoGUI crash), and zero subagent delegation.** It burned an estimated 8M tokens and produced zero working autonomous runs.

**Impact on rules:** This phase added 5 entirely new governance areas — desktop automation safety, premature abstraction bans, pivot discipline, delegation floors, and real-time loop budgets. These aren't theoretical; they're extracted from watching the same agent make the same category of mistake across independent projects.

### Phase 4: Continuous Governance ("Rules that improve themselves")

The final shift was from periodic review to continuous monitoring. A background cron job now:
1. Tails new steps from active conversations every 10 minutes
2. Cross-references behavior against all 9 rules and 7 skills
3. Stages proposed rule changes for human approval
4. Updates the scorecard and pushes to the repo

This caught 7 additional findings that manual review missed — including the insight that copying files into Antigravity's brain scratch directory pollutes checkpoint metadata (a platform-specific behavior no prescriptive rule would have anticipated).

**Impact on rules:** The monitor workflow itself generated governance improvements: approval-gated changes (don't auto-mutate global config), post-report tracker updates (don't skip steps on analyst failure), and prompt subagent cleanup (don't accumulate zombies).

### The Compound Effect

Each phase built on the last:

```
Prescriptive Rules → caught obvious gaps but missed real failure modes
    ↓
Evidence-Based → extracted rules from 1,339 steps of real waste
    ↓
Cross-Conversation → proved patterns are systemic, not one-off
    ↓
Continuous Monitor → catches new patterns as they emerge
```

The result: compliance went from **7.8/10 to 9.7/10**, waste rate dropped from **~56% to ~10%**, and the rules now cover failure modes that no amount of upfront design would have predicted.

### Design Principles (Emerged, Not Prescribed)

These weren't declared at the start — they crystallized through the evolution:

1. **Evidence over intuition** — Every rule traces back to observed steps wasted. No rule exists "just in case."
2. **Accuracy over speed** — The agent must never sacrifice correctness to save tokens. Cost-optimization explicitly defers to providence on trade-off analyses.
3. **Rules as a system** — Cross-references between rules are intentional. Providence §3 mandates read-before-write; refactoring-pilot operationalizes it as a phased workflow. Neither works alone.
4. **Continuous validation** — Rules aren't "done" after review. The live monitor treats governance as a living system that evolves with each session.

## Staff Review Scorecard

This rule set has been through **3 formal review iterations**, a **1,339-step session post-mortem**, a **skills modernization pass**, **continuous live monitoring**, a **1,579-step cross-conversation backfill**, and an **architectural redesign to hooks** — each performed by independent AI reviewers.

### Compliance Score (tested against a live 1,339-step coding session)

| Dimension | Before | After | Key Fixes |
|:----------|:------:|:-----:|:----------|
| Providence & Governance | 6.5 | 9.5 | External evidence, plan adherence, fail-fast validation, assumption surfacing, UI grounding gate, symbol collision guard, refactoring sweep, data ingestion filter |
| Cost Optimization | 9.5 | 10 | Concurrency cap, tier consolidation, scratch hygiene, bulk media delegation |
| Subagent Delegation | 8.5 | 9.5 | Read-only awareness, workspace conflict prevention, destructive delegation, media triage offload |
| Root Cause Resolution | 9.5 | 9.5 | No changes needed — agent fixed all 6 code review findings |
| Execution Discipline | 6.0 | 9.5 | Phase gates, checkpoint testing, mock-first mandate, venv binding |
| **Overall** | **7.8** | **9.8** | **58 findings fixed across all phases** |

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
| **Hooks Redesign** | Architectural review | 8 | 8 | PreInvocation governance init, PreToolUse safety gate, Stop log export, symlinks (zero drift), persistent state, cross-session memory |
| **Backfill 2** | 7 sessions (5,800+ steps total) | 5 | 5 | No collateral kills, deliverable-first mandate, micro-prototyping cap, sandbox awareness, metric rationalization ban |
| **Total** | | **62** | **58** | 4 skipped were intentional design decisions |

## Development History

This governance suite was built, tested, and continuously refined across 4,700+ steps of real coding sessions.

### Process Metrics

| Metric | Value |
|:-------|:------|
| Total steps analyzed across all sessions | 5,800+ |
| Sessions analyzed | 7 (Dwarf Fortress, TAB AI, Steering Rules, 4 mid-size) |
| Review phases | 9 (3 formal + post-mortem + skills modernization + live monitor + 2 backfills + hooks redesign) |
| Total findings | 62 |
| Findings fixed | 58 (4 skipped as intentional design decisions) |
| Subagents used for reviews | 17+ (all Flash tier) |
| Lifecycle hooks deployed | 3 (PreInvocation, PreToolUse, Stop) |
| Conversations archived | 14 (private repo) |

### What Worked

- **Flash subagents for reviews**: Independent reviewers at negligible cost saved the main context from 350K+ tokens of file reading
- **Dual reviewer fan-out**: Compliance auditor + gap analyst concurrently — each caught findings the other missed
- **Cross-conversation backfill**: Analyzing the Dwarf Fortress session (never previously reviewed) surfaced 5 entirely new pattern categories
- **Hooks over cron**: Replacing the ephemeral in-session cron with lifecycle hooks eliminated the "governance dies with session" problem entirely
- **Symlinks over copies**: Eliminated the manual cp → git push sync cycle that caused drift 3 times in one session

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
