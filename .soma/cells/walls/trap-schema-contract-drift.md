---
id: trap-schema-contract-drift
domain: correctness
type: wall
enforcement: gate
promotion_threshold: 0.85
demotion_threshold: 0.3
hypothesis: JSONL producer/consumer pairs in separate enzyme files use mismatched
  field names, causing silent data loss in the fitness pipeline
prediction: Will catch field name mismatches between enzyme files that read/write
  the same JSONL ledger files
falsification: 0 findings in 10 sessions → prune
target_paths:
- enzymes/*.py
- soma_mcp/*.py
- immune_system/**/*.py
- soma_cli/*.py
triggers:
- enzyme_modification
- pipeline_change
expiry_sessions: 10
expiry_days: 30
created: '2026-09-30'
impact_weight: 1.0
tags:
- pipeline
- schema
- silent-failure
fitness:
  score: null
  impact_weight: 1.0
  triggers: 0
  true_positives: 0
  false_positives: 0
  last_trigger_date: null
---
When modifying an enzyme that writes to a JSONL file (fitness.jsonl,
sessions_processed.jsonl, outcomes.jsonl), grep for ALL consumers of that
file and verify field names match.

Known incident: `fitness_updater.py` emitted `{triggered_at}` but
`oracle_checkpoint.py` consumed `{triggered}` — 100% of records silently
dropped, rendering the entire fitness loop inoperative.

Supercell C1 incident: `soma_mcp/tools.py` wrote outcomes to `.soma/outcomes.jsonl`
with `{cells_used: [...]}` while `lifecycle.py` read from `.soma/evidence/outcomes.jsonl`
with `{cell_id: str}` — 100% of MCP-reported outcomes silently ignored.
