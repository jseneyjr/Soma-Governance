# Genesis Report & Correctness Audit — Soma

> Generated: 2026-09-29 | Stages: 1–4 (read-only) + 3 correctness audit lanes
> Baseline commit: `1881b33` (branch `main`, clean worktree)
> Scope: production correctness, cross-OS portability, installer/uninstaller parity
> Supersedes: `docs/genesis_report.md` (2026-09-27), retained for diffing

---

## Privacy & Sanitization Notice

This document is written for external distribution. The following substitutions were applied:

| Token | Meaning |
|:------|:--------|
| `<REPO_ROOT>` | Absolute path to the repository checkout |
| `<HOME>` | Operating user's home directory |
| `<CONTRIBUTOR_A>`, `<CONTRIBUTOR_B>` | Git author name strings |

No usernames, hostnames, absolute local paths, credential values, or environment-variable
contents appear below. Environment facts are reported as sanitized aggregates (versions and
booleans), consistent with the Canopy privacy invariant in `organs/genesis/SKILL.md`.

---

## 1. Executive Summary

Three defect classes dominate, and each one independently breaks a core promise of the product:

1. **The uninstaller cannot correctly reverse the installer on any of the five platforms.** The
   manifest records the contents of destination directories rather than what was installed, so
   removal enrolls user-authored files. Backup and restore use different directory names, so
   restore is dead code. Every install deletes all prior backups.
2. **The Windows-native installer installs nothing.** A single missing `..` in path resolution
   points the rule source at a directory that does not exist. There is no PowerShell
   uninstaller at all.
3. **The MCP server cannot start,** because two modules in a package documented as
   zero-dependency perform a bare `import yaml`.

Compounding all three: **the project has no working automated gate.** `make validate` cannot
fail by construction, `install/uninstall.sh` is excluded from validation, and there is no
`tests/` directory, so `make test` passes vacuously. Every finding below shipped through a
green pipeline.

Severity was re-graded from the session's working notes into three tiers for triage. No
finding was withdrawn.

| Severity | Count | Primary impact |
|:---------|:-----:|:---------------|
| Critical | 12 | Silent data loss; total failure of install, uninstall, or MCP |
| High | 11 | Silent wrong behavior; absent verification; corrupted governance state |
| Medium | 8 | Protocol violations; misleading exit codes; drift and accumulation |
| **Total** | **31** | |

---

## 2. Canopy — Repository Structure

### Tech stack

| Aspect | Value |
|:-------|:------|
| Languages | Python, Bash, PowerShell, JavaScript (SDK), Markdown |
| Declared version | `0.25.0` (`VERSION:1`, `pyproject.toml:7`) |
| Python floor | `>=3.9` (`pyproject.toml:11`); CI pins 3.11 |
| Build backend | `setuptools>=68.0` + `wheel` (`pyproject.toml:1-3`) |
| Runtime dependency | `pyyaml>=6.0` — sole required dep (`pyproject.toml:29`) |
| Optional extras | `ai`/`gemini`/`anthropic`/`openai`/`dev` (`pyproject.toml:39-44`) |
| Console entry points | `soma` → `enzymes.soma_cli:main`; `soma-mcp` → `soma_mcp.server:main` |
| Monorepo | No |

### Sanitized dev environment (probe host)

| Probe | Value |
|:------|:------|
| OS / arch | Darwin, arm64 |
| Shell | bash 3.2.57 |
| Python | 3.14 |
| Git | 2.39.5, identity configured |
| Build tools present | make, npm |
| Package managers | brew, pip3, npm |
| Container | false |
| Active virtualenv | false |

> Bash 3.2 is the default interpreter on macOS and is the version that surfaces `SOMA-C03`.

### Layout

```
genome/          — agent behavior rules (7 top-level, 6 more in genome/.oracles/)
organs/          — skill definitions consumed as subagent prompts
enzymes/         — 50 executables (35 .py, 15 .sh); CLI, fitness, cell lifecycle
soma_mcp/        — MCP server (server.py, tools.py, jit_engine.py)
soma_sdk/        — Python SDK (governance.py)
soma_sdk_js/     — JavaScript SDK (not reviewed)
install/         — install.sh, install.ps1, uninstall.sh, hooks/, templates
.soma/cells/     — 18 adaptive governance cells across 5 organelle types
docs/            — reports, metrics, changelog
.github/         — single workflow: validate.yml
```

### Verification surfaces

| Command | Actual behavior |
|:--------|:----------------|
| `make validate` | `bash -n` syntax check only; **cannot fail** (see `SOMA-H01`) |
| `make test` | Runs `validate`, then `pytest tests/` only if pytest exists; **no `tests/` exists** |
| CI | `.github/workflows/validate.yml`, matrix `ubuntu-latest` + `macos-latest` |
| Lint | No lint target; `ruff` declared in the `dev` extra but never invoked |

### Delta from the 2026-09-27 baseline

| Baseline claim | Current reality |
|:---------------|:----------------|
| "Package manager: None detected" | `pyproject.toml` present; packaged as `soma-steering` |
| "Dependencies: Direct: 0" | 1 required (`pyyaml`), 4 optional extras |
| "CI/CD: none detected" | `.github/workflows/validate.yml`, 2-OS matrix |
| "Last release: N/A (No tags)" | 13 SemVer tags, latest `v0.21.1` |
| Entry points: `install.sh`, `Makefile`, `cell_fitness.py` | Adds `soma`, `soma-mcp`, `install.ps1`, MCP server, 2 SDKs |
| Directory `.gemini/` holds cells | Cells now at `.soma/cells/` |

The baseline predates the packaging, MCP, and PowerShell work entirely. It should not be used
for planning.

---

## 3. Rings — History & Risk

