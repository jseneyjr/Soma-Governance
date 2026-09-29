---
type: wall
target_paths: ["*"]
hypothesis: "Retrying failed jobs duplicates records in the warehouse"
prediction: "Record counts will increase when the same file is processed twice"
falsification: "If processing the same file twice yields the same record count, prune"
expiry_sessions: 5
expiry_days: 60
created: "template"
impact_weight: 2.0
tags: ["data", "idempotency"]
fitness:
  triggers: 0
  true_positives: 0
  false_positives: 0
  score: null
---
## Wall: Retrying failed jobs duplicates records in the warehouse

Retrying failed jobs duplicates records in the warehouse

### Prediction
Record counts will increase when the same file is processed twice

### Falsification Criteria  
If processing the same file twice yields the same record count, prune
