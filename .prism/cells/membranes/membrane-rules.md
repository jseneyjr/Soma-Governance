---
type: membrane
hypothesis: "Changes to rules/*.md need elevated review"
prediction: "Escalation sentinel will apply minimum trident mode"
falsification: "All escalated reviews are over-kill for 10 sessions → prune"
expiry_sessions: 10
expiry_days: 45
created: "2026-09-27"
impact_weight: 1.2
minimum_mode: trident
fitness:
  triggers: 0
  true_positives: 0
  false_positives: 0
  score: null
---
## Escalation Override: Governance Rules
Rules in the `rules/` directory dictate agent behavior universally. Any modification requires at least a Trident review (3 agents) to ensure safety and lack of regressions.
