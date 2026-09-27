---
name: Subagent Delegation Protocol
description: Enforces aggressive delegation to subagents to keep the main context window narrow and parallelize independent tasks.
trigger: always_on
---
# Delegation Protocol

> **Role**: This rule mandates that the agent act as an orchestrator, aggressively delegating isolated or repetitive tasks to subagents to protect the main context window.

## 1. Context Protection Mandate
- **Protect the Context Window**: The primary conversation's context window is expensive and should only contain high-level reasoning and coordination. 
- **Aggressive Delegation**: Do not perform long, context-heavy tasks yourself if they can be delegated. Spin up subagents for:
  1. Deep-diving into unfamiliar documentation or APIs.
  2. Broad codebase research or dependency mapping.
  3. Isolated refactors or boilerplate generation that do not require full system context.
  4. Bulk media triage, visual dataset exploration, or screenshot classification across >5 images.
- **Delegation Floor**: For engineering tasks exceeding ~75 steps, the orchestrator must have delegated at least one standalone module to a subagent. If step 75 is reached with zero delegations, halt and decompose.

## 2. Parallel Execution
- **Fan-Out Research**: When multiple independent research tasks exist, dispatch Flash subagents concurrently.
- **Fan-Out Implementation**: When approved changes touch disjoint file sets (no shared imports, no shared interfaces), dispatch coding subagents in parallel. Apply the Disjoint Lane Protocol:

### Disjoint Lane Protocol
Before parallelizing implementation:
1. **Map file ownership**: List every file each task will read or write
2. **Check intersection**: If any file appears in two tasks, serialize those tasks
3. **Check interface coupling**: If Task A modifies a function that Task B calls, serialize them
4. **Dispatch with explicit scope**: Each subagent prompt must list its owned files and explicitly state "do NOT modify files outside this list"
5. **Merge verification**: After all lanes complete, run the test suite once to catch integration issues

**Parallelizable** (disjoint files, no shared interfaces):
- Lane A edits `rules/git-workflow.md`, Lane B edits `rules/testing.md`, Lane C edits `rules/documentation.md`

**Must serialize** (shared interface):
- Task 1 adds parameter to `log_finding.sh` → Task 2 calls `log_finding.sh` from `governance_init.sh`

- **Review Sentinels**: For coding sessions exceeding ~75 steps, dispatch a lightweight Flash review probe after each logical unit of work. The probe reads recent diffs (`git diff`) and runs the test suite. This is NOT a full staff review — it's a 30-second sanity check that catches hallucinated symbols and regressions before they compound. See `staff-review` skill, Continuous Review section.
- **Concurrency Limits**: Fan out up to 4 read-only subagents (reviewers, researchers, auditors) concurrently. For coding lanes, limit to 3 concurrent writers with strict Disjoint Lane Protocol. Monitor waste rate — if it exceeds 8% after this change, revert to 2-3 concurrency.
- **Fire-and-Forget**: Dispatch tasks clearly and wait for the subagents to report back with succinct summaries.

### Context Pre-Seeding Protocol
Every subagent prompt should prepend a compact context block (~200 tokens) to eliminate cold-start exploratory steps:

```
<!-- CONTEXT: [PROJECT_NAME] -->
[PROJECT]: <Name> — <1-sentence core purpose>
[STACK]: <Language> | <Key libs> | Test: `<test_command>`
[LAYOUT]:
  - `<dir>/`: <3-word role>
[CONSTRAINTS]:
  - <Critical invariant or known trap>
[OUTPUT]: Max 5 bullets per section. Cite file:line.
<!-- END CONTEXT -->
```

**Rules**:
- Keep under 250 tokens — key-value structure, not prose
- Paths only, never inline file contents
- Include known traps to prevent rework (e.g., "Do NOT use ast.parse for linting")
- Include test runner command so subagents can verify immediately

## 3. Cost & Workspace Isolation
- **Model Tiering**: See `cost-optimization.md §3` for the authoritative model selection protocol. Key rules:
  - All review prongs (Spores through Mulch): `flash`
  - Coding subagents: `inherit`
  - Synthesis and design authority: orchestrator only
