---
type: wall
target_paths: ["*"]
hypothesis: "Hardcoded secrets exist in infrastructure code"
prediction: "TF files contain AWS_SECRET_ACCESS_KEY strings"
falsification: "If security scanner finds 0 secrets in 5 runs, prune"
expiry_sessions: 5
expiry_days: 60
created: "template"
impact_weight: 2.0
tags: ["security", "iac"]
fitness:
  triggers: 0
  true_positives: 0
  false_positives: 0
  score: null
---
## Wall: Hardcoded secrets exist in infrastructure code

Hardcoded secrets exist in infrastructure code

### Prediction
TF files contain AWS_SECRET_ACCESS_KEY strings

### Falsification Criteria  
If security scanner finds 0 secrets in 5 runs, prune
