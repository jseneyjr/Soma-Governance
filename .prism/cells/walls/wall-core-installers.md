---
type: wall
enforcement: advisory
promotion_threshold: 0.85
demotion_threshold: 0.30
hypothesis: "Changes to Makefile and install*.sh require core review"
prediction: "Will flag unreviewed changes to installer scripts"
falsification: "0 findings in 15 sessions → prune"
expiry_sessions: 15
expiry_days: 60
created: "2026-09-27"
impact_weight: 1.5
fitness:
  triggers: 0
  true_positives: 0
  false_positives: 0
  score: null
---
## Boundary: Core Installers
The `Makefile` and `install*.sh` scripts are the distribution mechanism for this framework. Changes here have a massive blast radius across all users. Validate syntax with `make validate` before modifying.
