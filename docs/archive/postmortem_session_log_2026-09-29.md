# Sanitized Session Log — Genesis & Correctness Audit

> Session date: 2026-09-29 | Baseline commit: `1881b33` | Outcome: 31 findings, 0 repo mutations
> Companion artifact: `docs/genesis_report_2026-09-29.md`
> Purpose: blameless post-mortem input. Documents *how* the audit was run, what the process got
> wrong, and which claims carry which evidence grade.

---

## Privacy & Sanitization Notice

This log was sanitized for external distribution. Substitutions applied:

| Token | Replaces |
|:------|:---------|
| `<REPO_ROOT>` | Absolute path to the repository checkout |
| `<HOME>` | Operating user's home directory |
| `<CONTRIBUTOR_A>`, `<CONTRIBUTOR_B>` | Git author name strings |
| `<THIRD_PARTY_SKILL>` | Name of a non-Soma skill found in the live install |
| `<USER_HOOK_A>`, `<USER_HOOK_B>` | Names of two user-authored hook files |

Removed entirely: machine identifiers, kernel build strings, git user identity values, and
credential/environment-variable contents. Retained deliberately: OS family and architecture,
tool version numbers, commit SHA, repo-relative paths, and line numbers — all required for the
post-mortem to be actionable, none personally identifying.

Two files were added to the repository (this log and the companion report). No other file was
created, modified, or deleted; the worktree was verified clean at start and end.

---

## 1. Session Objective

As stated by the requester: run a Genesis reconnaissance, then highlight production-level fixes,
cross-OS fixes, and installer/uninstaller fixes, with a general focus on bugs and correctness.

Interpretation applied: Genesis Stages 1–4 (read-only) for situational awareness, followed by a
correctness audit weighted toward the three named areas. Stage 5 (Cytogenesis) was deliberately
downgraded to written recommendations rather than generated cells, because Genesis carries a
read-only invariant and cell generation had not been requested.

---

## 2. Timeline

| Phase | Action | Result |
|:------|:-------|:-------|
| 1 | Activated Genesis protocol + staff-review protocol | Both loaded |
| 2 | Created 7-task plan | Accepted |
| 3 | Sanitized environment probe (single shell command) | Darwin/arm64, Bash 3.2.57, Python 3.14, Git 2.39.5, clean worktree |
| 4 | **Canopy** — dispatched `context-gatherer` + 7 parallel file reads | Success; identified prior report as materially stale |
| 5 | **Rings** — dispatched 1 read-only history analyst | Success; 170 commits, 13 tags, churn/LOC risk intersection |
| 6 | **Taproot** — dispatched 1 architecture analyst | **Aborted by requester mid-flight** |
| — | *Session interrupted and resumed* | State re-verified: HEAD unchanged, worktree clean |
| 7 | Re-dispatched **Taproot** | Success; full contract map, producer/consumer analysis |
| 8 | Dispatched 3 audit lanes as `code-review` | **Failed — agent not in registry (3 wasted dispatches)** |
| 9 | Re-dispatched the same 3 lanes as `general-task-execution` with the review protocol inlined | All 3 succeeded |
| 10 | Independent verification of Critical claims (11 shell invocations) | 10 usable, 1 abandoned on timeout |
| 11 | Synthesis into severity-graded report; count verification by grep | 12 C / 11 H / 8 M = 31 confirmed |
| 12 | PII scan of the output artifact | Clean |

---

## 3. Delegation Accounting

| Dispatch | Agent | Lens | Outcome |
|:---------|:------|:-----|:--------|
| 1 | `context-gatherer` | Canopy / structure | Success |
| 2 | `general-task-execution` | Rings / history | Success |
| 3 | `general-task-execution` | Taproot / architecture | Aborted by requester |
| 4 | `general-task-execution` | Taproot / architecture (retry) | Success |
| 5–7 | `code-review` ×3 | installer, cross-OS, runtime | Failed — not in registry |
| 8 | `general-task-execution` | Installer/uninstaller parity | Success |
| 9 | `general-task-execution` | Cross-OS portability | Success |
| 10 | `general-task-execution` | Runtime Python/MCP/CLI | Success |

**Attempts: 10. Productive returns: 6. Failures: 3 registry, 1 abort.**

