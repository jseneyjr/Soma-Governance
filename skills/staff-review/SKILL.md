---
name: Staff Review Protocol
description: Multi-lens review fan-out with staff-level synthesis. Activate when the user requests a comprehensive review, audit, or architectural assessment that benefits from orthogonal analysis perspectives.
trigger: user_request
---
# Staff Review Protocol

> **Role**: Orchestrates parallel expert reviews from independent perspectives, then synthesizes findings into a single fact-checked, actionable artifact. Use when the user requests a "full review", "architectural review", "audit", or any comprehensive quality assessment.

## Workflow

### Phase 1: Fan-Out (Independent Analysis)

Dispatch 2–3 **Flash-tier research subagents** with orthogonal review lenses. Each reviewer gets:
- A specific analytical focus (architecture, performance, security, etc.)
- Read access to all relevant files (enumerate explicitly in prompt)
- Structured output format requirements
- Independence constraint: reviewers must NOT see each other's findings

**Standard Lenses** (pick 2–3 based on request):

| Lens | Focus | When to Use |
|:-----|:------|:------------|
| **Architecture** | System structure, dependency graph, coverage gaps, configuration integrity, design debt | Always include for system-level reviews |
| **Performance** | Token costs, latency, resource overhead, quantitative ROI, optimization opportunities | When cost/efficiency matters |
| **Security** | OWASP Top 10, secrets exposure, input validation, auth flows, dependency vulnerabilities | When security is in scope |
| **Compliance** | Rule adherence, convention alignment, style consistency, documentation coverage | When governance/standards matter |
| **Behavioral** | Post-mortem waste patterns, rule effectiveness, agent behavior analysis | When reviewing agent sessions |
| **Domain Research** | External docs, wikis, papers, verified facts for the project domain | When external knowledge is needed for the review |
| **Spec Synthesis** | Cross-reference N artifacts → prioritized implementation plan | After reviews complete, before execution |
| **Visual** | Screenshot analysis, UI state, coordinate calibration, threshold tuning | For game automation or UI-heavy reviews |
| **Governance Audit** | Per-rule PASS/FAIL compliance check against session transcript | When verifying rule adherence mechanically |
| **Live Monitor** | Ongoing waste tracking with periodic probes and trajectory alerts | When a session needs real-time observation |

### Phase 2: Synthesis (Staff-Level Review)

After all reviewers report back, the **orchestrator** (not a subagent) performs the staff review:

1. **Cross-reference**: Identify findings that appear in multiple reviews (high confidence)
2. **Fact-check**: Verify quantitative claims against actual file sizes, step counts, or code
3. **Verification sweep**: Before drafting the final assessment, run a filesystem verification script confirming all reviewer assertions (file counts, byte sizes, trigger values, symlink targets). Do not trust reviewer math without mechanical confirmation.
4. **Reconcile conflicts**: When reviewers disagree, investigate and determine which is correct
4. **Incorporate context**: Fold in post-mortems, prior decisions, and architectural tenets
5. **Prioritize**: Rank findings by impact × effort, group into implementation tiers
6. **Produce**: One consolidated artifact with:
   - Verified findings (cross-referenced across reviews)
   - Single-reviewer findings (flagged as lower confidence)
   - Contradictions resolved with evidence
   - Actionable implementation plan sorted by priority

### Phase 3: Delivery

The final artifact follows feature-specs format:
- Problem statement with evidence
- Proposed changes grouped by component
- Implementation order (dependencies first)
- Verification criteria for each change
- Open questions requiring user input

## Continuous Review Mode (Coding Sessions)

For coding sessions exceeding ~75 steps, the orchestrator should dispatch lightweight Flash review probes at natural breakpoints instead of waiting for a batch review.

### When to Dispatch
- After completing a logical unit (feature, bugfix, refactor pass)
- Before any `git push`
- Every ~50 coding steps if no natural breakpoint occurred
- After any subagent delivers code that will be committed

### Probe Scope (Lightweight — NOT a full staff review)
The Flash reviewer receives:
1. List of files modified since last probe (`git diff --name-only`)
2. The actual diffs (`git diff`)
3. The project's test runner command

The reviewer checks:
- **Symbol consistency**: No hallucinated attributes/methods (e.g., `total_mem` vs `total_memory`)
- **Import validity**: All imports resolve to real modules
- **Blast radius**: Any public API changes that affect callers?
- **Test execution**: Run the test suite, report failures

### Probe Output
Structured findings: `{critical: [...], warnings: [...], clean: true/false}`
If critical findings exist, orchestrator must fix before continuing.

### Cost Budget
- Each probe: ~1,000 Flash tokens
- At 1 probe per 50 steps over a 500-step session: ~10,000 tokens total
- ROI: prevents 50-150 steps of rework (50,000-150,000 tokens saved)

## Specialist Skill Activation

When a staff review identifies that specialist analysis is needed, the orchestrator can activate dedicated skills as additional reviewers:

| Need | Skill | How |
|:-----|:------|:----|
| Domain knowledge gaps | `domain-researcher` | Dispatch with project context + specific questions |
| Multiple reports need consolidation | `spec-synthesizer` | Dispatch with artifact list + constraints |
| Active session needs monitoring | `session-monitor` | Activate with session ID + alert thresholds |
| Rule compliance unclear | `governance-auditor` | Dispatch with transcript path |
| Screenshot/UI evidence needed | `visual-analyst` | Dispatch with image paths |

Specialists run as **Flash subagents** and report back like standard reviewers. The orchestrator synthesizes their findings alongside the standard lens results. Specialists may also be activated independently outside of a staff review when the user requests their specific capability.

## Anti-Patterns

- **Don't dispatch a subagent for synthesis** — the orchestrator retains design authority and cross-cutting context that subagents lack
- **Don't let reviewers see each other's work** — independence prevents confirmation bias
- **Don't skip fact-checking** — reviewer claims must be verified against actual data before presenting to user
- **Don't fan out >4 reviewers** — diminishing returns; 4 orthogonal lenses catch ~98% of issues
- **Don't use inherit/pro for reviewers** — Flash is sufficient for read-only analysis; reserve heavyweight models for synthesis

## Model Selection

| Role | Model | Rationale |
|:-----|:------|:----------|
| Architecture reviewer | `flash` | Read-heavy, structured output |
| Performance reviewer | `flash` | Quantitative, file measurements |
| Security reviewer | `flash` | Pattern matching, checklist-based |
| Staff synthesizer | orchestrator (self) | Needs cross-cutting context, design authority, write access |

## Example Prompt Template for Reviewers

```
Perform a [LENS] REVIEW of [SYSTEM].

Read ALL of these files:
[explicit file list]

Deliver:
### 1. [Category]
[specific questions]

### 2. [Category]
[specific questions]

Provide specific evidence (file paths, line numbers, byte counts).
```