| Metric | Value |
|:-------|:------|
| Default / current branch | `main` (clean, tip `1881b33`) |
| Cached remote heads | 3 (`main`, `tempest-fixes`, `fix-15-bugs`) |
| Stale branches (>90d) | 0 |
| Commits in 6-month window | 170 reachable / 167 first-parent, all within the current month |
| Author name strings | 2 (`<CONTRIBUTOR_A>` 167, `<CONTRIBUTOR_B>` 3); no `.mailmap`, likely one person |
| Tags | 13, all lightweight SemVer; latest `v0.21.1` |
| Version drift | `VERSION` and `pyproject.toml` say `0.25.0`; no `v0.25.0` tag exists |
| Test paths in history | **0** — no tracked path matches `tests?/`, `specs?/`, `*_test`, `*.spec` |

### High-risk files (rename-aware churn >5 events AND >200 LOC)

| Path | Events | LOC | Findings landed here |
|:-----|:------:|:---:|:---------------------|
| `install/install.sh` | 11 | 603 | C04, C05, C06, C08, H03 |
| `enzymes/common.sh` | 12 | 363 | M04, M05 |
| `install/uninstall.sh` | 9 | 258 | C07, C09, C10, H03, H07 |
| `soma_mcp/tools.py` | 7 | 373 | C01, H10, M02 |
| `enzymes/cell_fitness.py` | 16 | 369 | H08, M01 |
| `enzymes/cell_promote.py` | 10 | 280 | H09 |
| `enzymes/cell_create.sh` | 10 | 292 | C03 |
| `enzymes/immune_init.sh` | 10 | 271 | — |
| `enzymes/escalation_sentinel.sh` | 6 | 301 | H10 (fail-open gate) |
| `install/install.ps1` | 5 | 636 | C11, C12, H05 |

Churn correctly predicted defect location: 9 of the 10 highest-risk executables carry at least
one finding. `install/install.ps1` sits just below the churn threshold (5 events) yet holds two
Criticals — low churn here reflects low attention, not stability.

---

## 4. Taproot — Architecture & Contracts

### Public surface

| Interface | Count | Location |
|:----------|:-----:|:---------|
| CLI subcommands | 3 (`init`, `doctor`, `status`) | `enzymes/soma_cli.py:112` |
| MCP tools | 10 | `soma_mcp/tools.py:146` |
| JSON-RPC methods | 4 (`initialize`, `tools/list`, `tools/call`, `notifications/initialized`) | `soma_mcp/server.py:23` |
| Installer platforms (Bash) | 5 (`gemini`, `kiro`, `copilot`, `claude`, `mcp`) | `install/install.sh:213` |
| Installer platforms (PowerShell) | 4 — **`mcp` absent** | `install/install.ps1:150` |

A 10-vs-3 asymmetry exists between MCP and CLI: `scan`, `grade`, `coverage`, `fitness`,
`list_cells`, and `report_outcome` have no CLI equivalent, and `cell_promote`, `cell_signal`,
`immune_replay`, and `quorum` have no MCP equivalent. `.soma/cells/plasmodesmata/
contract-mcp-cli-parity.md` names only 6 tools and is itself stale by 4.

### Manifest schema — producer/consumer analysis

`write_manifest()` (`install/install.sh:93`) emits 13 fields. Only 4 are ever read back
(`backup_dir`, `files`, `organs`, `hooks`, all by `install/uninstall.sh`). The 9 unconsumed
fields include `platform` and `scope` — precisely the two that would prevent `SOMA-C07`.

`write_manifest` is invoked for 4 of 5 platforms; the `mcp` branch (`install.sh:556-585`) never
calls it. The local-scope manifest override (`:96-99`) requires `LOCAL_INSTALL=true` **and**
`PLATFORM=gemini`, so non-gemini `--local` installs write a manifest to the global home
labelled `"scope": "global"`.

### Install → manifest → uninstall lifecycle

```
install.sh:12-19   resolve REPO_DIR (symlink-safe, appends /..)
install.sh:23      load_config  → enzymes/common.sh:126
install.sh:58-59   validate_config, resolve_subset
install.sh:62-63   detect_os, resolve_home → common.sh:56, :78
install.sh:88-90   migrate_prism_to_soma  (legacy .prism → .soma)
install.sh:169-176 BACKUP_TS, BACKUP_DIR, then rm -rf of ALL prior backups   ← SOMA-C06
install.sh:178-211 per-platform backup into $BACKUP_DIR/{genome,organs,...}  ← SOMA-C05 origin
install.sh:213-592 per-platform install
install.sh:93-160  write_manifest — find(3) over DESTINATION dirs            ← SOMA-C04
uninstall.sh:34-37 locate manifest (probes $(pwd) unconditionally)           ← SOMA-C07
uninstall.sh:52-72 read manifest via python3 -c in process substitution      ← SOMA-C09
uninstall.sh:165-171 rm -f files / rm -rf dirs
uninstall.sh:228-235 restore from $BACKUP_DIR/{rules,skills,steering}        ← SOMA-C05
```

### Cross-OS boundaries

OS classification happens in exactly one place (`common.sh:56`, 4 tokens: `wsl`, `macos`,
`linux`, `windows`) and feeds only `RESOLVED_HOME`. The platform `case` branches on
`$PLATFORM`, never on `$DETECTED_OS`, so all operating systems target an identical relative
layout differing only in the home prefix. `normalize_path` (`common.sh:108`) is **display-only**
— all call sites are `echo`/`log_info` arguments, so the paths that genuinely need native
Windows form (MCP config JSON) never pass through it.

`install.ps1` performs no OS detection and has no path-normalization abstraction; targets are
literal backslash strings.

---

## 5. Critical Findings

