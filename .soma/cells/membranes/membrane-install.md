---
id: membrane-install
domain: governance
type: membrane
hypothesis: Install scripts represent high-risk operations requiring elevated governance.
prediction: Enforcing maelstrom mode for install operations prevents unsafe system changes.
falsification: Install scripts operate in a fully sandboxed environment with no persistent effects.
expiry_sessions: 80
impact_weight: 1.0
fitness: 1.0
---

# Membrane: Install Escalation

Target: `install/`
Minimum Mode: maelstrom

Description: Escalation membrane for install and uninstall scripts, requiring Maelstrom+ review protocols.
