---
id: contract-mcp-cli-parity
domain: correctness
type: plasmodesmata
enforcement: advisory
hypothesis: The MCP server tools must expose the same capabilities as the CLI enzymes
prediction: New enzyme features added without corresponding MCP tool updates create
  feature gaps for non-Gemini users
falsification: "MCP and CLI are intentionally divergent by design \u2192 reclassify"
target_paths:
- soma_mcp/tools.py
- enzymes/cell_create_nl.py
- enzymes/cell_scan.py
- enzymes/immune_grade.py
- enzymes/cell_fitness.py
- enzymes/cell_coverage.py
expiry_sessions: 15
expiry_days: 60
created: '2026-09-28'
impact_weight: 1.2
minimum_mode: gale
tags:
- mcp
- api-surface
- parity
- cross-service
---

The MCP server (soma_mcp/tools.py) is the API contract for external agents.
When a new enzyme is added or an existing enzyme gains new features, the
corresponding MCP tool should be updated to maintain feature parity.
Current MCP tools: soma_create_cell, soma_scan, soma_grade, soma_coverage,
soma_fitness, soma_list_cells, soma_report_outcome, soma_propose_change,
soma_verify_changes, soma_checkpoint.