### SOMA-C01 — MCP server cannot start
**`soma_mcp/tools.py:6`, `soma_mcp/jit_engine.py:23`** · verified by execution

Both modules do a bare `import yaml`. Executed on the probe host:

```
$ python3 -m soma_mcp
ModuleNotFoundError: No module named 'yaml'
exit=1, stdout=0 bytes
```

This violates the repo's own `.soma/cells/walls/wall-mcp-zero-deps.md`. It reaches real users
because `install.sh` writes MCP configs as `python3 -m soma_mcp` with `cwd` set to the repo
checkout (`:360`, `:533`, `:572`) rather than the pip-installed package — so the documented
clone-and-install path yields a dead server even though `pyproject.toml` declares the
dependency. The stdlib fallback already present (`_list_cells_stdlib` at `tools.py:52`, the
`_HAS_SDK` guard at `:22-26`, the error message at `:361`) is unreachable dead code that
creates a false impression of graceful degradation.

```diff
-import yaml
+try:
+    import yaml
+except ImportError:
+    yaml = None
```
Then add a `yaml is None` branch to `_parse_frontmatter` in both files.
**Verification:** in an environment without pyyaml, `python3 -m soma_mcp` must answer `tools/list`.

---

### SOMA-C02 — The PreToolUse safety gate never executes
**`enzymes/safety_gate.sh:4`, `enzymes/session_close.sh:4`** · verified by execution

Both files contain literal backslash-escaped quotes inside command substitution:

```bash
DIR="$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd)"
```

Executed: `bash enzymes/safety_gate.sh` → exit 1,
`cd: ""enzymes": No such file or directory`, zero stdout. Both scripts set
`set -euo pipefail` on line 2, so they die before `source "$DIR/common.sh"` on line 5.

`install/hooks.json.template` wires `safety_gate.sh` as the `PreToolUse` gate (`:19`) and
`session_close.sh` as the `Stop` hook (`:30`). Two of the three shipped hooks are inert on
every operating system, and the one that is inert is the safety gate. `enzymes/immune_init.sh:23`
already uses the correct form.

```diff
-DIR="$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd)"
+DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
```
**Verification:** `bash enzymes/safety_gate.sh </dev/null; echo $?` must not emit a `cd` error.

---

### SOMA-C03 — Cell creation writes empty files and reports success
**`enzymes/cell_create.sh:280`** · verified by execution

`## ${TYPE^}: $HYPOTHESIS_TRUNCATED` sits inside an expanded heredoc. `${var^}` is Bash 4+
case conversion; macOS ships Bash 3.2.57. Executed:

```
$ /bin/bash -c 'TYPE=vacuole; echo "## ${TYPE^}: title"'
/bin/bash: ## ${TYPE^}: title: bad substitution   (exit 1)
```

The script sets no `set -e`, so it proceeds to print `Created: <path>` and exit 0 while the
file is 0 bytes. Every downstream consumer then parses a cell with no `fitness:` block.

`bash -n enzymes/cell_create.sh` exits **0** — bad substitution is an expansion-time failure,
so the current syntax-only gate is structurally incapable of catching this. Line 163 of the
same file already uses the portable idiom `tr '[:upper:]' '[:lower:]'`.

This is the only Bash 4 construct in the repository; `declare -A`, `mapfile`, `readarray`,
`local -n`, and `${var,,}` return zero matches across all shell scripts.

```diff
+set -euo pipefail
+TYPE_TITLE="$(printf '%s' "$TYPE" | awk '{print toupper(substr($0,1,1)) substr($0,2)}')"
-## ${TYPE^}: $HYPOTHESIS_TRUNCATED
+## ${TYPE_TITLE}: $HYPOTHESIS_TRUNCATED
```
**Verification:** create a cell under `/bin/bash` and assert the file is non-empty and contains `## Vacuole:`.

---

### SOMA-C04 — Manifest enrolls user-authored files for deletion
**`install/install.sh:118`, `:126`, `:130`** · verified by reading

The manifest is built by `find`-ing the **destination** directory, not by recording what was
copied:

```bash
files_arr="[$(find "$TARGET_RULES" -maxdepth 1 -type f -name "*.md" ...)]"
skills_arr="[$(find "$TARGET_SKILLS" -maxdepth 1 -mindepth 1 -type d ...)]"
hooks_arr="[$(find "$TARGET_HOOKS" -maxdepth 1 -type f ...)]"
```

Anything pre-existing in the target directory is enrolled. On the probe host's live install the
manifest recorded 90 skill directories, of which 74 were installer-generated `.bak.*` copies,
plus one third-party skill and two user-authored hook files that Soma never shipped. Uninstall
would `rm -rf` all of them.

**Fix:** accumulate `INSTALLED_FILES`/`INSTALLED_SKILLS` arrays at each `cp` site and serialize
those. This is the highest-leverage fix in the report — it is the only one that stops collateral
deletion of user data.
**Verification:** install into a directory seeded with a foreign `.md` and a foreign skill dir; assert neither appears in `manifest.json`.

> Attribution note: the live-manifest counts were produced by a delegated audit lane reading
> the probe host's existing `manifest.json`. The code defect is verified by reading; the
> specific counts were not independently re-derived.

---

### SOMA-C05 — Backup restore is dead code
**`install/install.sh:181-194` vs `install/uninstall.sh:228-235`** · verified by grep

Install creates:

```
$BACKUP_DIR/genome     $BACKUP_DIR/organs
$BACKUP_DIR/governance $BACKUP_DIR/hooks
```

Restore reads:

```
$BACKUP_DIR/rules  $BACKUP_DIR/skills     (gemini)
$BACKUP_DIR/steering $BACKUP_DIR/skills   (kiro)
```

