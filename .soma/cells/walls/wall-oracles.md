---
id: wall-oracles
domain: governance
type: wall
enforcement: gate
hypothesis: Oracles contain sensitive genome configuration.
prediction: Shielding the oracles directory prevents corruption of core identity logic.
falsification: Oracles are public and ephemeral.
target_paths:
- genome/.oracles/**
expiry_sessions: 100
impact_weight: 1.0
minimum_mode: trident
tags:
- oracles
- genome
- security
created: "2026-09-28"
---

# Wall: Oracles

Target: `genome/.oracles/`

Description: Security boundary protecting the genome oracles from unauthorized modification.
