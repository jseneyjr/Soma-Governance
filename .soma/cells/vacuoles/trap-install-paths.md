---
id: trap-install-paths
domain: correctness
type: vacuole
hypothesis: Install scripts have divergent paths.
prediction: Unifying install targets will prevent deployment errors.
falsification: The paths are intentionally distinct for separate deploy targets.
expiry_sessions: 40
impact_weight: 0.9
---

# Trap: Install Paths Divergence

Target: `install/install.sh` vs `Makefile`

Description: Install targets diverge (`~/.gemini/config/rules/` vs `~/.gemini/config/genome/`). These need to be unified or clearly documented if intentionally separated.
