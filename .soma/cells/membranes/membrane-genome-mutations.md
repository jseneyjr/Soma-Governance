---
id: membrane-genome-mutations
domain: governance
type: membrane
enforcement: advisory
promotion_threshold: 0.85
demotion_threshold: 0.3
hypothesis: "Changes to genome/*.md need elevated review \u2014 these are the organism's\
  \ DNA"
prediction: Escalation sentinel will apply minimum trident mode for genome mutations
falsification: "All escalated reviews are over-kill for 10 sessions \u2192 prune"
target_paths:
- genome/*.md
- genome/**
expiry_sessions: 10
expiry_days: 45
created: '2026-09-28'
impact_weight: 1.2
minimum_mode: trident
tags:
- genome
- review-escalation
- dna
---

Changes to the genome (rules) directory are high-impact mutations that affect every
user of Soma. Modifications to these files change the inherited behavioral DNA of
the organism and require elevated review intensity.
