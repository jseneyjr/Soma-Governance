# Gemini Steering Rules

A battle-tested set of global steering rules for AI coding assistants (Gemini / Antigravity). Designed by a senior software architect prioritizing **accuracy** and **cost optimization**.

## What's Included

| Rule | Trigger | Purpose |
|:-----|:--------|:--------|
| `providence.md` | always_on | **Highest priority.** Codebase grounding, claim verification, no hallucinations, no silent workarounds, venv safety. |
| `cost-optimization.md` | always_on | Token efficiency, subagent model tier selection, task hygiene. |
| `polyglot-standards.md` | always_on | Unified entrypoints (Makefiles), containerization with carve-outs for scripts. |
| `subagent-delegation.md` | always_on | Context window protection, parallel execution, coding task boundaries. |
| `architectural-tenets.md` | model_decision | Pragmatism over purity, explicit trade-off analysis, scale-to-zero preferences. |
| `feature-specs.md` | model_decision | PRD structure, acceptance criteria, documentation deliverables. |
| `testing.md` | model_decision | Behavioral testing, sad paths, minimal mocking, CLI/script testing. |
| `documentation.md` | model_decision | ADRs, actionable READMEs, Mermaid diagrams, high-signal comments. |
| `destructive-ops.md` | model_decision | Dry-run mandates and cost warnings for infrastructure-as-code. |

### Trigger Types

- **`always_on`**: Loaded into context on every turn. These are your non-negotiable governance rules.
- **`model_decision`**: The model sees the name and description but only loads the full content when it determines the rule is relevant. Zero cost until needed.

## Installation

### Quick Install

```bash
# Clone the repo
git clone https://github.com/<your-username>/gemini-steering-rules.git

# Copy rules to your global Gemini config
mkdir -p ~/.gemini/config/rules
cp gemini-steering-rules/rules/*.md ~/.gemini/config/rules/
```

### Symlink Install (stay synced with `git pull`)

```bash
git clone https://github.com/<your-username>/gemini-steering-rules.git ~/gemini-steering-rules

# Symlink the entire rules directory
ln -sf ~/gemini-steering-rules/rules ~/.gemini/config/rules
```

## Customization

These rules are opinionated. Fork and adjust to your preferences:

- **Cost tolerance**: Edit `cost-optimization.md` to adjust subagent model tiers or task limits.
- **Tech stack**: Edit `polyglot-standards.md` to change your preferred entrypoint format (Makefile vs Justfile vs package.json).
- **Architecture style**: Edit `architectural-tenets.md` to match your infrastructure preferences.
- **Priority hierarchy**: `providence.md` is declared as the highest-priority rule. All other rules defer to it.

## Design Philosophy

1. **Accuracy over speed** — The agent must never sacrifice correctness to save tokens.
2. **Cost-aware** — Minimize token consumption through precise edits, smart subagent delegation, and conditional rule loading.
3. **Battle-tested** — Every rule in this set was derived from real failure patterns observed in production coding sessions.

## License

MIT — use however you like.
