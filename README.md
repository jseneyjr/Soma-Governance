# AI Steering Rules

Battle-tested governance rules for AI coding assistants — forged from 5,500+ steps of real failures across 9 sessions, refined through 12 review phases, and enforced via lifecycle hooks.

## Why Use This?

- **Stop AI from guessing** — Rules force the agent to verify claims against your actual codebase before acting
- **Cut token costs ~65%** — Conditional loading, smart subagent delegation, and task hygiene eliminate wasted steps ([methodology](docs/COST_ANALYSIS.md))
- **Mechanically enforced** — Lifecycle hooks gate destructive operations, inject governance context, and capture logs automatically
- **Cross-platform** — Works with Gemini/Antigravity (Google), Kiro (AWS), and GitHub Copilot (Microsoft)

## Quick Start

> **Prerequisites:** `git`, `make`, and one of: [Gemini/Antigravity](https://github.com/google-gemini/antigravity), [Kiro](https://kiro.dev), or [GitHub Copilot](https://github.com/features/copilot)

```bash
git clone https://github.com/nseney1/ai-steering-rules.git
cd ai-steering-rules

# Optional: customize for your team/stack
cp steering.conf.example steering.conf
# Edit steering.conf (team size, tech stack, git strategy, etc.)

# Install for your platform:
make install              # Gemini / Antigravity (default)
make install-kiro         # Kiro
make install-copilot      # GitHub Copilot (MODE=global|project)
```

Rules take effect on your next conversation turn. No restart needed.

> **No `make`?** The install scripts still work standalone: `./install-gemini.sh`

---

## What's Included

### Rules (11 files)

| Rule | Trigger | Purpose |
|:-----|:--------|:--------|
| `providence.md` | always_on | **Highest priority.** Codebase grounding, claim verification, no hallucinations, venv shebang verification, desktop automation safety. |
| `cost-optimization.md` | always_on | Token efficiency, diffs-only edits, subagent model tiering, task hygiene. |
| `subagent-delegation.md` | always_on | Context window protection, parallel execution, coding task boundaries, structured reporting. |
| `architectural-tenets.md` | model_decision | Pragmatism, trade-off analysis, scale-to-zero, premature abstraction ban. |
| `polyglot-standards.md` | model_decision | Unified entrypoints (Makefiles), containerization. |
| `feature-specs.md` | model_decision | PRD structure, acceptance criteria, documentation deliverables. |
| `testing.md` | model_decision | Behavioral testing, ast.parse ban, sad paths, checkpoint testing, hook integration testing. |
| `documentation.md` | model_decision | ADRs, actionable READMEs, Mermaid diagrams, README modularization. |
| `destructive-ops.md` | model_decision | Dry-run mandates for IaC, database mutations, bulk git staging. |
| `git-workflow.md` | model_decision | Session awareness, conventional commits, .gitignore verification, pre-push test gate. |
| `desktop-automation.md` | model_decision | PyAutoGUI/xdotool safety: focus verification, coordinate clamping, coordinate grounding, closed-loop validation. |

- **`always_on`** — Loaded every turn (~2,980 tokens)
- **`model_decision`** — Loads full content only when relevant (~30 tokens idle)

### Skills (9 expert personas)

Zero tokens until invoked.

| Skill | Activates When... |
|:------|:------------------|
| `session-preflight` | Starting a coding project. Flash probe: venv health, test suite, git state, display env. |
| `code-review` | Review or critique code. Staff Engineer: architectural flaws, race conditions, SOLID. |
| `security-audit` | Check security or audit endpoints. AppSec Engineer: OWASP Top 10. |
| `incident-debug` | Crash, hang, or error. SRE: reproduce → isolate → diagnose → fix → verify. |
| `readme-writer` | Write or improve a README. Technical Writer: scannable, copy-pasteable. |
| `performance-audit` | Optimize or profile code. Performance Engineer: hot-path allocations, O(n²). |
| `post-mortem` | Review a past session. SRE Facilitator: blameless analysis, pattern extraction. |
| `refactoring-pilot` | Refactor 4+ files. Specialist: Mikado Method, incremental moves. |
| `staff-review` | Comprehensive review or audit. Multi-lens fan-out with staff-level synthesis. Includes continuous review sentinel for coding sessions. |

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
| Pattern taxonomy | `ai-conversation-logs/governance/taxonomy.json` (23 patterns, v2.1) |
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

## Team Configuration

Copy `steering.conf.example` → `steering.conf` and customize for your environment:

```bash
make info   # Show current configuration
```

| Variable | Options | Effect |
|:---------|:--------|:-------|
| `TEAM_SIZE` | `solo`, `small`, `team`, `enterprise` | Branching strategy, approval requirements |
| `GIT_STRATEGY` | `trunk`, `feature-branch`, `gitflow` | Git workflow overrides |
| `AI_USAGE` | `individual`, `shared-repo`, `multi-team` | Context coordination guidance |
| `TECH_STACK` | `python`, `node`, `go`, `rust`, `java`... | Environment checks, package manager, preflight |
| `TEST_COMMAND` | any command | Override test runner auto-detection |
| `RULES_SUBSET` | `all`, `core`, `minimal` | Control how many rules are installed |
| `APPROVAL_CHAIN` | `none`, `peer`, `lead` | Destructive operation approval requirements |

### Rule Subsets

| Subset | Rules | Tokens | Best For |
|:-------|:-----:|:------:|:---------|
| `all` | 11 | ~3,500 | Full governance (default) |
| `core` | 6 | ~2,800 | Balanced coverage without domain-specific rules |
| `minimal` | 3 | ~2,000 | Token-constrained environments or quick experiments |

## Customization

These rules are opinionated. Fork and adjust:

| What to Change | File to Edit |
|:---------------|:-------------|
| Token limits, subagent model tiers | `cost-optimization.md` |
| Entrypoint format (Makefile vs Justfile) | `polyglot-standards.md` |
| Infrastructure preferences | `architectural-tenets.md` |
| Priority hierarchy | `providence.md` (all others defer) |

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
