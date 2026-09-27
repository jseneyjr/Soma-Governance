# Experiment Log

Lightweight A/B experiments on the governance system. Each experiment changes one variable, measures the impact, and either graduates to a rule or gets reverted.

## Active Experiments

| ID | Hypothesis | Change | Metric | Baseline | Risk | Status |
|:---|:-----------|:-------|:-------|:---------|:-----|:-------|
| E14 | A zero-token local hook script checking git diff line count, dependency depth, and sensitive directory patterns will accurately recommend protocol escalation (Breeze→Trident→Maelstrom/Tempest) | Add auto-escalation sentinel hook | Escalation precision (true positive rate); escape defect count on un-escalated commits | — | Low-Medium | 🔬 TESTING (Sentinel + Phase Gate implemented — `scripts/escalation_sentinel.sh` + `providence.md §9`) |
| E15 | Persisting Mulch proposals to `mulch_queue.jsonl` and surfacing repeated patterns at session start via governance_init.sh will increase rule evolution velocity by 3x | Add Mulch accumulator pipeline | Days/sessions from defect occurrence to rule ratification; proposal discard rate | — | Low | ✅ VALIDATED (Critical Need — Write-Only; Consumer E16 Pending) |
| E11 | Delegating multi-prong orchestration to a dedicated review_orchestrator subagent will reduce parent context growth by >70% without reducing defect catch rate | Add review_orchestrator subagent type | Parent token delta per review; critical finding parity vs manual baseline | — | Medium-High | 🔬 TESTING (Breeze POC passed — nesting via `enable_subagent_tools` confirmed) |
| E16 | Consuming pending patterns from `governance/mulch_queue.jsonl` in `governance_init.sh` PreInvocation alert will eliminate cross-session anti-pattern recurrence (completes E15 read path) | Wire `mulch_queue.jsonl` parser into `governance_init.sh` | Days from Mulch proposal to ratification; recurrence rate of logged anti-patterns | — | Low | 🔬 PROPOSED |
| E17 | Capping review escalation at max 2 Tempests per session prevents review paralysis and context exhaustion (observed: 29 checkpoints in 4-Tempest session, diminishing returns after Tempest #1) | Add "Max 2 Tempests/Session" guideline to `staff-review/SKILL.md`; enforce via orchestrator self-check | Context checkpoint count; findings-per-dispatch ratio per Tempest number | — | Low | 🔬 PROPOSED |
| E18 | A structured 4-stage codebase scan (Genesis: Cartography→Chronicle→Codex→Compass) at first contact reduces cold-start exploration steps by >60% in subsequent sessions | Add `skills/genesis/SKILL.md` | Steps spent on codebase exploration in first 50 steps of new-repo sessions | ~15–25 exploration steps per new repo (estimated from 66 work sessions) | Low | 🔬 PROPOSED |
| E19 | Injecting domain-specific personas (e.g., "Security Compliance Reviewer", "API Contract Architect") into Spores scouts increases finding relevance by >30% | Add `domain_personas.md` config to `skills/staff-review/` | Ratio of actionable findings to total findings per Spores round | Unknown (needs measurement) | Low-Medium | 🔬 PROPOSED |
| E20 | Automatically distilling key decisions, traps, and patterns from completed sessions into a per-project institutional memory file reduces re-discovery of known issues | Add post-session distillation step to `session_close.sh` | Steps spent re-diagnosing previously-solved issues | Multiple sessions re-discovered same traps across 66-session dataset | Low | 🔬 PROPOSED |
| E21 | `define_subagent` with `enable_subagent_tools` can nest 3 levels deep (parent→orchestrator→scout→sub-scout) without platform errors | Live proof-of-concept dispatch | Success/failure, latency, context propagation accuracy | E11 validated 2-level nesting | Low | 🔬 PROPOSED |
| E22 | Having the agent review its OWN session transcript mid-session (every ~100 steps) catches drift patterns that continuous review probes miss | Add self-review checkpoint to `session-monitor` skill | Drift corrections caught by self-review vs external review | 0 (no self-review currently) | Low | 🔬 PROPOSED |

## Experiment Backlog

Ideas to test. Pick the highest-signal, lowest-risk experiment next.

| ID | Hypothesis | Change | Expected Signal | Risk |
|:---|:-----------|:-------|:----------------|:-----|
| E4 | Requiring `make test` before ANY code commit (not just push) catches defects earlier | Tighten git-workflow §2 to pre-commit gate | Rework loop frequency | Medium — may slow down exploratory coding |
| E5 | Summarizing subagent findings in ≤5 bullet points reduces orchestrator context consumption | Add output cap to subagent prompt template | Orchestrator compaction frequency | Low |
| E7 | Running sweep_session.py as a review sentinel (instead of full Flash subagent) is 10x cheaper with 80% signal retention | Replace Flash sentinel with local Python scan | Cost per probe, defect catch rate | Medium — may miss nuanced issues |
| E8 | Caching taxonomy patterns in the orchestrator prompt reduces Flash subagent taxonomy lookups | Inline top-10 patterns in subagent prompts | Subagent file reads | Low |
| E9 | Proactive error classification in subagent prompts ("if you see X, it's probably Y") reduces diagnosis time | Add known-error catalog to incident-debug skill | Steps from error to root cause | Low |
| E10 | Limiting orchestrator thinking to 3 paragraphs before acting reduces decision latency | Add "think briefly, act quickly" to providence | Steps per decision cycle | Medium — may reduce quality |

## Completed Experiments

| ID | Hypothesis | Result | Graduated? |
|:---|:-----------|:-------|:-----------|
| E1 | Higher concurrency reduces wall-clock time without waste regression | Fan-out raised to 4 readers / 3 writers. Waste held at [1.1%](METRICS.md#live-ab-validation) across 1,325 steps; wall-clock time improved ~2x on parallel lanes. | ✅ Yes — graduated to `subagent-delegation.md §2` |
| E2 | Pre-seeding domain context reduces research steps | Context Pre-Seeding (~200 tokens/dispatch) eliminated 2–3 exploratory steps per subagent (~8k–12k tokens saved). See [METRICS.md](METRICS.md#conditional-loading-roi). | ✅ Yes — graduated to `subagent-delegation.md §2` (Context Pre-Seeding Protocol) |
| E3 | Auto-activating session-preflight on coding projects catches env issues before step 10 | Auto-preflight in `governance_init.sh` prevented 40–120 steps of venv/env drift per session. Zero false triggers across 17 sessions. See [METRICS.md](METRICS.md#conditional-loading-roi). | ✅ Yes — graduated to `governance_init.sh` hook |
| E6 | Dispatching domain-researcher at session start for game projects eliminates mid-session wiki lookups | Domain detection in `governance_init.sh` reduced wiki/search steps by ~90% after step 50. Desktop automation guessing dropped from [255 steps](METRICS.md#top-waste-sources-ranked) to near-zero in governed sessions. | ✅ Yes — graduated to `governance_init.sh` domain hints |

---

## How to Run an Experiment

### 1. Pick
Choose the highest-signal experiment from the backlog. Prefer:
- **Low risk** over high risk
- **Easy to measure** over hard to measure
- **Easy to revert** over hard to revert

### 2. Define
Before starting, write:
```
Experiment: E[N]
Hypothesis: [one sentence]
Change: [exactly what gets modified — file, line, value]
Metric: [what number to track]
Baseline: [current value of that metric]
Duration: [N sessions or N steps]
Revert trigger: [when to abort]
```

### 3. Apply
Make the smallest possible change. One variable only — never bundle experiments.

### 4. Measure
Use `governance_sweep.sh` to collect metrics. Compare against baseline. Reference [METRICS.md](METRICS.md) for current baselines.

### 5. Decide
| Outcome | Action |
|:--------|:-------|
| Metric improved, no regression | Graduate to permanent rule change |
| Metric neutral | Revert (not worth the complexity) |
| Metric regressed | Revert immediately |
| Inconclusive (too few data points) | Extend duration |

### 6. Log
Move from Active → Completed with result and decision.

---

## Insight Capture

When an experiment (or a sweep, or a post-mortem) surfaces a non-obvious insight, log it here:

### Insights
1. **Mental runtime trace > brute-force execution** — `0dc37064` caught 2 critical blockers via mental simulation that `5dd84eed` hit at runtime after 188 steps. Cost: ~5 Flash steps. Savings: ~180 steps.
2. **Flash-only subagents eliminate the #1 cost driver** — `5dd84eed` used Opus for a 100-line script. `0dc37064` used 100% Flash. Credit savings: 88%.
3. **ast.parse as lint target is a persistent footgun** — appears in every TAB AI session. Removing it from the Makefile is more durable than relying on the agent to resist it.
4. **Governance overhead is <0.1% of session cost** — rules cost ~3,750 tokens/turn always-on. A single prevented rework loop saves ~80,000 tokens. 
5. **Waste rate decreases over session length** — early setup steps have higher waste density than later productive steps. Sessions >500 steps converge toward true waste rate.
6. **Schema bifurcation is now fixed** — Polymorphic extraction handles both flat and nested log formats. Baseline measurements from pre-fix sessions should be re-evaluated against the corrected extractor.
7. **Subagent nesting eliminates orchestration overhead** — `enable_subagent_tools: true` allows review orchestrators to dispatch their own scouts. Parent context consumption drops to 1 turn (dispatch + receive) per review cycle. (E11, Phase 10)
8. **Thorns adversarial testing catches ~60% defective fixes** — In the Maelstrom POC, 8/13 proposed fixes were broken or weakened. Without Thorns, 3 critical security defects would have shipped. (Phase 10)
9. **Sequential Tempests show diminishing returns** — Tempest #1 found 7 critical breaks; Tempests #2–#4 found 0 functional issues. Cap at 2 Tempests/session. (E17, Phase 10)
10. **Phase inversion is the highest-cost failure mode** — `f8b82d61` launched 3 coding lanes while 5 research scouts were active. 16 files of dead code were written against an obsolete architecture. Led to E14 phase gate rules. (Phase 10)
11. **Partial-fidelity installation is a silent governance failure** — `make install` for one platform target deployed 11 rules but 0 skills. Rules referenced review protocols (Spores→Mulch) that were absent on disk. `make doctor` reported all-green because it only checked rules. Production code shipped without any review protocol. (Phase 11, 66-session field validation)
12. **Delegation evolves from context-saving to second-opinion** — Across 66 production sessions, subagent delegation progressed from zero (sessions 1–24), through selective context-gathering (25–53), to full orchestrated review with 14 subagents (session 53). However, delegation was NEVER used for adversarial second opinions until governance skills were installed. (Phase 11)
13. **Pre-governance agents re-discover the same traps across sessions** — Multiple sessions independently hit the same environmental constraints (older shell version, cherry-pick vs merge confusion, stale branch state) without any cross-session memory. This directly motivates E20 (Conversation Memory Distillation). (Phase 11)
14. **Unbounded file ingestion is a universal cold-start failure** — Session 001 crashed in 7 seconds by reading a 141KB git diff without line limits. This pattern repeats across codebases and is not specific to any domain or toolchain. (Phase 11)
