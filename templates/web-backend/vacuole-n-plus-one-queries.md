---
type: vacuole
target_paths: ["*"]
hypothesis: "Fetching user feeds causes N+1 database queries"
prediction: "Database query count will scale linearly with feed items"
falsification: "If query count is constant regardless of feed size, prune"
expiry_sessions: 5
expiry_days: 60
created: "template"
impact_weight: 1.0
tags: ["db", "performance"]
fitness:
  triggers: 0
  true_positives: 0
  false_positives: 0
  score: null
---
## Vacuole: Fetching user feeds causes N+1 database queries

Fetching user feeds causes N+1 database queries

### Prediction
Database query count will scale linearly with feed items

### Falsification Criteria  
If query count is constant regardless of feed size, prune
