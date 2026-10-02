# Known Issues — Windows (v0.89.0)

Open Windows issues as of v0.89.0 were observed on Windows 11 with Windows PowerShell 5.1, Git Bash, and Python 3.14. Each open issue is tracked in [`BUG_REGISTRY.json`](project/BUG_REGISTRY.json) with `"status": "open"`.

> **⚠ Don't run the full test suite on a Windows machine you care about (BUG-010).** It can write to the real home directory. That includes `tests/test_install_lifecycle.py`, which `enzymes/verify_readme_claims.py` may invoke.

## Impact summary

| Area | v0.89.0 status | Bug |
|---|---|---|
| `python -m soma_mcp` | Startup fixed in v0.89.0 | BUG-008 |
| MCP write/execute tools | Fixed in v0.89.0; request a state-bound receipt first | BUG-009 |
| `install.ps1` parsing under Windows PowerShell 5.1 | Parse failure fixed in v0.89.0, but generated rules can contain mojibake and hooks are skipped | BUG-011, BUG-014 |
| `install.ps1` under PowerShell 7 (`pwsh`) | Not fully verified; avoids the known PS 5.1 decoding issue, but the PowerShell installer still skips hooks | BUG-014 |
| Hooks under Git Bash with a python.org install | Open: `python3` may resolve to the Windows Store stub | BUG-010 |
| `soma status` on a cp1252 console | Open: can crash unless `PYTHONIOENCODING=utf-8` | BUG-012 |
| `soma_list_cells` / `Governance.list_cells` | Open: non-ASCII text can be garbled and some cells can be dropped | BUG-012 |
| Windows-only tests | Open: path-separator and verification-contract failures remain undiagnosed | BUG-013 |

## Fixed in v0.89.0

### BUG-008: MCP server crashed at startup ([#45](https://github.com/nseney1/Soma-Governance/issues/45))
`soma_mcp/tools.py` and `soma_sdk/telemetry.py` now guard the POSIX-only `fcntl` import and use platform-appropriate or best-effort locking fallbacks.

### BUG-009: Write/execute MCP tools needed a token hosts could not supply ([#46](https://github.com/nseney1/Soma-Governance/issues/46))
Write and execute tools now use single-use receipts obtained from `soma_request_receipt`. A receipt is bound to the MCP session, canonical workspace, operation, exact arguments, target-file state, and governance-cell state. It is an operation authorization mechanism, not user authentication.

### BUG-011: `install.ps1` did not parse under Windows PowerShell 5.1 ([#48](https://github.com/nseney1/Soma-Governance/issues/48))
The PowerShell scripts now carry a UTF-8 BOM, and CI dry-runs the installer under Windows PowerShell 5.1 as well as PowerShell 7. This fixes parsing, not the separate rule-content decoding problem in BUG-014.

## Open issues

### BUG-010: Test suite writes to the real home directory ([#47](https://github.com/nseney1/Soma-Governance/issues/47))
The install-lifecycle tests run `install/install.sh` through Git Bash. The installer can resolve `RESOLVED_HOME` to the real profile instead of the test's temporary `HOME`, rewriting user configuration and causing Windows test failures.

**Related (Git Bash):** a python.org install may not provide `python3.exe`, so `python3` resolves to the App Installer stub. `command -v python3` succeeds but execution fails, preventing hook generation and other shell-script Python calls.

**Workaround:** disable the `python3.exe` App execution alias and put a real `python3` on `PATH`, such as a shim that invokes `python.exe`.

### BUG-012: Implicit cp1252 encoding ([#49](https://github.com/nseney1/Soma-Governance/issues/49))
- `soma status` prints characters that a cp1252 console may reject. **Workaround:** `$env:PYTHONIOENCODING = "utf-8"`.
- `soma_sdk/governance.py` has locale-dependent cell reads; decoding failures can be swallowed and cells omitted.

### BUG-013: Windows-only test failures ([#50](https://github.com/nseney1/Soma-Governance/issues/50))
- `tests/test_init.py` compares Windows paths against POSIX separators.
- Mutation-tester and branch-coverage contract tests fail on Windows; the cause remains undiagnosed.

### BUG-014: PowerShell installer writes mojibake ([#48](https://github.com/nseney1/Soma-Governance/issues/48))
Windows PowerShell 5.1 decodes UTF-8 rule files using its locale default when `Get-Content` has no explicit encoding, so generated rules can contain mojibake. The PowerShell installer also skips hooks.

**Workaround:** use `pwsh` to avoid the known PS 5.1 decoding problem, while recognizing that PowerShell installer hook parity is still unavailable.
