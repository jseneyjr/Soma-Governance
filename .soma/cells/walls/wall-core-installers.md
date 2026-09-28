---
type: wall
enforcement: advisory
promotion_threshold: 0.85
demotion_threshold: 0.30
hypothesis: "Changes to install.sh, install.ps1, uninstall.sh, common.sh, and Makefile require install-flow review"
prediction: "Will flag unreviewed changes to core installer infrastructure"
falsification: "0 findings in 15 sessions → prune"
target_paths:
  - "install/install.sh"
  - "install/install.ps1"
  - "install/uninstall.sh"
  - "install/hooks/*"
  - "install/soma.conf.example"
  - "enzymes/common.sh"
  - "Makefile"
expiry_sessions: 15
expiry_days: 60
created: "2026-09-28"
impact_weight: 1.5
minimum_mode: trident
fitness:
  triggers: 0
  true_positives: 0
  false_positives: 0
tags: [install, cross-platform, safety-critical]
---

The install flow is the first thing every user touches. Breakage here means
broken onboarding across Linux, macOS, WSL, and Windows. Changes to these files
must be reviewed for cross-platform compatibility and path correctness.
