---
type: membrane
target_paths: ["*"]
hypothesis: "Database migrations with DROP COLUMN cause staging failures"
prediction: "Staging pipeline will fail on >50% of DROP COLUMN migrations"
falsification: "If 10 migrations with DROP COLUMN succeed, prune"
expiry_sessions: 5
expiry_days: 60
created: "template"
impact_weight: 1.5
tags: ["db", "migration"]
fitness:
  triggers: 0
  true_positives: 0
  false_positives: 0
  score: null
---
## Membrane: Database migrations with DROP COLUMN cause staging failures

Database migrations with DROP COLUMN cause staging failures

### Prediction
Staging pipeline will fail on >50% of DROP COLUMN migrations

### Falsification Criteria  
If 10 migrations with DROP COLUMN succeed, prune
