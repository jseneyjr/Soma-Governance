---
type: vacuole
enforcement: advisory
promotion_threshold: 0.85
demotion_threshold: 0.30
hypothesis: "Hardcoded platform paths (e.g. ~/.gemini) in common scripts"
prediction: "Will flag hardcoded paths where dynamic STEERING_PLATFORM logic is required"
falsification: "0 findings in 10 sessions → prune"
expiry_sessions: 10
expiry_days: 30
created: "2026-09-27"
impact_weight: 0.8
fitness:
  triggers: 0
  true_positives: 0
  false_positives: 0
  score: null
---
## Trap: Hardcoded Platform Paths
This repository builds steering configurations for multiple platforms (Gemini, Kiro, Copilot). 
Do not hardcode paths like `~/.gemini/config` in shared installer scripts. Always use the `STEERING_PLATFORM` environment variable or switch statements as seen in `Makefile`.