Only `governance` and `hooks` intersect. Gemini restores neither rules nor skills; Kiro restores
neither steering nor skills. Each `cp` is guarded by `[ -d ]`, so the failure is silent and the
script still prints `Restore complete.`

The dry-run block at `uninstall.sh:201-207` prints the **correct** names (`genome`, `organs`),
which proves the executing code is the defect rather than the naming convention.

```diff
-            [ -d "$BACKUP_DIR/rules" ] && cp -r "$BACKUP_DIR/rules" "$RESOLVED_HOME/.gemini/config/"
-            [ -d "$BACKUP_DIR/skills" ] && cp -r "$BACKUP_DIR/skills" "$RESOLVED_HOME/.gemini/config/"
+            [ -d "$BACKUP_DIR/genome" ] && cp -r "$BACKUP_DIR/genome" "$RESOLVED_HOME/.gemini/config/rules"
+            [ -d "$BACKUP_DIR/organs" ] && cp -r "$BACKUP_DIR/organs" "$RESOLVED_HOME/.gemini/config/skills"
```
Apply the equivalent correction to the kiro branch (`steering` → `genome`, `skills` → `organs`).
**Verification:** install, uninstall with restore, then assert the pre-install rule set is byte-identical.

---

### SOMA-C06 — Every install destroys the only recovery copy
**`install/install.sh:174`** · verified by reading

```bash
BACKUP_DIR="$RESOLVED_HOME/.soma/backup/$BACKUP_TS"
rm -rf "$RESOLVED_HOME/.soma/backup"      # wipes the parent, all generations
```

The timestamped subdirectory implies retention, but the parent is removed first, so exactly one
generation survives. After the second install that survivor is a copy of Soma's own output; the
genuine pre-Soma configuration is unrecoverable. The probe host showed five install runs and one
surviving generation.

**Fix:** retain N generations and prune oldest-last, never deleting the only copy.
**Verification:** run install twice; assert two generations exist and the older contains the pre-install state.

---

### SOMA-C07 — Uninstall ignores the platform argument
**`install/uninstall.sh:52`** · verified by reading

The manifest branch keys only on `MANIFEST_EXISTS`. `$PLATFORM` is never compared against the
`platform` field that `write_manifest` does record. Running `uninstall.sh mcp` against a
kiro manifest deletes the kiro installation and never touches `.mcp.json`.

The restore half *does* switch on `$PLATFORM` (`:227`), so a single invocation can delete one
platform's files and attempt to restore another's.

Aggravating factor: `:35` probes `$(pwd)/.soma/manifest.json` unconditionally with no platform,
scope, or freshness check. A single past `--local` install in a directory makes every subsequent
uninstall from that directory use the stale local manifest.

**Fix:** refuse to proceed when the manifest's `platform` differs from the requested platform;
require `--force` with an explicit warning to override.
**Verification:** install kiro, run `uninstall.sh mcp`, assert non-zero exit and zero deletions.

---

### SOMA-C08 — `uninstall.sh claude` is a no-op
**`install/install.sh:117-121`** · verified by reading

The `elif` chain is mis-ordered:

```bash
if   [ -n "${TARGET_RULES:-}" ] ...        # unset for claude
elif [ -n "${TARGET_DIR:-}"   ] ...        # SET at :482/:486 → this branch wins
elif [ -n "${TARGET_FILE:-}"  ] ...        # unreachable
```

The claude branch sets `TARGET_DIR` (`:482` = `$(pwd)`, `:486` = `<HOME>/.claude`), so the
second branch matches and searches for `*.instructions.md`, finding nothing. `files_arr` is
`[]` and `CLAUDE.md` is never recorded. `install.sh claude && uninstall.sh claude` reports
success and leaves `CLAUDE.md` fully intact. The generated `.mcp.json` (`:533`) is likewise
never recorded.

**Fix:** test `TARGET_FILE` before `TARGET_DIR`, or select the branch explicitly per platform;
add an MCP-file branch so `.mcp.json` and `mcp.json` are tracked.
**Verification:** install claude, assert `manifest.json` `files` contains `CLAUDE.md`, uninstall, assert it is gone.

---

### SOMA-C09 — Silent no-op uninstall when python3 is absent or JSON is malformed
**`install/uninstall.sh:62`, `:66`, `:70`** · verified by execution

The manifest is parsed by three `python3 -c` invocations inside process substitution. `set -e`
cannot observe failures in `< <(...)`. Verified on Bash 3.2:

```
$ bash -c 'set -euo pipefail; while read -r l; do echo "$l"; done < <(nosuchcmd 2>/dev/null); echo survived'
survived        (exit 0)
```

The removal arrays stay empty, the manifest itself is deleted (`:72`, `:192`),
`Uninstall complete.` prints, and every installed rule survives. A retry then falls through to
the pattern fallback, which per `SOMA-H03` matches nothing — two failed uninstalls, nothing
removed, no error.

Secondary defect on the same lines: the manifest path is interpolated into a Python
single-quoted literal (`open('$MANIFEST_PATH')`). A quote in the path is a `SyntaxError`
silenced by `2>/dev/null`; a crafted directory name is code execution.

```diff
-  done < <(python3 -c "import json, sys; d=json.load(open('$MANIFEST_PATH')); print('\n'.join(d.get('files', [])))")
+  manifest_files="$(SOMA_MF="$MANIFEST_PATH" python3 -c 'import json,os; print("\n".join(json.load(open(os.environ["SOMA_MF"])).get("files",[])))')" || {
+    log_error "Cannot read manifest at $MANIFEST_PATH — refusing to continue."; exit 1; }
+  while IFS= read -r f; do ... done <<< "$manifest_files"
```
**Verification:** corrupt the manifest to invalid JSON, run uninstall, assert non-zero exit and zero deletions.

