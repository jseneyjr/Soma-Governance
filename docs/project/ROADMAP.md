# Soma Governance — Roadmap

> Features listed here are planned or in-progress. They are NOT yet shipped in the current release.
> A feature moves from this roadmap to the README only when:
> 1. Its behavioral test suite is written
> 2. All tests pass
> 3. It has a Claim Registry entry with status `unlocked`

## Shipped Features

### Layer 2 Verification
**Status**: ✅ SHIPPED (v0.60)  
AST-based verification tools with information-partitioned evaluation.

### Transcript Verifier
**Status**: ✅ SHIPPED (v0.60)  
Verify agent conversation transcripts against governance rules.

### Genesis
**Status**: ✅ SHIPPED (v0.70)  
Automated codebase scanning and governance cell candidate generation.

### Review Intensity Levels (Breeze → Supercell)
**Status**: ✅ SHIPPED (v0.60)  
Dynamic review depth escalation based on diff risk assessment.

### Phase 1 — Stop the Bleeding
**Status**: ✅ SHIPPED (v0.73)  
README stripped to earned claims, hook fix, claim registry, roadmap/release workflow docs.

### Phase 2 — Foundation
**Status**: ✅ SHIPPED (v0.74)  
Canonical cell parser, Wilson-bounded scoring, error hierarchy, 27-file parser migration.

## Phase 3 — v0.75 (NEXT)

### Credit Assignment
**Status**: Implementation planned (Phase 3)  
**Tracking**: `claim_credit_assignment` in `docs/project/CLAIM_REGISTRY.json`  
Attribute session outcomes to the specific cells that fired, enabling causal fitness updates.

### Crossover (Structured Rule Merging)
**Status**: Implementation planned (Phase 3)  
**Tracking**: `claim_structured_crossover` in `docs/project/CLAIM_REGISTRY.json`  
Field-level merge of parent cell attributes to create hybrid rules.

### Tournament Selection
**Status**: Implementation planned (Phase 3)  
**Tracking**: `claim_tournament_selection` in `docs/project/CLAIM_REGISTRY.json`  
Competitive evaluation between rules to select higher-fitness survivors.

## Phase 4 — v0.80

### Quorum Sensing (Multi-Rule Consensus)
**Status**: Implementation planned (Phase 4)  
**Tracking**: `claim_quorum_sensing` in `docs/project/CLAIM_REGISTRY.json`  
Require agreement from multiple rules before taking high-stakes actions.

### Gate Enforcement (Invariant DSL)
**Status**: Implementation planned (Phase 4)  
**Tracking**: `claim_gate_enforcement` in `docs/project/CLAIM_REGISTRY.json`  
CI-required invariant checks defined in cell YAML frontmatter.

## Research

### Antifragile Scaling
**Status**: Research  
Cells that perform better under stress receive fitness bonuses.

### External Validation Benchmarks
**Status**: Research  
Standardized benchmarks for comparing governance effectiveness across projects.

### Natural Language Rule Creation
**Status**: Experimental  
Create cells from natural language descriptions via `cell_create.sh --from-description`.

### Team Topology (Multi-Repo Sync)
**Status**: Experimental  
Synchronize governance rules across multiple repositories.

### Counterfactual ROI
**Status**: Research  
Causal inference for measuring governance impact.

