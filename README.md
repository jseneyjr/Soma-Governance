# AI Steering Rules

Battle-tested governance rules for AI coding assistants — forged from 5,300+ steps of real failures across 8 sessions, refined through 10 review phases, and enforced via lifecycle hooks.

## Why Use This?

- **Stop AI from guessing** — Rules force the agent to verify claims against your actual codebase before acting
- **Cut token costs ~65%** — Conditional loading, smart subagent delegation, and task hygiene eliminate wasted steps ([methodology](docs/COST_ANALYSIS.md))
- **Mechanically enforced** — Lifecycle hooks gate destructive operations, inject governance context, and capture logs automatically
- **Cross-platform** — Works with Gemini/Antigravity (Google), Kiro (AWS), and GitHub Copilot (Microsoft)

## Quick Start

> **Prerequisites:** `git` and one of: [Gemini/Antigravity](https://github.com/google-gemini/antigravity), [Kiro](https://kiro.dev), or [GitHub Copilot](https://github.com/features/copilot)

```bash
git clone https://github.com/nseney1/ai-steering-rules.git
cd ai-steering-rules

# Pick your platform:
./install-gemini.sh     # Gemini / Antigravity
./install-kiro.sh       # Kiro
./install-copilot.sh    # GitHub Copilot (run with 'global' or 'project')
```

Rules take effect on your next conversation turn. No restart needed.

---

## What's Included

### Rules (10 files)

| Rule | Trigger | Purpose |
|:-----|:--------|:--------|
| `providence.md` | always_on | **Highest priority.** Codebase grounding, claim verification, no hallucinations, venv shebang verification, desktop automation safety. |
| `cost-optimization.md` | always_on | Token efficiency, diffs-only edits, subagent model tiering, task hygiene. |
| `subagent-delegation.md` | always_on | Context window protection, parallel execution, coding task boundaries, structured reporting. |
| `architectural-tenets.md` | model_decision | Pragmatism, trade-off analysis, scale-to-zero, premature abstraction ban. |
| `polyglot-standards.md` | model_decision | Unified entrypoints (Makefiles), containerization. |
| `feature-specs.md` | model_decision | PRD structure, acceptance criteria, documentation deliverables. |
| `testing.md` | model_decision | Behavioral testing, ast.parse ban, sad paths, checkpoint testing. |
| `documentation.md` | model_decision | ADRs, actionable READMEs, Mermaid diagrams. |
| `destructive-ops.md` | model_decision | Dry-run mandates for IaC, database mutations, bulk git staging. |
| `git-workflow.md` | model_decision | Session awareness, conventional commits, .gitignore verification. |

- **`always_on`** — Loaded every turn (~3,320 tokens)
- **`model_decision`** — Loads full content only when relevant (~25 tokens idle)

### Skills (8 expert personas)

Zero tokens until invoked.

| Skill | Activates When... |
|:------|:------------------|
| `code-review` | Review or critique code. Staff Engineer: architectural flaws, race conditions, SOLID. |
| `security-audit` | Check security or audit endpoints. AppSec Engineer: OWASP Top 10. |
| `incident-debug` | Crash, hang, or error. SRE: reproduce → isolate → diagnose → fix → verify. |
| `readme-writer` | Write or improve a README. Technical Writer: scannable, copy-pasteable. |
| `performance-audit` | Optimize or profile code. Performance Engineer: hot-path allocations, O(n²). |
| `post-mortem` | Review a past session. SRE Facilitator: blameless analysis, pattern extraction. |
| `refactoring-pilot` | Refactor 4+ files. Specialist: Mikado Method, incremental moves. |
| `staff-review` | Comprehensive review or audit. Multi-lens fan-out with staff-level synthesis. |

### Hooks (3 lifecycle hooks)

Enforce governance mechanically — don't rely on the model remembering rules.

| Hook | Event | What It Does |
|:-----|:------|:-------------|
| `governance-monitor` | `PreInvocation` | Exports logs, checks for pending governance proposals, injects alerts. |
| `safety-gate` | `PreToolUse` | Gates `rm -rf /`, `git push -f`, `DROP TABLE`, `git add -A`. |
| `session-close` | `Stop` | Exports logs and syncs repos. No data loss even on crashes. |

---

## How It Works

```
SESSION START
│
├── PreInvocation hook (turn 1 + every 100th turn)
│   ├── Exports conversation logs (async, non-blocking)
│   ├── Checks for pending critical governance proposals
│   └── Injects ephemeral alert if found
│
├── NORMAL WORK
│   └── PreToolUse hook (every run_command)
│       ├── Dangerous patterns → BLOCKED (force_ask)
│       └── Everything else → allowed instantly
│
└── SESSION END
    └── Stop hook → exports logs, syncs repos
```

### Where Everything Lives

| What | Location |
|:-----|:---------|
| Live rules + skills | `~/.gemini/config/rules/`, `skills/` (symlinked) |
| Hooks | `~/.gemini/config/plugins/governance/hooks.json` |
| Hook scripts | `ai-steering-rules/scripts/` |
| Audit trail | `ai-conversation-logs/governance/auto_applied_log.jsonl` |
| Pattern taxonomy | `ai-conversation-logs/governance/taxonomy.json` (18 patterns) |
| Rule effectiveness | `ai-conversation-logs/governance/effectiveness.json` |

---

## Installation Details

### Gemini / Antigravity

**Option A: Copy** (simple, manual updates)
```bash
mkdir -p ~/.gemini/config/rules ~/.gemini/config/skills
cp rules/*.md ~/.gemini/config/rules/
cp -r skills/* ~/.gemini/config/skills/
```

**Option B: Symlink** (stays synced with `git pull`)
```bash
ln -sf "$(pwd)/rules" ~/.gemini/config/rules
ln -sf "$(pwd)/skills" ~/.gemini/config/skills
```

### Kiro

```bash
./install-kiro.sh
```

Activate manual rules by typing `#testing`, `#documentation`, `#feature-specs`, etc.

### GitHub Copilot

```bash
./install-copilot.sh global    # Merges all rules into ~/copilot-instructions.md
./install-copilot.sh project   # Creates .github/instructions/*.instructions.md
```

> Ensure "Enable custom instructions" is checked in your IDE's Copilot settings.

---

## Customization

These rules are opinionated. Fork and adjust:

| What to Change | File to Edit |
|:---------------|:-------------|
| Token limits, subagent model tiers | `cost-optimization.md` |
| Entrypoint format (Makefile vs Justfile) | `polyglot-standards.md` |
| Infrastructure preferences | `architectural-tenets.md` |
| Priority hierarchy | `providence.md` (all others defer) |

### Minimum Viable Governance

For small projects or token-constrained environments, load only 3 files (~2,000 tokens):

1. `providence.md` — grounding, anti-hallucination, no workarounds
2. `subagent-delegation.md` — context protection + cost tiering
3. `destructive-ops.md` — safety net for destructive operations

---

## Deep Dives

| Document | Contents |
|:---------|:---------|
| [Cost Analysis](docs/COST_ANALYSIS.md) | Per-file token costs, conditional loading math, ROI calculations |
| [Evolution](docs/EVOLUTION.md) | How the approach evolved across 4 phases, from prescriptive to evidence-based |
| [Scorecard](docs/SCORECARD.md) | Compliance scores, review history, current waste metrics |

---

## License

MIT