---

### SOMA-C10 — Uninstall deletes data the installer never created
**`install/uninstall.sh:121-137`** · verified by reading

Unconditionally queued for removal regardless of platform or manifest:

| Path | Nature |
|:-----|:-------|
| `$REPO_DIR/.soma/cells/*` | User-authored governance cells |
| `$REPO_DIR/fitness.jsonl` | Accumulated fitness history |
| `$REPO_DIR/docs/snapshots/*` | Metrics snapshots |
| `$REPO_DIR/soma.conf` | User configuration (unless `--keep-config`) |

`make uninstall` (`Makefile:71`) passes no `--keep-config`, so the documented uninstall path
deletes the user's configuration.

A plan/action mismatch masks the blast radius: `:139` labels every entry `[FILE]` including
directories, while the removal loop at `:165` is `[ -f ]`-guarded. Cell *directories* therefore
survive while the user is told they will be deleted; cells written directly as
`.soma/cells/*.md` **are** deleted.

**Fix:** never delete user-authored content during uninstall. Gate cells, fitness history, and
snapshots behind an explicit `--purge-data` flag, and make the printed plan match the removal
logic exactly.
**Verification:** author a cell, install, uninstall, assert the cell still exists.

---

### SOMA-C11 — The Windows installer installs nothing
**`install/install.ps1:63-66`** · verified by filesystem inspection

```powershell
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path   # → <REPO_ROOT>/install
$RepoDir   = (Resolve-Path $ScriptDir).Path                    # no ".." component
$SourceRules  = Join-Path $RepoDir "genome"                    # → install/genome
$SourceSkills = Join-Path $RepoDir "organs"                    # → install/organs
$ConfigFile   = Join-Path $RepoDir "soma.conf"                 # → install/soma.conf
```

`install/install.sh:19` correctly appends `/..`; the PowerShell port does not. Filesystem check:

```
MISSING  install/genome     MISSING  install/organs     MISSING  install/soma.conf
EXISTS   genome             EXISTS   organs
```

Rule enumeration returns nothing, `soma.conf` is never read on Windows so every configuration
knob is silently ignored, and the script still prints `Done! Installed 0 rules, 0 skills`.

```diff
-$RepoDir = (Resolve-Path $ScriptDir).Path
+$RepoDir = (Resolve-Path (Join-Path $ScriptDir "..")).Path
```
**Verification:** `pwsh -File install\install.ps1 -DryRun` must report a non-zero rule count.

> Not verified at runtime: no PowerShell interpreter was available on the probe host. This
> finding rests on the path arithmetic plus the confirmed-missing directories.

---

### SOMA-C12 — Windows users cannot uninstall
**`install/` (absence)** · verified by filesystem inspection

`find . -name "*.ps1"` returns exactly two files: `install/install.ps1` and the root wrapper.
There is no `uninstall.ps1`. `README.md` documents only `bash install/uninstall.sh`.

A PowerShell-installed user must first obtain Git Bash or WSL, and even then removal fails three
ways: `install.ps1` writes no manifest, so the Bash uninstaller takes the pattern fallback;
that fallback targets stale paths (`SOMA-H03`); and restore is dead code (`SOMA-C05`).
PowerShell's per-item `.bak.<epoch>` siblings (`install.ps1:183`, `:196`) live in a namespace
`uninstall.sh` never reads.

**Fix:** ship `install/uninstall.ps1` with manifest parity, or have `install.ps1` write the same
`manifest.json` schema and document the Bash uninstaller as the supported removal path for
Windows with its prerequisites stated.
**Verification:** end-to-end install/uninstall cycle on a Windows runner leaving no residue.

---

## 6. High Findings

### SOMA-H01 — `make validate` cannot fail
**`Makefile:108-110`** · verified by execution

```make
@for s in install/install.sh enzymes/*.sh; do \
  if [ -f "$$s" ]; then bash -n "$$s" && echo "  ✅ $$s" || echo "  ❌ $$s"; fi; \
done
```

`|| echo` swallows the non-zero status; the loop's exit status is the last `echo`'s. Executed
against a deliberately broken script: loop exit **0**. A syntax error anywhere in `enzymes/`
prints ❌ and CI stays green. `install/uninstall.sh` — the destructive script — is absent from
the file list entirely.

```diff
-	@for s in install/install.sh enzymes/*.sh; do \
-	  if [ -f "$$s" ]; then bash -n "$$s" && echo "  ✅ $$s" || echo "  ❌ $$s"; fi; \
-	done
+	@set -e; for s in install/install.sh install/uninstall.sh enzymes/*.sh; do \
+	  if [ -f "$$s" ]; then bash -n "$$s" && echo "  ✅ $$s" || { echo "  ❌ $$s"; exit 1; }; fi; \
+	done
```
**Verification:** introduce a syntax error; `make validate` must exit non-zero.

### SOMA-H02 — No test suite exists; `make test` passes vacuously
**`Makefile:139-146`** · verified by filesystem inspection

`test` depends on `validate`, then runs `pytest tests/` only `if command -v pytest`. There is no
`tests/` directory and no pytest configuration; git history contains no test path in the last
100 commits. Combined with `SOMA-H01`, the project has no gate capable of failing. This is the
root enabler for the other 30 findings.

**Fix:** add `tests/` with, at minimum, regression coverage for each Critical above; make the
pytest step mandatory rather than conditional.

### SOMA-H03 — Stale `rules`→`genome` rename leaves dead paths
**`install/uninstall.sh:77`, `:80`; `Makefile:127`** · verified by grep

