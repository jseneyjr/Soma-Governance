---
id: trap-version-drift
domain: correctness
type: vacuole
enforcement: advisory
hypothesis: Version numbers across VERSION, pyproject.toml, soma_sdk/__init__.py,
  and soma_sdk_js/package.json must stay in sync
prediction: Will catch version drift when bumping versions in one file but not others
falsification: 0 version mismatches in 10 sessions → prune
target_paths:
- VERSION
- pyproject.toml
- soma_sdk/__init__.py
- soma_sdk_js/package.json
expiry_sessions: 10
expiry_days: 45
created: '2026-09-28'
impact_weight: 1.0
minimum_mode: breeze
tags:
- versioning
- consistency
- release
fitness:
  score: 0.7273
  impact_weight: 1.0
  triggers: 11
  true_positives: 8
  false_positives: 2
  last_trigger_date: '2026-10-01T04:26:19Z'
---
Version consistency is enforced across 4 sources:
- `VERSION` (single source of truth)
- `pyproject.toml` (Python package)
- `soma_sdk/__init__.py` (Python SDK)
- `soma_sdk_js/package.json` (JavaScript SDK)

The JS SDK was found at 0.20.0 when everything else was 0.22.0 during the
Phase 22 audit. A version bump checklist or automated script should verify sync.
