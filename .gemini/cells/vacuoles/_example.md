---
type: vacuole
hypothesis: "This repo uses build.sh not make — agents frequently guess wrong"
prediction: "Will flag attempts to run make in repos without Makefile"
falsification: "0 findings in 10 sessions → prune"
expiry_sessions: 10
expiry_days: 30
created: 2026-09-28
impact_weight: 0.8
fitness:
  triggers: 0
  true_positives: 0
  false_positives: 0
  score: null
---

## Trap: Build Tool Mismatch

This repository uses `build.sh` for builds, not `make`. Common anti-pattern: agents attempt `make build` or `make test` which fails.

### Correct Approach
- Run `./build.sh` for builds
- Run `./build.sh test` for tests
- Check build.sh --help for available targets
