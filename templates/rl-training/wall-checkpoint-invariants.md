---
type: wall
target_paths: ["*"]
hypothesis: "Model weights contain NaNs or infinite values after checkpoint load"
prediction: "Checkpoints saved after iteration 10k will corrupt during load"
falsification: "If 5 consecutive checkpoints load cleanly, prune"
expiry_sessions: 5
expiry_days: 60
created: "template"
impact_weight: 2.0
tags: ["rl", "checkpoint"]
fitness:
  triggers: 0
  true_positives: 0
  false_positives: 0
  score: null
---
## Wall: Model weights contain NaNs or infinite values after checkpoi

Model weights contain NaNs or infinite values after checkpoint load

### Prediction
Checkpoints saved after iteration 10k will corrupt during load

### Falsification Criteria  
If 5 consecutive checkpoints load cleanly, prune
