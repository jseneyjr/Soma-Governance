---
id: contract-sdk-feature-parity
domain: correctness
type: plasmodesmata
enforcement: advisory
hypothesis: The Python SDK (soma_sdk/) and JavaScript SDK (soma_sdk_js/) must expose
  equivalent public API methods — when a public method is added to either SDK, the
  corresponding method must be added to the other before release
prediction: New SDK features added to one language without the other create invisible
  feature gaps that are only discovered during cross-language audits
falsification: SDKs are intentionally divergent by design → reclassify
target_paths:
- soma_sdk/governance.py
- soma_sdk/cells.py
- soma_sdk_js/lib/governance.js
- soma_sdk_js/lib/cells.js
expiry_sessions: 30
expiry_days: 120
created: '2026-10-01'
impact_weight: 1.0
minimum_mode: gale
tags:
- sdk
- api-surface
- parity
- cross-language
fitness:
  score: 1.0
  impact_weight: 1.0
  triggers: 3
  true_positives: 3
  false_positives: 0
  last_trigger_date: '2026-10-01T04:26:19Z'
---
The Python and JavaScript SDKs are parallel interfaces to the same governance
system. Feature drift between them means users on different platforms get
different capabilities without documentation.

Phase 3 incident:
JS SDK (`soma_sdk_js/lib/governance.js:185-192`) implemented `entropy()` and
`adversarial(cellName)` wrapping immune_entropy.py and cell_adversarial.py.
Python SDK (`soma_sdk/governance.py`) had neither method. The gap was only
discovered during a Supercell cross-SDK audit in Cycle 5.

Additionally, both SDKs had `is_extinct` and `is_promotable` using legacy
`raw_score` thresholds that diverged from canonical `cell_promote.py`
standards (Bayesian > 0.85, triggers >= 20). The JS SDK still uses
`rawScore` and needs alignment.

Parity check: diff public method names between Python and JS SDKs.
  Python: grep 'def [a-z]' soma_sdk/governance.py soma_sdk/cells.py
  JS:     grep '[a-z]*(' soma_sdk_js/lib/governance.js soma_sdk_js/lib/cells.js
