---
type: wall
target_paths: ["*"]
hypothesis: "Authentication tokens are logged in plaintext"
prediction: "Log files will contain 'Bearer eyJ' strings"
falsification: "If logs pass regex scan for JWTs 5 times, prune"
expiry_sessions: 5
expiry_days: 60
created: "template"
impact_weight: 2.0
tags: ["security", "auth"]
fitness:
  triggers: 0
  true_positives: 0
  false_positives: 0
  score: null
---
## Wall: Authentication tokens are logged in plaintext

Authentication tokens are logged in plaintext

### Prediction
Log files will contain 'Bearer eyJ' strings

### Falsification Criteria  
If logs pass regex scan for JWTs 5 times, prune
