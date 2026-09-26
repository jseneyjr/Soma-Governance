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

### Phase 2: Synthesis (Staff-Level Review)

After all reviewers report back, the **orchestrator** (not a subagent) performs the staff review:

1. **Cross-reference**: Identify findings that appear in multiple reviews (high confidence)
2. **Fact-check**: Verify quantitative claims against actual file sizes, step counts, or code
3. **Reconcile conflicts**: When reviewers disagree, investigate and determine which is correct
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

## Anti-Patterns

- **Don't dispatch a subagent for synthesis** — the orchestrator retains design authority and cross-cutting context that subagents lack
- **Don't let reviewers see each other's work** — independence prevents confirmation bias
- **Don't skip fact-checking** — reviewer claims must be verified against actual data before presenting to user
- **Don't fan out >3 reviewers** — diminishing returns; 2 orthogonal lenses catch 90% of issues
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
