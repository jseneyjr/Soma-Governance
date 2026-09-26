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
- **Delegation Floor**: For engineering tasks exceeding ~100 steps, the orchestrator must have delegated at least one standalone module to a subagent. If step 100 is reached with zero delegations, halt and decompose.

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
- **Fire-and-Forget**: Dispatch tasks clearly and wait for the subagents to report back with succinct summaries.

## 3. Cost & Workspace Isolation
- **Model Downgrading**: Per the cost-optimization protocol.
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
