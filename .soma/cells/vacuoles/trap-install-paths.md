---
id: trap-install-paths
domain: correctness
type: vacuole
enforcement: advisory
hypothesis: Install scripts have divergent paths.
prediction: Unifying install targets will prevent deployment errors.
falsification: The paths are intentionally distinct for separate deploy targets.
target_paths:
- install/install.sh
- Makefile
expiry_sessions: 40
impact_weight: 0.9
minimum_mode: breeze
tags:
- install
- paths
- correctness
created: "2026-09-28"
---

# Trap: Install Paths Divergence

Target: `install/install.sh` vs `Makefile`

Description: Install targets diverge (`~/.gemini/config/rules/` vs `~/.gemini/config/genome/`). These need to be unified or clearly documented if intentionally separated.
