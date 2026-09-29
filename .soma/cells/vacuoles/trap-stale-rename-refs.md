---
type: vacuole
enforcement: advisory
hypothesis: "Bulk renames leave stale references to old names in files not covered by the rename script"
prediction: "Will catch orphaned references to 'prism', 'steering', 'rules/', 'skills/', 'scripts/' after rename operations"
falsification: "0 stale references found in 5 sessions → prune"
target_paths:
  - "enzymes/*.py"
  - "enzymes/*.sh"
  - "install/*.sh"
  - "install/*.ps1"
  - "soma_mcp/*.py"
  - "soma_sdk/*.py"
  - "Makefile"
  - "README.md"
expiry_sessions: 10
expiry_days: 30
created: "2026-09-28"
impact_weight: 1.3
minimum_mode: gale
fitness:
  triggers: 5
  true_positives: 4
  false_positives: 1
tags: [rename, migration, anti-pattern, high-value]
---

After the Phase 22 Soma Rebirth rename, multiple stale references survived:
- `scripts_dir = "$repo_dir/scripts"` in common.sh (CRITICAL — broke all hooks)
- `prism_root` variable names in soma_resolve.py and soma_mcp/tools.py  
- `.prism` directory check in cell_transfer.sh (always false after rename)
- "Installing steering rules" banners in install.sh and install.ps1

Any future rename operation must include a post-rename grep sweep.
