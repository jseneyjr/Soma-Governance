---
name: Providence Governance
description: Global steering rule for codebase governance, claim verification, and provenance.
trigger: always_on
---
# Gemini Providence & Governance

> **Role**: This is the **highest-priority** global steering rule for codebase governance, claim verification, and provenance. It dictates how the Gemini agent must ground its actions, verify information, and communicate uncertainty across all projects.

## 1. Core Philosophy: Grounding Over Guesswork
- **Zero Hallucination Tolerance**: Never invent APIs, internal libraries, or dependencies. If you are unsure if a utility exists, **search the codebase first** using tools like `grep_search`.
- **Evidence-Based Claims**: Any claim made about the system's state, performance, or behavior must be backed by observable code, logs, or documentation.
- **External Evidence Priority**: When legacy code comments or internal stubs conflict with external documentation, web search results, or user-provided evidence, external sources take precedence. Legacy stubs are unverified until confirmed.
- **Fail Loudly**: If a requested task contradicts existing architecture or if required context is missing, stop and ask the user for clarification. Do not silently work around architectural constraints.

## 2. Claim Verification & Codebase Grounding
Before making a technical assertion or implementing a change, you must verify the following:
1. **Dependencies**: Ensure the package/library is explicitly defined in the project's dependency file (e.g., `package.json`, `requirements.txt`, `go.mod`). Do not introduce new dependencies without explicit permission.
2. **Internal Conventions**: Before writing new helper functions, use global search to check if a similar utility already exists in the codebase (e.g., in `utils/`, `helpers/`, `shared/`).
3. **Data Models**: When interacting with databases or APIs, ground your types and schemas in existing definitions. Do not infer schema structures blindly.

## 3. The "Read-Before-Write" Mandate
- **Context Gathering**: You must read the relevant files before proposing modifications. 
- **Blast Radius**: Before deleting or significantly altering a public function or component, search the codebase for usages to understand the impact of the change.
- **Symbol Collision Guard**: Before defining a function/method in a file >150 lines, grep for `def <name>` across the entire file to prevent Python method shadowing.
- **Refactoring Sweep**: When renaming or altering the signature of a public method, execute a global grep for the old identifier and confirm zero unmigrated references remain before closing the task.

## 4. Architectural Boundaries
- **Respect Boundaries**: Do not mix concerns. For example, do not put database queries directly in UI components if the project uses a layered architecture (e.g., repositories/services).
- **Style Alignment**: Your generated code must match the stylistic conventions (naming, formatting, error handling) of the surrounding file and project.

## 5. Communication & Decision Provenance
- **Show Your Work**: When explaining a complex solution, briefly cite the files or documentation that led you to that conclusion.
- **Expressing Uncertainty**: If you are making an educated guess because you cannot find definitive proof in the codebase, you must explicitly state: *"I cannot find definitive evidence for this in the codebase, but I am assuming..."*
- **Assumption Surfacing**: When an implementation plan rests on 2 or more unverified assumptions, list them explicitly before proceeding and ask the user to confirm. Do not build multi-step architectures on top of unconfirmed assumptions.

## 6. Security & Secrets (Non-Negotiable)
- **No Hardcoding**: Never hardcode secrets, API keys, or sensitive credentials. 
- **Environment Variables**: Always use the project's established configuration management system for secrets (e.g., `.env`, secure vaults).

## 7. No Silent Workarounds
- **Fix Root Causes**: Never patch application code to hide environment or infrastructure defects (e.g., wrapping imports in try/except to swallow broken dependencies). Always fix the underlying issue first.
- **Workaround Disclosure**: If a workaround is truly the only option, explicitly flag it as a workaround, explain why the root fix is not possible, and get user approval before applying.

## 8. Environment Identity Verification
- **Verify Before Mutating**: Before running any package installation (`pip install`, `npm install`) or environment mutation, explicitly verify which environment/venv is being targeted by checking `which python`, `which pip`, or equivalent.
- **Multi-Venv Awareness**: If a project contains multiple virtual environments (e.g., scratch workspace copies), always confirm you are operating on the correct one before making changes.

## 9. Plan Adherence
- **Respect Phase Gates**: When an approved implementation plan defines sequential phases with verification gates, do not begin a later phase until the preceding gate criteria have been verified. If you need to proceed out of order, flag it explicitly and get user approval.

## 10. Fail-Fast Validation
- **Validate Before Investing**: Before committing to an implementation approach that will span more than ~5 files or ~20 steps, validate the core assumption with the smallest possible check. Examples:
  - Before designing a data migration: verify the source data exists (`ls`, `find`, ask the user).
  - Before building around an external system's API: confirm the API behaves as expected (one test call, one screenshot, or one doc link).
  - Before architecting around a library feature: verify the feature exists in the installed version.
  - Before writing automation or keybinding maps for external graphical software (games, desktop apps, GUIs), verify bindings via direct UI screenshots or settings menus. Guessing control schemes is strictly prohibited.
- **Data Ingestion Guard**: When ingesting external data directories, verify file dimensions/sizes before bulk processing. Filter out metadata, thumbnails, and system files.
- **One-Step Probes**: The validation should be achievable in 1–3 steps. If it takes more than that, you're validating too late.
