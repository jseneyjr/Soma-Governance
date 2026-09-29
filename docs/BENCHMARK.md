# Soma Governance Benchmark Protocol v1.0

> Standardized methodology for measuring governance effectiveness across projects.

## Purpose

Provide a reproducible benchmark so any team can measure Soma's impact and contribute comparable data.

## Protocol

### Phase 1: Baseline (Ungoverned)
1. Select a target repository
2. Run 10 ungoverned sessions (no Soma rules, skills, or cells active)
3. Record per-session:
   - Waste rate (tokens wasted / tokens used)
   - FPSR (first-pass success rate)
   - Rework loops (times agent revisited the same file)
   - Session duration

### Phase 2: Genesis
4. Install Soma: `make install` or `bash install/install.sh <platform> --local` (Optionally integrate via `soma_mcp` MCP server)
5. Run Genesis skill to generate initial cells
6. If domain templates exist (`templates/`), verify they were seeded

### Phase 3: Governed Sessions
7. Run 30 governed sessions with full Soma stack (rules + skills + hooks + cells)
8. Record per-session:
   - Same metrics as baseline
   - Cell triggers (which cells fired)
   - Cell fitness scores
   - New cells created (genesis, crossover, metamorphosis)
   - Cells pruned (extinction)

### Phase 4: Analysis
9. Compute:
   - Waste rate trajectory (should decline)
   - FPSR trajectory (should improve)
   - Cell population dynamics:
     - Total births, deaths, metamorphoses, crossovers
     - Survival rate (cells alive at session 30 / total created)
     - Generation depth (max lineage.generation)
   - Fitness landscape (per-cell and aggregate)
10. Generate fitness landscape visualization: `python3 enzymes/fitness_landscape.py`

### Phase 5: Reporting
11. Report:

| Metric | Baseline (10 sessions) | Governed (30 sessions) | Δ |
|:-------|:----------------------:|:---------------------:|:-:|
| Avg waste rate | | | |
| Avg FPSR | | | |
| Avg rework loops | | | |
| Cells created | N/A | | |
| Cells surviving | N/A | | |
| Cells extinct | N/A | | |
| Metamorphoses | N/A | | |
| Crossovers | N/A | | |
| Promotions | N/A | | |

## Domain Configurations

| Domain | Suggested Sessions | Telomere Shortening | Notes |
|:-------|:-----------------:|:---------:|:------|
| Web Backend | 30 | 60 days | Stable patterns |
| RL Training | 30 | 30 days | Fast iteration |
| Infrastructure | 20 | 180 days | Slow change |
| Mobile App | 30 | 45 days | Medium churn |
| Data Pipeline | 20 | 90 days | Batch-oriented |

## Reproducibility Requirements

- Record Soma version (`cat VERSION`)
- Record platform and OS
- Record `soma.conf` settings (sanitized)
- Use `metrics_snapshot.sh` from session 1
- Do not modify cells manually during governed sessions
- Report all cell lineage data for phylogenetic analysis

## Cross-Domain Validation

For the strongest results, run the benchmark across 3+ domains and show:
1. Cell population converges (fitness landscape stabilizes)
2. Governance ROI is positive (waste Δ > 0)
3. GA dynamics are observable (crossover + metamorphosis events)
4. The mechanism transfers (same lifecycle works across domains)