Concurrency held at 4 read-only agents maximum. No writer agents were dispatched, so the
disjoint-lane protocol was not exercised. Orthogonality was enforced by assigning conflicting
objectives — installer symmetry vs. OS portability vs. runtime data integrity — and the three
lanes produced non-overlapping finding sets, which is the intended signal that the lens
assignment worked.

---

## 4. Process Failures

### PF-1 — Three dispatches wasted on a non-existent agent
**Impact: 3 of 10 dispatches (30%).** `code-review` exists as a *skill*, not a registered
*agent*. All three audit lanes were dispatched to it simultaneously and all three returned
`Agent 'code-review' not found in registry`.

Root cause: the skill name was assumed to be an agent name without checking the registry. The
failure was cheap to recover (re-dispatch with the protocol inlined into
`general-task-execution` prompts) but entirely avoidable.

**Corrective action:** verify agent availability before any fan-out; when a protocol lives in a
skill rather than an agent, inline it into the prompt from the outset.

### PF-2 — Shell quoting and batching failures
**Impact: 3 commands produced garbled or empty output; ~4 wasted invocations.**

| Symptom | Cause |
|:--------|:------|
| Multi-check batch returned empty, exit 1 | Too many chained checks with embedded quotes in one command string |
| `zsh: no matches found: --include=*.py` | Unquoted glob pattern consumed by zsh before reaching grep |
| Multi-line Python collapsed into a `SyntaxError` | Newlines inside a single-line `python3 -c` argument |
| One command blocked after exceeding approval rounds | Heredoc inside a chained command list |

**Corrective action:** one verification per invocation; always quote glob patterns for grep;
never embed multi-line Python in a single-line `-c` argument; avoid heredocs inside chained
command lists.

### PF-3 — Abandoned reproduction after a timeout
**Impact: 1 finding's evidence grade reduced.** An attempt to reproduce the `SOMA-H09`
frontmatter corruption end-to-end sourced `enzymes/common.sh` into an interactive shell to call
`strip_frontmatter`; the command hit the 60-second timeout and returned stale output.

The attempt was abandoned rather than retried, and the finding was reported on code-reading
evidence plus a delegated lane's independent reproduction. This is disclosed in the report's
evidence table rather than papered over.

**Corrective action:** run shell-function reproductions in a non-interactive subshell with an
explicit timeout, or reproduce the logic in Python instead of sourcing a large shell library.

### PF-4 — A planned stage was interrupted and required state re-verification
**Impact: low; 1 dispatch repeated.** Taproot was aborted mid-flight and the session resumed
later. Resumption correctly re-verified HEAD, branch, worktree cleanliness, version, and the
absence of `tests/` before continuing rather than trusting remembered state. No corrective
action needed — this is the desired behavior after an interruption.

---

## 5. Evidence Grading

Every finding was assigned one of three grades. This is the most important section for the
post-mortem, because it bounds how much the report can be trusted without re-verification.

| Grade | Meaning | Count |
|:------|:--------|:-----:|
| **A — Executed** | Reproduced by running a command on the probe host | 10 |
| **B — Read** | Verified by reading the exact cited line, not executed | 20 |
| **C — Inferred** | Reasoned from code plus environment facts; runtime unverified | 1 |

### Grade A (executed)
`SOMA-C01` (server exits 1, `ModuleNotFoundError`), `C02` (`safety_gate.sh` exits 1 with `cd`
error), `C03` (`bad substitution` on Bash 3.2; `bash -n` exits 0), `C09` (process substitution
survives a failed command under `set -e`), `H01` (masked loop exits 0 on a broken script),
`H04` (90 `open()` calls, 0 with `encoding=`), `H05` (7 top-level vs 13 recursive rules),
`H07` (`read -p` exits 1 at EOF), `H09` (9 of 18 cells lack `enforcement:`),
`M01` (`json.dumps` emits bare `Infinity`).

Also executed as negative confirmations: zero Bash 4 constructs beyond `SOMA-C03`; zero GNU-only
utility flags; `install/genome`, `install/organs`, `install/soma.conf` all absent; only two
`.ps1` files exist repo-wide.

### Grade C (inferred, single finding)
`SOMA-C11` — the PowerShell repo-root defect. No PowerShell interpreter was available. The
finding rests on the path arithmetic at `install.ps1:63-66` plus filesystem confirmation that
all three derived source paths are missing. The precise runtime symptom is unverified and the
report says so.

