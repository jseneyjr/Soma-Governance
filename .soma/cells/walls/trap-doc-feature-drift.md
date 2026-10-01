---
id: trap-doc-feature-drift
domain: documentation
type: wall
enforcement: gate
hypothesis: Adding or modifying a feature without updating ALL documentation surfaces
  (README, CHANGELOG, SKILL.md) in the same commit causes doc-feature desync
prediction: Will fire when a commit touches code files but not documentation, or
  updates one doc surface but not others
falsification: 0 findings in 20 sessions → prune
target_paths:
- README.md
- docs/CHANGELOG.md
- 'organs/*/SKILL.md'
- 'soma_cli/*.py'
- 'soma_mcp/*.py'
triggers:
- feature_addition
- feature_modification
- commit_review
minimum_mode: standard
expiry_sessions: 30
expiry_days: 90
created: '2026-09-30'
impact_weight: 1.0
tags:
- documentation
- drift
- process
fitness:
  score: null
  impact_weight: 1.0
  triggers: 0
  true_positives: 0
  false_positives: 0
  last_trigger_date: null
---
Supercell doc-drift incident: Supercell intensity added to README and SKILL.md but
CHANGELOG v0.60.0 was not updated. Architecture ASCII box was edited but not
width-verified. Detection: when a commit adds a feature term to any doc, grep all
other doc surfaces for the same term.
