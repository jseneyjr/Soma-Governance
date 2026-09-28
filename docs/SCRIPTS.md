# Scripts Reference

This document catalogs the 25 executable scripts that power the Prism AI Steering framework.

## Lifecycle Scripts (Hooks)
These scripts are invoked automatically by the IDE or terminal environment.
* **`governance_init.sh`**: PreInvocation hook that sets up the workspace, seeds contexts, injects domain hints and runs the pre-flight scan.
* **`safety_gate.sh`**: PreToolUse hook that screens commands for destructive or globally scoped operations (e.g., `rm -rf /`, `git push -f`).
* **`session_close.sh`**: Post-session cleanup hook that synthesizes learning from the session and triggers local reporting.
* **`escalation_sentinel.sh`**: Scans diffs to recommend protocol escalation levels (e.g., Breeze vs Trident vs Tempest) based on directory and file path sensitivity.

## Agent Health
* **`liveness_sentinel.sh`**: Monitors subagent dispatch health during multi-agent orchestration. Detects stalled or deadlocked agents.

## Cell Evolutionary Lifecycle Scripts
These scripts run the Cytogenesis selection and speciation pipeline. They respect `METRICS_REPO` configuration for tracking across repositories.
* **`cell_selection.sh`**: Main entrypoint for evaluating local cell fitness, calling the python scripts below.
* **`cell_fitness.py`**: Computes the fitness score of each cell in `.prism/cells/` based on true positives, false positives, and triggers. Respects `METRICS_REPO`.
* **`cell_adapt.py`**: Modifies underperforming cells (score 0.3 - 0.7) by refining their hypotheses and targeting to improve signal-to-noise ratios. Respects `METRICS_REPO`.
* **`cell_promote.py`**: Identifies high-performing local cells (score > 0.7) running in multiple repositories and promotes them into global forest-floor rules. Respects `METRICS_REPO`.

## External Signals & Lifecycle

| Script | Purpose |
|:-------|:--------|
| `cell_signal.sh` | External fitness signal API. Allows CI/CD, monitoring, test suites, or any external system to feed TP/FP/FN outcomes back to cells. |
| `cell_create.sh` | Programmatic cell creation. Create cells from automated systems, incident response, or test failures. |
| `cell_demote.py` | Reverse of cell_promote.py. Demotes global rules back to local cells when they cause false positives in new contexts. |

## Evolutionary Computation

| Script | Purpose |
|:-------|:--------|
| `cell_crossover.py` | GA crossover operator. Merges hypotheses from two high-fitness cells into a new offspring cell. |
| `cell_tournament.py` | Tournament selection. Picks k random cells and returns the fittest, preserving diversity. |
| `cell_metamorphose.py` | Cell type transformation. Vacuoles harden into Walls, Walls graduate to Rules through proof. |
| `cell_transfer.sh` | Horizontal gene transfer. Copies cells to other projects with fitness reset and 5-session probation. |
| `fitness_landscape.py` | Governance fitness visualization. ASCII chart of all cells with decayed fitness scores. |

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

## Team & Organization
* **`team_sync.sh`**: Syncs local promoted cells and metrics snapshots to a shared team repository. Enables multi-developer governance convergence with push/pull/status modes. Respects `TEAM_REPO` and `ORG_REPO` in `steering.conf`. **Privacy:** Only cell hypotheses/scores flow — never file content, paths, or PII.

## Installation Management
* **`uninstall.sh`**: Clean uninstaller that removes Prism AI Steering files from the system using `~/.prism-ai-steering/manifest.json`. Features backup-on-install and restore-on-uninstall functionality to safely reinstate previous configurations if desired.