### Boundary verification performed on delegated claims
Per protocol, subagent findings were spot-checked rather than propagated on trust:

- File existence and line locality re-checked for every Critical.
- Three line-number errors in briefings *I* supplied were caught and corrected by a lane
  (cells block is `uninstall.sh:118-121` not `:121-133`; copilot fallback `:97` not `:108`;
  gemini fallback globs `:77`/`:80`).
- One lane self-corrected a call-site miscount (`backup_dir` appears as a manifest *key* at
  `uninstall.sh:54` and `install.sh:151`, not as a function call).
- One numeric discrepancy was resolved in favor of my own count: a lane reported 91 `open()`
  calls; my mechanical count returned 90. The report states 90.

### Claims accepted without independent re-derivation
The live-manifest statistics in `SOMA-C04` (90 recorded skill dirs, 74 of them `.bak.*`, one
`<THIRD_PARTY_SKILL>`, `<USER_HOOK_A>` and `<USER_HOOK_B>`) came from a lane reading the probe
host's existing `manifest.json`. The **code defect** is Grade B; the **counts** were not
re-derived. Flagged in the report.

---

## 6. Findings Refuted

A review that only confirms hypotheses is not a review. Six plausible defects were investigated
and **rejected** with evidence, and are recorded so nobody re-litigates them:

| Hypothesis | Verdict | Evidence |
|:-----------|:--------|:---------|
| `${arr[0]:-default}` is unsafe on an empty array under Bash 3.2 `set -u` | **Refuted** | Returns the fallback, exit 0. `install.sh:54,56` and `uninstall.sh:30` are correct |
| `rm -rf` targets could expand to `/` or another unintended root | **Refuted** | Every `resolve_home` branch returns non-empty; loops are `[ -f ]`/`[ -d ]`-guarded. Worst case is a literal `~` directory (logged as `SOMA-M04`, not a root wipe) |
| `cp -r` during restore nests directories | **Refuted** | Tested: merges rather than nesting |
| The `jq` filter at `uninstall.sh:185` is syntactically invalid | **Refuted** | Valid in jq 1.7.1. The real defect is semantic — it targets a key the installer never writes |
| Re-installing duplicates merged rule content in `CLAUDE.md` / `copilot-instructions.md` | **Refuted** | Both truncate before appending; re-runs are byte-identical |
| Widespread GNU vs BSD utility divergence | **Refuted** | The only `sed -i` usage is the portable `-i.bak` form. One latent GNU-ism (`\L`) found, unreachable in practice |

---

## 7. Efficiency Notes

Deliberately reported as observations rather than a scored metric, since a single audit session
is too small a sample for a meaningful waste-rate figure.

| Observation | Detail |
|:------------|:-------|
| Wasted dispatches | 3 of 10 (PF-1), all from one avoidable assumption |
| Wasted shell invocations | ~4 of ~15 (PF-2), all from quoting/batching, all recoverable |
| Parallelism achieved | 4 concurrent read-only agents; 7 file reads batched alongside dispatch 1 |
| Context discipline | All deep file traversal delegated; the orchestrator retained synthesis and severity grading only |
| Rework on findings | Zero findings withdrawn after verification; 1 numeric claim corrected downward; 6 hypotheses refuted before reaching the report |

The dominant inefficiency was not analysis — it was tooling assumptions (a non-existent agent
name, shell quoting). Both are mechanically preventable.

---

## 8. Observations for the Post-Mortem Discussion

These are framed as questions for the team, not conclusions.

1. **The immune system detected two of these classes and was not heeded.**
   `wall-mcp-zero-deps.md` predicts `SOMA-C01` and `trap-stale-rename-refs.md` predicts
   `SOMA-H03`. Both cells exist, both are correct, both describe live defects. One of them was
   scored with a false positive. The gap is enforcement and fitness feedback, not detection —
   which connects directly to `SOMA-H08`, where outcome signals are written to keys nothing
   reads. Worth asking: can a cell that is factually correct currently be rewarded?

2. **Every finding shipped through a green pipeline.** `make validate` cannot fail (`SOMA-H01`),
   `make test` has no tests (`SOMA-H02`), and CI never parses the PowerShell installer
   (`SOMA-H06`). The verification layer reports success unconditionally. Worth asking: was the
   green signal ever validated against a known-bad input?

