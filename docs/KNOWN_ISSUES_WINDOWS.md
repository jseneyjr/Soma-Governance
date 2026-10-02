# Known Issues — Windows

Open Windows issues as of v0.88.2, found on Windows 11 with Windows PowerShell 5.1, Git Bash, and Python 3.14.
Each issue is tracked in [`BUG_REGISTRY.json`](project/BUG_REGISTRY.json) with `"status": "open"` and has a GitHub issue.

> **⚠ Don't run the full test suite on a Windows machine you care about (BUG-010).** It writes to your real home directory. That includes `tests/test_install_lifecycle.py`, the required test for `claim_multi_platform`, so `enzymes/verify_readme_claims.py` triggers it too.

## Impact summary

| Area | Works on Windows? | Bug |
|---|---|---|
| `.\install.ps1` under Windows PowerShell 5.1 | Installs (parse failure fixed in Unreleased), but generated rules contain mojibake | BUG-011, BUG-014 |
| `install.ps1` under PowerShell 7 (`pwsh`) | Yes | — |
| MCP server (`python -m soma_mcp`) | Yes (fixed in Unreleased) | BUG-008 |
| MCP write/execute tools from an MCP host | **No** (all platforms): `_sessionToken` not reachable | BUG-009 |
| Hooks under Git Bash with a python.org install | **No**: `python3` is the Windows Store stub | BUG-010 |
| `soma status` on a cp1252 console | Crashes unless `PYTHONIOENCODING=utf-8` | BUG-012 |
| `soma_list_cells` / `Governance.list_cells` | Garbles non-ASCII text; silently drops some cells | BUG-012 |

## Issues

### BUG-008: MCP server crashes at startup ([#45](https://github.com/nseney1/Soma-Governance/issues/45)) — fixed (Unreleased)
`soma_mcp/tools.py` and `soma_sdk/telemetry.py` imported `fcntl` unconditionally. Both now fall back to unlocked appends, as `enzymes/fitness_updater.py` already did.

### BUG-009: Write/execute MCP tools need a token hosts can't supply ([#46](https://github.com/nseney1/Soma-Governance/issues/46))
The token is generated per process on `initialize` and returned only in `serverInfo._sessionToken`. MCP hosts don't pass `serverInfo` to the model, so `soma_report_outcome` and the other write/execute tools return JSON-RPC `-32600`. Outcomes can't be reported, so fitness doesn't evolve.

### BUG-010: Test suite writes to the real home directory ([#47](https://github.com/nseney1/Soma-Governance/issues/47))
The install-lifecycle tests run `install/install.sh` through Git Bash. The installer resolves `RESOLVED_HOME` to the real profile, not the test's `HOME`, so it rewrites `~/.claude/CLAUDE.md`, creates `~/.kiro/`, and overwrites `~/.soma/manifest.json`. This also causes the `test_install_lifecycle.py` and `test_status.py` failures on Windows.

**Related (Git Bash):** a python.org install has no `python3.exe`, so `python3` resolves to the App Installer stub (`WindowsApps\python3.exe`). `command -v python3` succeeds, but running it exits 49 with no output. `install_hooks()` in `enzymes/common.sh` then renders an empty `hooks.json` and skips hooks, and the other `python3` calls in the shell scripts fail.
**Workaround:** turn off the `python3.exe` App execution alias, and put a real `python3` on PATH, e.g. a `~/bin/python3` shim that runs `python.exe "$@"`.

### BUG-011: `install.ps1` doesn't parse under Windows PowerShell 5.1 ([#48](https://github.com/nseney1/Soma-Governance/issues/48)) — fixed (Unreleased)
The `.ps1` files were UTF-8 without a BOM, so PS 5.1 read them as cp1252 and the em-dash's 0x94 byte ended a string early. They now carry a BOM, and CI dry-runs the installer under Windows PowerShell 5.1 as well as `pwsh` 7.

### BUG-014: The PowerShell installer writes mojibake ([#48](https://github.com/nseney1/Soma-Governance/issues/48))
`Get-Content` without `-Encoding` decodes the UTF-8 rule files as cp1252 under PS 5.1, so sequences like `â€”` appear in generated rules. The PowerShell installer also skips hooks.
**Workaround:** use `pwsh`.

### BUG-012: Implicit cp1252 encoding ([#49](https://github.com/nseney1/Soma-Governance/issues/49))
- `soma status` prints emoji to a cp1252 console and crashes. **Workaround:** `$env:PYTHONIOENCODING = "utf-8"`.
- `soma_sdk/governance.py` reads cells with `read_text()` and no encoding inside `except Exception: pass`. Non-ASCII text is garbled, and cells containing bytes cp1252 can't decode (0x81, 0x8D, 0x8F, 0x90, 0x9D) are silently dropped.

### BUG-013: Windows-only test failures ([#50](https://github.com/nseney1/Soma-Governance/issues/50))
- `tests/test_init.py` compares Windows paths against POSIX separators.
- The mutation-tester and branch-coverage contract tests fail on Windows; the cause hasn't been diagnosed.
