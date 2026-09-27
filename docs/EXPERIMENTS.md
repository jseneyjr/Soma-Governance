# Experiment Log

Lightweight A/B experiments on the governance system. Each experiment changes one variable, measures the impact, and either graduates to a rule or gets reverted.

## Active Experiments

| ID | Hypothesis | Change | Metric | Baseline | Status |
|:---|:-----------|:-------|:-------|:---------|:-------|
| E1 | Higher concurrency reduces wall-clock time without waste regression | Fan-out 3→4 readers, 2→3 writers | Waste rate | 1.0% (0dc37064) | 🔬 RUNNING |

## Experiment Backlog

Ideas to test. Pick the highest-signal, lowest-risk experiment next.

| ID | Hypothesis | Change | Expected Signal | Risk |
|:---|:-----------|:-------|:----------------|:-----|
| E2 | Pre-seeding domain context reduces research steps | Orchestrator sends project README + tech stack summary to every subagent prompt | Steps-to-first-useful-output | Low |
| E3 | Auto-activating session-preflight on coding projects catches env issues before step 10 | Add preflight dispatch to governance_init.sh for projects with venv/ | Steps wasted on env issues | Low |
| E4 | Requiring `make test` before ANY code commit (not just push) catches defects earlier | Tighten git-workflow §2 to pre-commit gate | Rework loop frequency | Medium — may slow down exploratory coding |
| E5 | Summarizing subagent findings in ≤5 bullet points reduces orchestrator context consumption | Add output cap to subagent prompt template | Orchestrator compaction frequency | Low |
| E6 | Dispatching a domain-researcher at session start for game projects eliminates mid-session wiki lookups | Auto-dispatch on project detection | Wiki/search steps after step 50 | Low |
| E7 | Running sweep_session.py as a review sentinel (instead of full Flash subagent) is 10x cheaper with 80% signal retention | Replace Flash sentinel with local Python scan | Cost per probe, defect catch rate | Medium — may miss nuanced issues |
| E8 | Caching taxonomy patterns in the orchestrator prompt reduces Flash subagent taxonomy lookups | Inline top-10 patterns in subagent prompts | Subagent file reads | Low |
| E9 | Proactive error classification in subagent prompts ("if you see X, it's probably Y") reduces diagnosis time | Add known-error catalog to incident-debug skill | Steps from error to root cause | Low |
| E10 | Limiting orchestrator thinking to 3 paragraphs before acting reduces decision latency | Add "think briefly, act quickly" to providence | Steps per decision cycle | Medium — may reduce quality |

## Completed Experiments

| ID | Hypothesis | Result | Graduated? |
|:---|:-----------|:-------|:-----------|
| — | — | — | — |

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
Use `governance_sweep.sh` to collect metrics. Compare against baseline.

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
4. **Governance overhead is <0.1% of session cost** — rules cost ~4,000 tokens/turn. A single prevented rework loop saves ~80,000 tokens. 
5. **Waste rate decreases over session length** — early setup steps have higher waste density than later productive steps. Sessions >500 steps converge toward true waste rate.