| Site | Path used | Correct? |
|:-----|:----------|:---------|
| `install.sh:220-221` (writes) | `config/rules`, `config/skills` | ✅ |
| `Makefile:93` (`doctor`) | `config/rules` | ✅ |
| `uninstall.sh:77,80` (fallback) | `config/genome`, `config/organs` | ❌ never matches |
| `Makefile:127` (`status`) | `config/genome` | ❌ reports all rules missing |

The rename landed in some call sites only. `make status` reports every rule "not installed" on a
healthy install, and the uninstall fallback removes nothing. This is the repo's own
`.soma/cells/vacuoles/trap-stale-rename-refs.md` firing on the repo.

### SOMA-H04 — 90 `open()` calls, zero with `encoding=`
**`enzymes/`, `soma_mcp/`, `soma_sdk/`** · verified by execution

Mechanical census: **90** `open()` calls (excluding `makedirs` lines), **0** passing `encoding=`.
With `requires-python >=3.9`, PEP 686's UTF-8 default does not apply, so Windows uses the
locale codepage (commonly cp1252). Three of the seven top-level genome rules contain `≥` or `→`
and are not cp1252-encodable. Any Python path reading or rewriting a rule or cell on such a host
raises `UnicodeDecodeError`/`UnicodeEncodeError` or silently mojibakes content.

**Fix:** add `encoding="utf-8"` to all 90 sites — mechanical, high blast radius.
**Verification:** run the suite under `PYTHONUTF8=0` with a non-UTF-8 locale.

### SOMA-H05 — PowerShell installs 7 of 13 rules; team overrides become a no-op
**`install/install.ps1:332` and four peers** · verified by execution

`Get-ChildItem` is non-recursive. Counts: **7** top-level `genome/*.md`, **13** recursive, **6**
in `genome/.oracles/`. Two concrete consequences:

- `RULES_SUBSET=core` requests `testing.md` and `git-workflow.md`, both of which exist **only**
  under `.oracles/`. Windows silently delivers 4 of 6 requested rules.
- `Apply-TeamOverrides` (`:220-303`) appends to `git-workflow.md` in the target directory.
  PowerShell never installs that file, so `TEAM_SIZE=team` and `GIT_STRATEGY=gitflow` produce
  no governance change on Windows.

```diff
-        $ruleFiles = Get-ChildItem -Path $SourceRules -Filter "*.md" | Sort-Object Name
+        $ruleFiles = Get-ChildItem -Path $SourceRules -Filter "*.md" -Recurse -Force | Sort-Object Name
```
`-Force` is required because `.oracles` is a dot-directory.

### SOMA-H06 — CI cannot catch any Windows or runtime defect
**`.github/workflows/validate.yml`** · verified by reading

Matrix is `ubuntu-latest` + `macos-latest`. Zero references to `windows`, `pwsh`, or `ps1` — the
636-line PowerShell installer is never parsed by anything. Only `gemini --dry-run` is exercised,
and `--dry-run` skips backup, manifest write, trigger conversion, hook install, and `.prism`
migration, so no real install path is tested. The uninstall step passes `--dry-run --force` and
returns at `uninstall.sh:158` before any deletion or `sed` runs.

**Fix:** add a `windows-latest` job that parses `install.ps1` via
`[Parser]::ParseFile` and asserts the dry-run rule count is non-zero; add a `macos-latest` job
that *executes* `cell_create.sh` under `/bin/bash` and asserts the cell is non-empty; exercise
all five platforms.

### SOMA-H07 — `--force` disables recovery; prompts abort non-interactively
**`install/uninstall.sh:149`, `:222`, `:150`, `:223`** · verified by execution

`--force` skips the deletion confirmation (`:149`) **and** routes to
`Force mode enabled, skipping restore.` (`:222`). The one flag intended for automation disables
the safety net.

Separately, both `read -p` calls abort under `set -e` at EOF — verified exit 1 with
`</dev/null`. Uninstall therefore dies mid-run in CI, in containers, or under `curl | bash`.

**Fix:** split `--force` (skip confirmation) from `--restore`/`--no-restore`; guard both prompts
with `[ -t 0 ]` and choose a documented default when stdin is not a TTY.

### SOMA-H08 — Fitness signals are written where nothing reads them
**`enzymes/outcome_engine.py:503-507` vs `enzymes/cell_fitness.py:92-98`** · verified by reading

`outcome_engine` writes `triggers`, `true_positives`, `false_positives` at frontmatter **top
level**; `cell_fitness` reads them from the **nested** `fitness` mapping. Every outcome signal
is invisible, so cells remain `triggers=0 → score=None → status="NEW"` permanently, and
promotion/demotion never fires.

Compounding: `outcome_engine.py:494` seeds `fitness` as `{'score': 100, ...}` while the rest of
the system treats `score` as a 0..1 ratio. `jit_engine.get_fitness_score` then returns
`100 * impact_weight`, so any cell `outcome_engine` has touched permanently outranks every other
cell in JIT selection.

```diff
-    fm['triggers'] = fm.get('triggers', 0) + 1
+    fitness['triggers'] = fitness.get('triggers', 0) + 1
...
+    fm['fitness'] = fitness
```
and change the `:494`/`:501` default from `100` to `None`.

### SOMA-H09 — `cell_promote.py` corrupts frontmatter on 9 of 18 cells
**`enzymes/cell_promote.py:106-115`** · verified by reading

`frontmatter_str` retains its trailing newline, so `split('\n')` ends with an empty element. The
`else` branch appends *after* that element, so `new_frontmatter` no longer ends with a newline
and `:115` emits:

```
enforcement: mechanical---
```

`strip_frontmatter` (`enzymes/common.sh:244-245`) matches `/^---$/` strictly, so `in_front`
never resets and the entire cell body is dropped — silently, with exit 0. Mechanical count:
**9 of 18** current cells lack an `enforcement:` key and would take that branch.

