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
- **Fan-Out Tasks**: When multiple independent tasks must be done (e.g., researching 3 libraries with `flash`, or batching file edits within the heavy-model concurrency cap), spin up subagents concurrently rather than executing sequentially.
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
