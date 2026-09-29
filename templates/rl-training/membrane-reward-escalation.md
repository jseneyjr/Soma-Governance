---
type: membrane
target_paths: ["*"]
hypothesis: "Reward scaling causes policy divergence over time"
prediction: "Action probabilities will become deterministic (entropy < 0.1)"
falsification: "If entropy stays above 0.5 for 1000 steps, prune"
expiry_sessions: 5
expiry_days: 60
created: "template"
impact_weight: 1.5
tags: ["rl", "reward", "policy"]
fitness:
  triggers: 0
  true_positives: 0
  false_positives: 0
  score: null
---
## Membrane: Reward scaling causes policy divergence over time

Reward scaling causes policy divergence over time

### Prediction
Action probabilities will become deterministic (entropy < 0.1)

### Falsification Criteria  
If entropy stays above 0.5 for 1000 steps, prune
