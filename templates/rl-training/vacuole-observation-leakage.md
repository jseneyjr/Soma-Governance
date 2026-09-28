---
type: vacuole
hypothesis: "Observation space contains future information leaking to agent"
prediction: "Agent performance drops significantly when testing on held-out environment"
falsification: "If test performance is within 10% of train performance, prune"
expiry_sessions: 5
expiry_days: 60
created: "template"
impact_weight: 1.0
tags: ["rl", "observation"]
fitness:
  triggers: 0
  true_positives: 0
  false_positives: 0
  score: null
---
## Vacuole: Observation space contains future information leaking to age

Observation space contains future information leaking to agent

### Prediction
Agent performance drops significantly when testing on held-out environment

### Falsification Criteria  
If test performance is within 10% of train performance, prune
