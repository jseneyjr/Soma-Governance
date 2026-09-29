---
type: wall
target_paths: ["*"]
hypothesis: "Gradients explode during PPO update phase"
prediction: "Gradient norm will exceed 100 in the first 5 epochs"
falsification: "If gradient norm stays below 10 for 50 epochs, prune"
expiry_sessions: 5
expiry_days: 60
created: "template"
impact_weight: 2.0
tags: ["rl", "gradients"]
fitness:
  triggers: 0
  true_positives: 0
  false_positives: 0
  score: null
---
## Wall: Gradients explode during PPO update phase

Gradients explode during PPO update phase

### Prediction
Gradient norm will exceed 100 in the first 5 epochs

### Falsification Criteria  
If gradient norm stays below 10 for 50 epochs, prune