```diff
-                    frontmatter_str = content[3:end_idx]
+                    frontmatter_str = content[3:end_idx].strip('\n')
...
-                        f.write(f"---{new_frontmatter}---{content[end_idx+3:]}")
+                        f.write(f"---\n{new_frontmatter}\n---{content[end_idx+3:]}")
```
**Verification:** run `--tier-check --execute` on a cell with no `enforcement:` key; assert `strip_frontmatter` output is byte-identical to the original body.

### SOMA-H10 — `soma_propose_change` writes files despite its ADVISORY label
**`enzymes/ttc_verifier.py:104-114`** · verified by reading

`soma_mcp/tools.py:242` advertises `(PROTOTYPE - ADVISORY ONLY)`, but the handler performs
`os.makedirs` + `open(resolved_path, "w")`. All three gates in front of the write are inert or
fail-open:

| Gate | Failure mode |
|:-----|:-------------|
| Escalation sentinel (`:49-59`) | Returns `breeze` if the script is missing; all exceptions swallowed |
| `TTCVerifier` (`:28-38`) | Only fires when a playbook name contains `React` or `Testing`; repo cells are file stems |
| TTC Oracle (`:94-102`) | Comment claims fail-closed; `ttc_oracle.py:74` returns `APPROVED:` on any exception |

The containment check (`:108`) is correct but runs **after** `proposed_content` has been sent to
an external LLM. Additionally the `__main__` self-test writes `src/App.jsx` into the current
directory.

**Fix:** either remove the write and return a verdict plus diff, or drop the ADVISORY label and
move the containment check to the top of the function, before any I/O or network egress.

### SOMA-H11 — `PromptOnlyProvider` corrupts the MCP transport
**`enzymes/inference_provider.py:113-118`** · verified by reading

`resolve_provider` never returns `None` — the final line returns `PromptOnlyProvider()`. That
provider `print()`s the prompt and then calls `sys.stdin.read()`. Inside the stdio MCP server,
stdout **is** the JSON-RPC transport and stdin **is** the client's request stream. An
unconfigured `soma_propose_change` call therefore emits multi-line non-JSON into the framing and
blocks until EOF, swallowing every subsequent request. The server hangs permanently.
`ttc_verifier.py:81`, `:98`, `:101`, `:104` add four more unconditional `print()` calls on the
same channel.

**Fix:** route all diagnostics in any module reachable from `soma_mcp` to `sys.stderr`; make
`PromptOnlyProvider` raise when `not sys.stdin.isatty()`.

---

## 7. Medium Findings

| ID | Location | Issue | Fix |
|:---|:---------|:------|:----|
| SOMA-M01 | `enzymes/cell_fitness.py:119` | `float('inf')` for every healthy cell serializes as bare `Infinity`; verified `json.dumps` output. Valid for Python clients, rejected by strict TS/Rust/Go MCP hosts | Emit `None` or a finite cap; render `∞` in the formatter only |
| SOMA-M02 | `soma_mcp/server.py:56` | `is_error` keys off `"error" in result`, but `tools.py:307` returns `{"result": "CRITICAL ERROR: …"}` and the audit tools return `{"status": "FAIL"}` — rejections reported as success | Normalize failures to one shape, or key `isError` off an explicit `status` field |
| SOMA-M03 | `enzymes/soma_cli.py:117-119` | Unknown command prints an error and returns `None`; console wrapper calls `sys.exit(None)` → exit 0. `cmd_doctor` prints ❌ and still exits 0, so it cannot gate CI | `return 1`; track a failure flag in `cmd_doctor`; broaden `cmd_status`'s `except ImportError` to catch `RuntimeError`/`FileNotFoundError` |
| SOMA-M04 | `enzymes/common.sh:89`, `:99`, `:103` | `"${HOME:-~}"` does not tilde-expand inside quotes. With `HOME` unset a "global" install lands in `./~/`, and `install.sh:174` runs `rm -rf ./~/.soma/backup` relative to the launch directory | Fail loudly when neither `HOME` nor `USERPROFILE` is set |
| SOMA-M05 | `enzymes/common.sh:211`, `:225` | `.bak.<epoch>` minted per run with no retention. Steering `.bak` files are permanently orphaned because the manifest's `find … -name "*.md"` cannot match `META.md.bak.1790693059` | Cap retention; include `.bak.*` in the removal set or stop creating them per-run |
| SOMA-M06 | `Makefile:25` | Help text says `cp soma.conf.example soma.conf`; the file exists only at `install/soma.conf.example`, while `-include soma.conf` expects it at the root | Correct the path in the help text |
| SOMA-M07 | `VERSION:1`, `pyproject.toml:7`, `soma_mcp/server.py:40` | Declared `0.25.0` in three places with no test tying them together; latest git tag is `v0.21.1` and no `v0.25.0` tag exists | Read via `importlib.metadata`; add a release check that a tag matches `VERSION` |
| SOMA-M08 | `install/install.sh:93-160`; cell producers | 9 of 13 manifest fields have no consumer; `expiry_sessions` is written by three producers and read by none, so cells transferred with only `expiry_sessions` never expire | Consume or delete the fields; implement a session counter if expiry-by-session is intended |

---

## 8. Recommended Fix Order

Ordered by blast radius, with the verification gate first so subsequent fixes are provable.

