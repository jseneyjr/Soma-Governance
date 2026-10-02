# Known Issues — Windows (v0.89.0)

Open Windows issues as of v0.89.0 were observed on Windows 11 with Windows PowerShell 5.1, Git Bash, and Python 3.14. Each open issue is tracked in [`BUG_REGISTRY.json`](project/BUG_REGISTRY.json) with `"status": "open"`.

> **⚠ On v0.89.0, don't run the full test suite on a Windows machine you care about (BUG-010).** It can write to the real home directory. That includes `tests/test_install_lifecycle.py`, which `enzymes/verify_readme_claims.py` may invoke. Fixed after v0.89.0; see below.

## Impact summary

| Area | v0.89.0 status | Bug |
|---|---|---|
| `python -m soma_mcp` | Startup fixed in v0.89.0 | BUG-008 |
| MCP write/execute tools | Fixed in v0.89.0; request a state-bound receipt first | BUG-009 |
| MCP cell reads and receipts (`soma_scan`, `soma_list_cells`, `soma_request_receipt`) | v0.89.0 fails once any cell has been edited; fixed after v0.89.0 | BUG-035 |
| `install.ps1` parsing under Windows PowerShell 5.1 | Parse failure fixed in v0.89.0, but generated rules can contain mojibake and hooks are skipped | BUG-011, BUG-014, BUG-032 |
| `install.ps1` under PowerShell 7 (`pwsh`) | Not fully verified; avoids the known PS 5.1 decoding issue, but the PowerShell installer still skips hooks | BUG-014, BUG-032 |
| Hooks under Git Bash with a python.org install | Open: `python3` may resolve to the Windows Store stub | BUG-037 |
| `uninstall.sh` under Git Bash | Open: rejects every path as "not an absolute path" and removes nothing | BUG-036 |
| Test suite on Windows | v0.89.0 can write to the real home directory; fixed after v0.89.0 | BUG-010 |
| `soma status` on a cp1252 console | Open: can crash unless `PYTHONIOENCODING=utf-8` | BUG-012 |
| `soma_list_cells` / `Governance.list_cells` | Open: non-ASCII text can be garbled and some cells can be dropped | BUG-012 |
| Windows-only tests | Open: verification-contract failures root-caused (unescaped Windows paths in generated tests); path-separator failures remain | BUG-013 |

## Fixed after v0.89.0 (unreleased)

### BUG-035: Cell inventory rejected edited cells ([#61](https://github.com/nseney1/Soma-Governance/issues/61))
On v0.89.0, `soma_scan` and `soma_list_cells` fail with `file changed before it was opened`, and `soma_request_receipt` returns `Internal error`, so no write or execute tool can run. Cause: `os.stat` and `os.fstat` report different `st_ctime` values on Windows. The inventory now leaves `st_ctime` out of its change check on Windows and reads cells in binary mode.

### BUG-010: Test suite wrote to the real home directory ([#47](https://github.com/nseney1/Soma-Governance/issues/47))
Under Git Bash, `resolve_home()` prefers `USERPROFILE` over `HOME`, and six calls in `tests/test_install_lifecycle.py` overrode only `HOME`, so the installer ran against the real profile. The shared `run()` helper in `tests/conftest.py` now sets `USERPROFILE` whenever a test overrides `HOME` alone.

## Fixed in v0.89.0

### BUG-008: MCP server crashed at startup ([#45](https://github.com/nseney1/Soma-Governance/issues/45))
`soma_mcp/tools.py` and `soma_sdk/telemetry.py` now guard the POSIX-only `fcntl` import and use platform-appropriate or best-effort locking fallbacks.

### BUG-009: Write/execute MCP tools needed a token hosts could not supply ([#46](https://github.com/nseney1/Soma-Governance/issues/46))
Write and execute tools now use single-use receipts obtained from `soma_request_receipt`. A receipt is bound to the MCP session, canonical workspace, operation, exact arguments, target-file state, and governance-cell state. It is an operation authorization mechanism, not user authentication.

### BUG-011: `install.ps1` did not parse under Windows PowerShell 5.1 ([#48](https://github.com/nseney1/Soma-Governance/issues/48))
The PowerShell scripts now carry a UTF-8 BOM, and CI dry-runs the installer under Windows PowerShell 5.1 as well as PowerShell 7. This fixes parsing, not the separate rule-content decoding problem in BUG-014.

## Open issues

### BUG-036: `uninstall.sh` under Git Bash rejects every path ([#62](https://github.com/nseney1/Soma-Governance/issues/62))
Under Git Bash the removal plan holds MSYS paths (`/c/Users/...`, `/tmp/...`), and the confinement check runs in native Windows Python, where `os.path.isabs()` rejects them. Uninstall refuses every entry and removes nothing. **Workaround:** remove Soma's files by hand.

### BUG-037: Git Bash `python3` may be the Windows Store stub ([#47 comment](https://github.com/nseney1/Soma-Governance/issues/47#issuecomment-5943767333))
A python.org install may not provide `python3.exe`, so `python3` resolves to the App Installer stub. `command -v python3` succeeds but execution fails, preventing hook generation and other shell-script Python calls.

**Workaround:** disable the `python3.exe` App execution alias and put a real `python3` on `PATH`, such as a shim that invokes `python.exe`.

### BUG-012: Implicit cp1252 encoding ([#49](https://github.com/nseney1/Soma-Governance/issues/49))
- `soma status` prints characters that a cp1252 console may reject. **Workaround:** `$env:PYTHONIOENCODING = "utf-8"`.
- `soma_sdk/governance.py` has locale-dependent cell reads; decoding failures can be swallowed and cells omitted.

### BUG-013: Windows-only test failures ([#50](https://github.com/nseney1/Soma-Governance/issues/50))
- `tests/test_verification/test_branch_coverage.py` and `test_mutation_tester.py` write `sys.path.insert(0, '{tmp_path}')` into generated test files. A Windows path contains `\U` (`C:\Users\...`), so the generated file fails with a `unicodeescape` `SyntaxError`. The mutation tester counts the uncompilable test as killing every mutant and reports `verdict=True` (`0/3 survived`), so the tautological-test contract test fails (BUG-034, [#54](https://github.com/nseney1/Soma-Governance/issues/54)).
- `tests/test_init.py` compares Windows paths against POSIX separators, and its symlink test needs Developer Mode (WinError 1314).
- The `bash` fixture in `tests/conftest.py` returns `None` instead of skipping when bash is missing.

CI does not yet run the test suite on Windows ([#56](https://github.com/nseney1/Soma-Governance/issues/56)), so these failures are not caught upstream.

### BUG-032: PowerShell installer does not install lifecycle hooks
`install.ps1` skips hooks because they require Bash, so post-session fitness updates never run after a native PowerShell install.

**Workaround:** install through Git Bash with `install/install.sh`, with a real `python3` on `PATH` (see BUG-037).

### BUG-014: PowerShell installer writes mojibake ([#59](https://github.com/nseney1/Soma-Governance/issues/59), split from [#48](https://github.com/nseney1/Soma-Governance/issues/48))
Windows PowerShell 5.1 decodes UTF-8 rule files using its locale default when `Get-Content` has no explicit encoding, so generated rules can contain mojibake. The PowerShell installer also skips hooks.

**Workaround:** use `pwsh` to avoid the known PS 5.1 decoding problem, while recognizing that PowerShell installer hook parity is still unavailable.
