---
type: membrane
target_paths: ["*"]
hypothesis: "Switching data sources causes metric discrepancies"
prediction: "Daily Active Users metric will drift by >5% between old and new sources"
falsification: "If discrepancy is <1% for 7 consecutive days, prune"
expiry_sessions: 5
expiry_days: 60
created: "template"
impact_weight: 1.5
tags: ["data", "metrics"]
fitness:
  triggers: 0
  true_positives: 0
  false_positives: 0
  score: null
---
## Membrane: Switching data sources causes metric discrepancies

Switching data sources causes metric discrepancies

### Prediction
Daily Active Users metric will drift by >5% between old and new sources

### Falsification Criteria  
If discrepancy is <1% for 7 consecutive days, prune
