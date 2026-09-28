# Genesis Report — Soma
> Generated: 2026-09-27T16:47:45-04:00 | Stages: 1-5 | Repos: 1

## 🗺️ Canopy
### Tech Stack
- Language(s): Bash, Python (3.x), Markdown
- Framework: Custom (Soma)
- Build system: Make (`make install`, `make test`)
- Package manager: None detected

### Dev Environment
- Shell: bash 5.x
- OS & arch: linux, x86_64
- Build tools: make, python3, git
- Container: false
- Python: 3.x detected
- Git: 2.x, configured

### Directory Tree
```
genome/       — AI behavior rules
enzymes/     — Automation & tooling
organs/      — Domain-specific skills
docs/        — Documentation & metrics
.gemini/     — Adaptive immune cells
```

### Dependencies
- Direct: 0 (No standard manifest found)
- Notable: Bash, Python3, Make

### Entry Points
- `install.sh` — Global installer
- `Makefile` — Build and configuration targets
- `cell_fitness.py` — Fitness calculation

### Testing
- Framework: Custom Makefile
- Runner: `make test`
- Test directory: Mixed (`enzymes/`)

### Monorepo
- Is monorepo: no

## 📜 Rings
### Branch Topology
- Default branch: main
- Active branches: 1 (main)
- Stale branches (>90 days): 0

### Commit Activity
- Total commits: 104
- Active contributors: 1 (Nick Seney)

### Release Cadence
- Last release: N/A (No tags)

### Churn Heatmap (top 10 most-modified files, last 100 commits)
| File | Modifications | Role |
|:-----|:------------:|:------------------------|
| README.md | 43 | documentation |
| SKILL.md (staff-review) | 19 | skill |
| PHYLOGENY.md | 18 | documentation |
| EXPERIMENTS.md | 16 | documentation |
| subagent-delegation.md | 14 | rule |
| immune_init.sh | 11 | script |
| providence.md | 11 | rule |
| cost-optimization.md | 10 | rule |
| Makefile | 9 | config |
| METRICS.md | 9 | documentation |

### High-Risk Files
- `immune_init.sh` — 11 changes — Risk: High (Core setup script)
- `Makefile` — 9 changes — Risk: High (Configuration entrypoint)

## 📖 Taproot
### API Surface
- None (Configuration framework)

### Data Models
| Entity | Fields | Relationships | File |
|:-------|:------:|:-------------|:-----|
| Cell (YAML) | 11 | None | `cell_fitness.py` |
| Hooks (JSON) | ~5 | None | `hooks.json.template` |

### Configuration Pattern
- Config strategy: Config file & Env vars
- Config files: `soma.conf`, `hooks.json.template`
- Env vars referenced: 6 (SOMA_PLATFORM, TEAM_SIZE, etc.)

### External Service Integrations
- None (Local toolkit)

### Cross-Repo Boundaries
- Shared schemas: `metrics_snapshot.sh` logs metrics to `METRICS_REPO`

## 🧭 Lichen
### Coding Conventions
- Naming: snake_case for scripts, kebab-case for markdown
- Formatting: none detected
- Linter: `make validate` (bash -n)
- Error handling: bash strict mode

### Testing Patterns
- Strategy: Syntax validation
- Framework: `make validate`
- Test naming: standard scripts

### Deployment Model
- Containerized: no
- CI/CD: none detected
- IaC: none
- Environments: `soma.conf` platform modes

### Known Traps & Gotchas
| File | Signal | Trap | Recommendation |
|:-----|:-------|:-----|:---------------|
| `install.sh` | High complexity | Hardcoded paths | Use `$SOMA_PLATFORM` |
| `genome/*.md` | Modifies global behavior | Changes affect all | Elevate review mode |

### Recommended Governance Configuration
- Default review protocol: Trident — Modifying global rules requires scrutiny
- High-risk areas requiring Maelstrom+: `install.sh`, `Makefile`

### Auto-Generated Context Pre-Seeding Block
```
<!-- CONTEXT: soma -->
[PROJECT]: soma — Adaptive AI governance rules framework
[STACK]: Python | Bash | Markdown | Test: `make test`
[LAYOUT]:
  - `genome/`: Agent behavior rules
  - `organs/`: Subagent domain tasks
  - `enzymes/`: Tooling and fitness logic
  - `.soma/cells/`: Adaptive constraints
[CONSTRAINTS]:
  - Respect Privacy Invariants: No raw paths, usernames, or env vars
  - Measured token values (ratio 1.35), never heuristics
<!-- END CONTEXT -->
```

## 🧫 Cytogenesis
Generated cells in `.soma/cells/`:
- `vacuoles/trap-hardcoded-paths.md`
- `walls/wall-core-installers.md`
- `membranes/membrane-rules.md`
- `chloroplasts/persona-governance-architect.md`
