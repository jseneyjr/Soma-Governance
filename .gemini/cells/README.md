# Governance Cells

This directory contains Prism AI Steering governance cells. Cells are atomic, modular components that inject specialized constraints, heuristics, or environmental adaptations into the agent's context.

## Cell Types
- **Vacuole**: Traps and anti-patterns. Prevents the agent from falling into common pitfalls (e.g., using incorrect build tools, deprecated APIs).
- **Chloroplast**: Accelerators and optimizations. Provides fast-paths for common workflows.
- **Wall**: Boundary conditions and strict invariants. Enforces safety and policy requirements.
- **Membrane**: Filtering and transformation. Adjusts input/output to conform to expected structures.

## Cell Format Spec
Each cell is a Markdown file starting with YAML frontmatter.
Required fields:
- `type`: vacuole, chloroplast, wall, or membrane
- `hypothesis`: What this cell intends to achieve
- `prediction`: Expected measurable outcome
- `falsification`: Conditions under which this cell should be removed
- `expiry_sessions` / `expiry_days`: TTL for the cell
- `fitness`: Tracking block with `triggers`, `true_positives`, `false_positives`

## Fitness Lifecycle
Cells undergo evolutionary selection based on their fitness score (TP / Triggers * Weight):
- **SURVIVE**: Score > 0.7 (Highly effective, kept)
- **ADAPT**: Score 0.3 - 0.7 (Needs tuning)
- **EXTINCT**: Score < 0.3 (Candidate for pruning)
- **DORMANT**: 0 triggers past expiry (Candidate for pruning)
- **NEW**: 0 triggers within expiry (Undergoing testing)