- **Branch Workspaces**: Only use `branch` workspace mode for subagents performing genuinely destructive operations (e.g., deleting files, rewriting core modules). The orchestrator must obtain user confirmation on the plan *before* dispatching destructive work to a subagent. For additive tasks like creating new files, writing tests, or generating boilerplate, use the default `inherit` workspace mode so files land directly in the project.

## 4. Coding Task Boundaries
- **Delegate Only Independent Work**: For coding tasks, only delegate to subagents when the changes are fully independent with no shared interfaces or imports. Never delegate architectural decisions or tightly-coupled edits to subagents.
- **Orchestrator Retains Design Authority**: The primary conversation must retain all integration work, API contract decisions, and cross-module coordination. Subagents execute; they do not design.
- **Workspace Conflict Prevention**: While a subagent is actively reading, testing, or modifying specific files, the orchestrator must not modify those same files or their public contracts. Wait for the subagent to report back, or kill the subagent before making conflicting changes.
- **Disjoint File Ownership**: If two delegated sub-tasks touch the same target file, sequence them serially. Never dispatch parallel subagents that write to the same file.

## 5. Subagent Reporting
- **Structured Debrief**: When completing a task as a subagent, always report back with: (1) files created/modified, (2) what succeeded, (3) what failed or was skipped, and (4) any assumptions made.
- **No Silent Completions**: Never report "done" without listing concrete deliverables.
- **Prompt Cleanup**: Kill completed subagents immediately upon receiving their completion debrief rather than deferring to a batch kill_all. If zero files were produced, explicitly state that and explain why.
- **No Collateral Kills**: Never use `kill_all` when sibling subagents from the same fan-out are still running. Kill only the completed subagent by its `ConversationId`. Premature `kill_all` forces the orchestrator to redo in-flight work manually.
- **Read-Only Awareness**: Research subagents cannot write files. Instruct them to return results via `send_message`, not file creation. Only subagents with write tools can create or modify files.
- **Mulch Execution Invariant**: In Tempest reviews, Mulch must be dispatched as an unskippable post-Bedrock learning extraction step. If Mulch is omitted, the orchestrator must explicitly document the omission rationale before session close. Mulch output should be persisted to `governance/mulch_queue.jsonl` for cross-session learning.

## 6. Boundary Verification Protocol
Before acting on subagent findings, the orchestrator **must spot-check claims against the actual codebase** (not exhaustively — protect context window):
- **File existence**: Confirm cited file paths exist (`list_dir` or `view_file`)
- **Line accuracy**: Verify cited content exists within ±5 lines of the claimed location (LLMs commonly drift by 1–3 lines)
- **Symbol validity**: Verify function/class names exist where claimed (`grep_search`)
- **Numeric claims**: Independently verify any aggregate math (sums, percentages, counts)
- **Omission claims**: Findings about *missing* code (e.g., no auth middleware, no rate limiting) cannot cite a file:line. Accept these if the subagent specifies *where* the check should exist and a grep confirms absence.

If a finding fails verification after fuzzy locality search, demote it to ℹ️ info (not silent discard) and flag the subagent's report as partially ungrounded. Never propagate unverified claims downstream — hallucinations compound across agent boundaries.

## 7. Orthogonal Persona Mandate
When dispatching 2+ review subagents in the same phase, assign **conflicting analytical incentives**:
- ❌ **Banned**: 3 reviewers all tasked with "review this code for issues"
- ✅ **Required**: Orthogonal lenses (e.g., correctness verifier, performance minimalist, adversarial red-team)

Homogeneous reviewers converge on the same findings via consensus bias, wasting tokens. Orthogonal personas with different success criteria (one rewarded for finding waste, another for finding bugs, another for finding security issues) maximize coverage per token spent.

**Exception**: High-assurance single-domain subsystems (cryptography, auth pipelines) may use multiple same-domain lenses exploring different attack vectors. The orchestrator serves as the arbiter when reviewers conflict.

