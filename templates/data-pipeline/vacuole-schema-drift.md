---
type: vacuole
target_paths: ["*"]
hypothesis: "Upstream API changes cause downstream pipeline failures"
prediction: "JSON parsing errors will increase by 20% after API updates"
falsification: "If API updates happen without parsing errors for 2 weeks, prune"
expiry_sessions: 5
expiry_days: 60
created: "template"
impact_weight: 1.0
tags: ["data", "api"]
fitness:
  triggers: 0
  true_positives: 0
  false_positives: 0
  score: null
---
## Vacuole: Upstream API changes cause downstream pipeline failures

Upstream API changes cause downstream pipeline failures

### Prediction
JSON parsing errors will increase by 20% after API updates

### Falsification Criteria  
If API updates happen without parsing errors for 2 weeks, prune