| # | Findings | Rationale |
|:-:|:---------|:----------|
| 1 | H01, H02 | Without a gate that can fail, no other fix stays fixed |
| 2 | C02 | One-line change; restores the PreToolUse safety gate |
| 3 | C03 | One-line change plus `set -euo pipefail`; stops silent empty-cell creation |
| 4 | C01 | Guard two imports; restores MCP and makes the existing fallback real |
| 5 | C11, H05 | Two-line change; makes the Windows installer function at all |
| 6 | C04 | Record what you copy; stops collateral deletion of user data |
| 7 | C06, C05 | Backup retention, then restore directory names |
| 8 | C07, C08, C09, C10, H07 | Uninstall hardening as one coherent change |
| 9 | H06 | Add Windows + execution jobs so 3–8 cannot regress |
| 10 | C12, H03, H04 | Windows uninstaller, stale paths, encoding sweep |
| 11 | H08, H09, H10, H11, M01–M08 | Runtime correctness and protocol conformance |

---

## 9. Governance Recommendations (Lichen)

### Conventions observed

| Aspect | Value |
|:-------|:------|
| Naming | `snake_case` for scripts and Python, `kebab-case` for markdown |
| Formatting | No formatter configured; `ruff` declared in `dev` extra but never invoked |
| Shell error handling | `set -euo pipefail` in installers; **absent** from `cell_create.sh` |
| Python error handling | Predominantly `except Exception: pass` — 17 such handlers in `outcome_engine.py` alone |

### Suggested review posture

| Path | Minimum protocol | Rationale |
|:-----|:-----------------|:----------|
| `install/**` | Highest available | 5 Criticals; destructive operations; no test coverage |
| `enzymes/common.sh` | Highest available | Sourced by 9 scripts; sole OS-detection site |
| `soma_mcp/**` | Elevated | Protocol conformance; zero-dependency invariant |
| `enzymes/*.py` (cell lifecycle) | Elevated | Rewrites user governance state in place, non-atomically |
| `genome/**`, `organs/**` | Standard | Content changes, no execution path |

### Suggested new cells (Cytogenesis)

Genesis is read-only, so these are proposals rather than generated artifacts:

1. **Vacuole — Bash 4 constructs.** Catch `${var^}`, `${var,,}`, `declare -A`, `mapfile`,
   `readarray`, `local -n`. Predicts `SOMA-C03`. Falsifiable: 0 findings in 10 sessions → prune.
2. **Vacuole — install/uninstall path symmetry.** Assert every literal path written by
   `install.sh` appears in `uninstall.sh` or the manifest. Predicts C04, C05, C08, H03.
3. **Wall — installer path rename boundary.** Any path-literal change under `install/` must be
   applied consistently across `install.sh`, `uninstall.sh`, `install.ps1`, and `Makefile`.
   Predicts H03.
4. **Vacuole — exit-code masking.** Catch `cmd && echo || echo` in Makefile recipes and
   verification loops. Predicts H01.
5. **Vacuole — unencoded file I/O.** Catch `open(` without `encoding=`. Predicts H04.

Two existing cells were correct and unheeded: `wall-mcp-zero-deps.md` predicted `SOMA-C01`, and
`trap-stale-rename-refs.md` predicted `SOMA-H03`. The immune system detected these classes; the
gap is enforcement, not detection.

### Context pre-seeding block

```
<!-- CONTEXT: Soma -->
[PROJECT]: Soma — adaptive governance framework for AI coding assistants
[STACK]: Python >=3.9 | Bash 3.2-compatible | PowerShell | PyYAML | Test: `make test` (NO tests/ exist)
[LAYOUT]:
  - `genome/`: agent behavior rules (7 top-level + 6 in .oracles/)
  - `organs/`: subagent skill definitions
  - `enzymes/`: CLI, fitness, cell lifecycle (50 files)
  - `install/`: install.sh, install.ps1, uninstall.sh
  - `soma_mcp/`: MCP server; must stay zero-dependency
  - `.soma/cells/`: 18 adaptive governance cells
[CONSTRAINTS]:
  - Bash must run on macOS Bash 3.2 — no ${var^}, declare -A, mapfile
  - `make validate` cannot currently fail; do not treat green as passing
  - Installer path literals must change in 4 files at once (sh/ps1/uninstall/Makefile)
  - All open() calls need encoding="utf-8" for Windows
  - No raw paths, usernames, or env values in any output
[OUTPUT]: Max 5 bullets per section. Cite file:line.
<!-- END CONTEXT -->
```

---

## 10. Scope & Limitations

### Verified by execution on the probe host
`SOMA-C01`, `C02`, `C03`, `C09`, `H01`, `H04`, `H05`, `H07`, `H09` (count), `M01`; plus the
absence of Bash 4 constructs, the absence of GNU-only utility flags, and the missing PowerShell
source directories.

### Verified by reading exact lines, not executed
`SOMA-C04` (code path), `C05`, `C06`, `C07`, `C08`, `C10`, `C12`, `H02`, `H03`, `H06`, `H08`,
`H09` (mechanism), `H10`, `H11`, `M02`–`M08`.

### Not verified
| Item | Reason |
|:-----|:-------|
| `install.ps1` runtime behavior (`SOMA-C11`, `H05`) | No PowerShell interpreter on the probe host |
| `resolve_home` WSL and Windows branches | Cannot be exercised from macOS |
| Live-manifest counts in `SOMA-C04` | Produced by a delegated lane; code defect verified, counts not re-derived |
| Installed-wheel console-script behavior | Would require mutating the environment |
| Whether GitHub's `macos-latest` default `bash` is 3.2 or Homebrew 5 | Not determinable from the repository |

### Explicitly out of scope
`soma_sdk_js/`, `organs/*/SKILL.md` contents, `templates/`, `immune_system/`, and the individual
argparse surfaces of the ~35 `enzymes/*.py` CLIs.

### Method integrity
No installer, uninstaller, or write-path Python was executed against live configuration. All
probes were read-only or confined to temporary directories and cleaned up. The repository
remained at `1881b33` with a clean worktree throughout the audit; these two report files are the
only additions.
