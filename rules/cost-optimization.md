---
name: Cost & Token Optimization
description: Forces extreme token efficiency and cost-saving measures in AI output and subagent model selection.
trigger: always_on
---
# Token Efficiency Protocol

> **Role**: This rule enforces strict cost-optimization behaviors by minimizing unnecessary token consumption and prioritizing cheaper models for background tasks.

## 1. No Conversational Filler
- **Zero Fluff**: Skip pleasantries, restatements of the problem, and excessive explanations unless explicitly asked.
- **Never Sacrifice Accuracy**: Cost savings must never come at the expense of correctness. Never kill a research subagent early or skip codebase verification to save tokens. The providence governance rule always takes precedence. Engineering trade-off analyses (per architectural-tenets) and evidence citations (per providence) are essential deliverables, not conversational fluff.
- **Direct Answers**: Provide the solution or code immediately.

## 2. Diffs Only
- **Precise Edits**: Always use precise file editing tools (`replace_file_content` or `multi_replace_file_content`) to apply changes.
- **No Full File Outputs**: Never re-output entire functions or files in chat unless explicitly requested by the user.

## 3. Subagent Model Selection (Flash-Tier First)
- **Cost-Effective Delegation**: When spawning subagents for background research, web searches, or basic file reading, ALWAYS default to using the `flash` or `flash_lite` models rather than `pro` or `inherit`.
- **Reserve Pro**: Only use the `pro` model for subagents if the delegated task requires deep architectural reasoning or heavy refactoring.
- **Coding Subagents**: When delegating file-creation or code-writing tasks to subagents, use `inherit` model tier (not `flash`). Flash models are prone to analysis paralysis and may exhaust their steps on research without producing output.

## 4. Task Hygiene
- **Kill Stale Tasks**: Before spawning a new background command for a task you've already attempted, kill the previous hanging/timed-out task first.
- **No Task Accumulation**: Never allow more than 2 concurrent background tasks for the same logical operation. If a task times out, kill it and diagnose the root cause before retrying.
- **Heavy Model Concurrency Cap**: When spawning subagents with `inherit` or `pro` model tiers, limit to 2 concurrent subagents to avoid API rate limiting (HTTP 429). For trivial mechanical edits (adding attributes, single-line changes, boilerplate), prefer `flash` regardless of whether the task involves code.
