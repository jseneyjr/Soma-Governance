---
type: vacuole
hypothesis: Hardcoded numeric literals represent brittle magic numbers that reduce code adaptability.
prediction: Extracting these numbers into configuration or constants will increase the fitness of the codebase.
falsification: The numbers are mathematically fundamental constants that never change.
expiry_sessions: 50
impact_weight: 0.8
fitness: 1.0
---

# Trap: Magic Numbers

Target: `enzymes/cell_fitness.py`, `enzymes/outcome_engine.py`, `enzymes/cell_promote.py`

Description: There are many hardcoded numeric literals (priors, z-scores, weights) in these files. They should be extracted into configuration files or constants.