3. **Defect density tracked inattention, not churn.** `install.ps1` has the lowest churn of the
   large executables (5 events, 636 LOC) and carries two Criticals. The highest-churn file
   (`README.md`, 48 events) carries none. Churn predicted *where* code was risky; absence of
   churn predicted *where nobody was looking*.

4. **Three of the twelve Criticals are one-line fixes** (`C02`, `C03`, `C11`). Two more are
   small (`C05`, `C06`). The severity distribution reflects missing verification rather than
   deep architectural problems, which is a comparatively good position to be in.

5. **`--force` currently disables the safety net** (`SOMA-H07`). The flag intended for
   automation skips confirmation *and* skips restore. Worth asking whether any automated
   uninstall path has been exercised since that flag was added.

---

## 9. Reproduction Commands

All commands are read-only and were run from the repository root. Paths are repo-relative.

```bash
# Baseline state
git rev-parse --short HEAD && git status --short | wc -l

# SOMA-C03: Bash 4 construct fails on macOS Bash 3.2
/bin/bash -c 'TYPE=vacuole; echo "## ${TYPE^}: title"'        # -> bad substitution, exit 1
/bin/bash -n enzymes/cell_create.sh                            # -> exit 0 (gate is blind)

# SOMA-C02: hook dies before sourcing common.sh
bash enzymes/safety_gate.sh                                    # -> exit 1, cd: ""enzymes"
grep -n 'BASH_SOURCE' enzymes/safety_gate.sh enzymes/session_close.sh enzymes/immune_init.sh

# SOMA-C01: MCP server cannot start without pyyaml
grep -n 'import yaml' soma_mcp/tools.py soma_mcp/jit_engine.py
python3 -m soma_mcp                                            # -> ModuleNotFoundError, exit 1

# SOMA-H01: validate loop masks failure
printf 'x() {\n' > /tmp/broken.sh
bash -c 'for s in /tmp/broken.sh; do bash -n "$s" && echo OK || echo FAIL; done'; echo "exit=$?"

# SOMA-C05: backup writes vs restore reads
grep -n 'BACKUP_DIR/genome\|BACKUP_DIR/organs' install/install.sh
grep -n 'BACKUP_DIR/rules\|BACKUP_DIR/skills\|BACKUP_DIR/steering' install/uninstall.sh

# SOMA-H03: stale rename across call sites
grep -n 'gemini/config/rules\|gemini/config/genome' install/install.sh install/uninstall.sh Makefile

# SOMA-C11 / C12: PowerShell source paths and missing uninstaller
for p in install/genome install/organs install/soma.conf genome organs; do
  test -e "$p" && echo "EXISTS $p" || echo "MISSING $p"; done
find . -name "*.ps1" -not -path "./.git/*"

# SOMA-H04: encoding census
grep -rn "open(" --include="*.py" enzymes soma_mcp soma_sdk | grep -v makedirs | wc -l
grep -rn "open(" --include="*.py" enzymes soma_mcp soma_sdk | grep -c "encoding="

# SOMA-H05: rule discovery depth
ls -1 genome/*.md | wc -l && find genome -type f -name '*.md' | wc -l

# SOMA-H09: cells lacking the enforcement key
total=0; missing=0
for f in .soma/cells/*/*.md; do total=$((total+1));
  grep -q '^enforcement:' "$f" || missing=$((missing+1)); done
echo "total=$total missing=$missing"

# SOMA-M01: invalid JSON constant on the wire
python3 -c "import json; print(json.dumps({'snr_db': float('inf')}))"
```

---

## 10. Method Integrity Statement

- Genesis Stages 1–4 were run read-only. Stage 5 produced written recommendations only.
- No installer, uninstaller, or write-path Python was executed against live configuration.
- Probe artifacts were confined to temporary directories and removed.
- The repository remained at `1881b33` with a clean worktree for the entire audit; the two
  report files are the only additions.
- Environment facts are reported as sanitized aggregates. No raw paths, usernames, hostnames,
  or credential values appear in either artifact.
- Where a claim could not be verified, the artifact says so explicitly rather than presenting an
  inference as a fact.
