---
type: vacuole
hypothesis: "Manual AWS changes cause terraform state drift"
prediction: "Terraform plan will show unexpected modifications in SG rules"
falsification: "If 3 consecutive plans show no drift, prune"
expiry_sessions: 5
expiry_days: 60
created: "template"
impact_weight: 1.0
tags: ["iac", "aws"]
fitness:
  triggers: 0
  true_positives: 0
  false_positives: 0
  score: null
---
## Vacuole: Manual AWS changes cause terraform state drift

Manual AWS changes cause terraform state drift

### Prediction
Terraform plan will show unexpected modifications in SG rules

### Falsification Criteria  
If 3 consecutive plans show no drift, prune
