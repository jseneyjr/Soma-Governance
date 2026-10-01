# Soma Governance — Roadmap

> Features listed here are planned or in-progress. They are NOT yet shipped in the current release.
> A feature moves from this roadmap to the README only when:
> 1. Its behavioral test suite is written
> 2. All tests pass
> 3. It has a Claim Registry entry with status `unlocked`

## Planned Features

### Crossover (Structured Rule Merging)
**Status**: Implementation planned (Phase 3)  
**Tracking**: `claim_structured_crossover` in `docs/CLAIM_REGISTRY.json`  
Field-level merge of parent cell attributes to create hybrid rules.

### Tournament Selection
**Status**: Implementation planned (Phase 3)  
**Tracking**: `claim_tournament_selection` in `docs/CLAIM_REGISTRY.json`  
Competitive evaluation between rules to select higher-fitness survivors.

### Quorum Sensing (Multi-Rule Consensus)
**Status**: Implementation planned (Phase 4)  
**Tracking**: `claim_quorum_sensing` in `docs/CLAIM_REGISTRY.json`  
Require agreement from multiple rules before taking high-stakes actions.

### Gate Enforcement (Invariant DSL)
**Status**: Implementation planned (Phase 4)  
**Tracking**: `claim_gate_enforcement` in `docs/CLAIM_REGISTRY.json`  
CI-required invariant checks defined in cell YAML frontmatter.

### Antifragile Scaling
**Status**: Research  
Cells that perform better under stress receive fitness bonuses.

### External Validation Benchmarks
**Status**: Research  
Standardized benchmarks for comparing governance effectiveness across projects.

### Layer 2 Verification
**Status**: Research  
AST-based verification tools with information-partitioned evaluation.

### Natural Language Rule Creation
**Status**: Experimental  
Create cells from natural language descriptions via `cell_create.sh --from-description`.

### Review Intensity Levels (Breeze → Tempest)
**Status**: Experimental  
Dynamic review depth escalation based on diff risk assessment.

### Team Topology (Multi-Repo Sync)
**Status**: Experimental  
Synchronize governance rules across multiple repositories.

### Transcript Verifier
**Status**: Research  
Verify agent conversation transcripts against governance rules.

### Counterfactual ROI
**Status**: Research  
Causal inference for measuring governance impact.
