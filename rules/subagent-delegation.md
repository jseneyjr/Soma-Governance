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

## 2. Parallel Execution
- **Fan-Out Tasks**: When multiple independent tasks must be done (e.g., updating 5 unrelated files, researching 3 different libraries), always spin up multiple subagents concurrently rather than executing sequentially.
- **Fire-and-Forget**: Dispatch tasks clearly and wait for the subagents to report back with succinct summaries.

## 3. Cost & Workspace Isolation
- **Model Downgrading**: Per the cost-optimization protocol.
- **Branch Workspaces**: Only use `branch` workspace mode for subagents performing genuinely destructive operations (e.g., deleting files, rewriting core modules). For additive tasks like creating new files, writing tests, or generating boilerplate, use the default `inherit` workspace so files land directly in the project.

## 4. Coding Task Boundaries
- **Delegate Only Independent Work**: For coding tasks, only delegate to subagents when the changes are fully independent with no shared interfaces or imports. Never delegate architectural decisions or tightly-coupled edits to subagents.
- **Orchestrator Retains Design Authority**: The primary conversation must retain all integration work, API contract decisions, and cross-module coordination. Subagents execute; they do not design.
