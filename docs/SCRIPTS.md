# Scripts Reference

This document catalogs the 15 executable scripts that power the Prism AI Steering framework.

## Lifecycle Scripts (Hooks)
These scripts are invoked automatically by the IDE or terminal environment.
* **`governance_init.sh`**: PreInvocation hook that sets up the workspace, seeds contexts, injects domain hints and runs the pre-flight scan.
* **`safety_gate.sh`**: PreToolUse hook that screens commands for destructive or globally scoped operations (e.g., `rm -rf /`, `git push -f`).
* **`session_close.sh`**: Post-session cleanup hook that synthesizes learning from the session and triggers local reporting.
* **`escalation_sentinel.sh`**: Scans diffs to recommend protocol escalation levels (e.g., Breeze vs Trident vs Tempest) based on directory and file path sensitivity.

## Cell Evolutionary Lifecycle Scripts
These scripts run the Cytogenesis selection and speciation pipeline. They respect `METRICS_REPO` configuration for tracking across repositories.
* **`cell_selection.sh`**: Main entrypoint for evaluating local cell fitness, calling the python scripts below.
* **`cell_fitness.py`**: Computes the fitness score of each cell in `.gemini/cells/` based on true positives, false positives, and triggers. Respects `METRICS_REPO`.
* **`cell_adapt.py`**: Modifies underperforming cells (score 0.3 - 0.7) by refining their hypotheses and targeting to improve signal-to-noise ratios. Respects `METRICS_REPO`.
* **`cell_promote.py`**: Identifies high-performing local cells (score > 0.7) running in multiple repositories and promotes them into global forest-floor rules. Respects `METRICS_REPO`.

## Telemetry & Metrics
* **`token_census.py`**: Validates the token costs of active rules and skills via the Gemini SDK (or fallback estimation). Evaluates `METRICS_REPO`. **Privacy:** Only tokenizes local open-source rules/skills; never exfiltrates codebase files.
* **`metrics_snapshot.sh`**: Saves automated baselines and ROI deltas into `METRICS_REPO` (defaults to `docs/snapshots/`).
* **`export_logs.sh`**: Prepares logs and transcripts for post-mortem analysis.

## Governance & Maintenance
* **`common.sh`**: A shared bash library used across scripts to standardize output, error handling, and path resolutions.
* **`governance_sweep.sh`**: Performs local scans across past session transcripts to extract waste patterns and identify missed traps.
* **`sweep_session.py`**: Companion python script for `governance_sweep.sh` that classifies waste and scores compliance per session.
* **`log_finding.sh`**: Appends specific anti-patterns or successful catches into the `mulch_queue.jsonl` database for evolutionary learning.

## Privacy Note
All scripts are constrained by the **Privacy Invariant**: No script may output, log, or transmit raw file paths, usernames, hostnames, directory structures, diffs, or code patches. Only aggregate counts, booleans, and sanitized strings are permitted.
