# Tempest Review — Soma Governance Repo

> **Scope**: All changes between `1881b33` (genesis baseline) and `02deea8` (GPT Sol 5.6 session)
> **Files changed**: 48 (+4,531 / −463 lines)
> **Protocol**: Tempest (auto-escalated: HIGH-sensitivity paths across `install/`, `enzymes/`, `soma_mcp/`)
> **Prongs dispatched**: 4 Spores (Installer Correctness, Shell Safety, Python Runtime, Test Suite Quality)
> **Date**: 2026-09-29

---

## Verdict: REVISE

The session fixed **22 of 31 genesis findings** — an impressive throughput. However, **3 findings remain unfixed**, **6 are partial**, and the new test suite has a logic bug and is never executed by CI. The CI pipeline itself was left unchanged, meaning no automated gate exists for the new tests.

---

## 🔴 Critical Findings (3)

### TEMPEST-01 — CI does not run the new test suite (SOMA-H06 unfixed)

[`.github/workflows/validate.yml`](file:///home/nseney/.gemini/antigravity/scratch/soma-governance-review/Soma-Governance/.github/workflows/validate.yml) was not modified. The workflow runs `make validate` only. It does not:
- Install `pytest`
- Run `make test`
- Include a `windows-latest` matrix entry
- Parse `install.ps1` or `uninstall.ps1`

The entire new test suite is a local-only safety net. The Makefile `test` target ([Makefile:159-165](file:///home/nseney/.gemini/antigravity/scratch/soma-governance-review/Soma-Governance/Makefile#L159-L165)) also degrades to a vacuous pass when pytest is missing:

```make
@if command -v pytest >/dev/null 2>&1; then \
  pytest tests/ || exit 1; \
else \
  echo "  ⚠️  pytest not found, skipping Python tests."; \
fi
@echo "All tests passed."
```

The "All tests passed." line executes unconditionally — even when pytest was skipped.

**Impact**: Every fix in this changeset can regress silently. The genesis report's observation #2 ("every finding shipped through a green pipeline") remains true.

---

### TEMPEST-02 — Test assertion logic bug masks C02 regression

[`tests/test_static_invariants.py:80`](file:///home/nseney/.gemini/antigravity/scratch/soma-governance-review/Soma-Governance/tests/test_static_invariants.py#L80):
```python
assert "No such file or directory" not in combined or "cd:" not in combined, (
```

The `or` operator means the assertion passes if **either** substring is absent. The correct logic requires `and` — both must be absent to confirm no directory resolution failure.

Additionally, line 78 uses `source "$path" 2>&1 || true`, which discards the exit code. Even if the script exits non-zero, the test passes.

**Impact**: A regression reintroducing the escaped-quote bug in `safety_gate.sh` would not be caught.

---

### TEMPEST-03 — TTC Oracle remains fail-open (SOMA-H10 partial)

[`enzymes/ttc_oracle.py:74`](file:///home/nseney/.gemini/antigravity/scratch/soma-governance-review/Soma-Governance/enzymes/ttc_oracle.py#L74):
```python
except Exception as e:
    return f"APPROVED: Oracle evaluation failed ({str(e)})"
```

Any exception (network timeout, malformed input, configuration error) results in an automatic approval. Combined with the escalation sentinel now defaulting to `"tempest"` instead of `"breeze"`, the Oracle is the last remaining fail-open gate in the TTC pipeline.

**Impact**: A file-write proposal that should be rejected by the Oracle could be approved if the inference provider raises any exception.

---

## ⚠️ Warnings (5)

### TEMPEST-W01 — Backup restore never tested at runtime (SOMA-C05 partial coverage)

Every integration test passes `--no-restore` ([test_install_lifecycle.py:72](file:///home/nseney/.gemini/antigravity/scratch/soma-governance-review/Soma-Governance/tests/test_install_lifecycle.py#L72)). The backup directory name fix (genome→rules, organs→skills) was verified by static grep only, never by actually running a restore.

### TEMPEST-W02 — `.bak.*` orphan cleanup not addressed (SOMA-M05 partial)

A retention cap (`MAX_BAK_FILES=5`) was added to `enzymes/common.sh`, but the manifest's `find` pattern still cannot match `.bak.*` files. Prior installs may have dozens of orphaned backup files that will never be cleaned up.

### TEMPEST-W03 — Version consistency still fragile (SOMA-M07 partial)

`soma_mcp/server.py` reads version via `importlib.metadata` with an `except Exception` fallback to `"0.25.0"`. When running from source (the development case), this always falls back — which is precisely the scenario where drift occurs.

### TEMPEST-W04 — `ttc_verifier.py` `__main__` self-test writes files

The `__main__` block still writes `src/App.jsx` into the current directory when run directly. Not a runtime risk but a development hygiene issue.

### TEMPEST-W05 — No test for Claude platform manifest (SOMA-C08)

The `elif` reordering fix was verified by code reading but has no integration test specifically covering `install.sh claude`.

---

## ✅ Confirmed Fixes (22)

| Finding | Verdict | Evidence |
|:--------|:--------|:---------|
| **SOMA-C01** | ✅ FIXED | `yaml` import guarded with try/except + regex fallback in both [tools.py:6-9](file:///home/nseney/.gemini/antigravity/scratch/soma-governance-review/Soma-Governance/soma_mcp/tools.py#L6-L9) and [jit_engine.py:23-26](file:///home/nseney/.gemini/antigravity/scratch/soma-governance-review/Soma-Governance/soma_mcp/jit_engine.py#L23-L26) |
| **SOMA-C02** | ✅ FIXED | Escaped quotes removed in [safety_gate.sh:4](file:///home/nseney/.gemini/antigravity/scratch/soma-governance-review/Soma-Governance/enzymes/safety_gate.sh#L4) and [session_close.sh:4](file:///home/nseney/.gemini/antigravity/scratch/soma-governance-review/Soma-Governance/enzymes/session_close.sh#L4) |
| **SOMA-C03** | ✅ FIXED | Portable `awk` title-case + `set -euo pipefail` in [cell_create.sh](file:///home/nseney/.gemini/antigravity/scratch/soma-governance-review/Soma-Governance/enzymes/cell_create.sh#L3) |
| **SOMA-C04** | ✅ FIXED | Manifest now records `INSTALLED_FILES`/`INSTALLED_SKILLS`/`INSTALLED_HOOKS` arrays at copy sites |
| **SOMA-C05** | ✅ FIXED | Restore paths corrected (genome→rules, organs→skills) in [uninstall.sh:248-269](file:///home/nseney/.gemini/antigravity/scratch/soma-governance-review/Soma-Governance/install/uninstall.sh#L248-L269) |
| **SOMA-C06** | ✅ FIXED | Backup retention with `MAX_BACKUPS=3` and oldest-first pruning |
| **SOMA-C07** | ✅ FIXED | Platform validation with `--force` override at [uninstall.sh:55-60](file:///home/nseney/.gemini/antigravity/scratch/soma-governance-review/Soma-Governance/install/uninstall.sh#L55-L60) |
| **SOMA-C08** | ✅ FIXED | `elif` chain reordered: `TARGET_FILE` tested before `TARGET_DIR` |
| **SOMA-C09** | ✅ FIXED | Process substitution replaced with command substitution; `SOMA_MANIFEST` env var used (path injection resolved) |
| **SOMA-C10** | ✅ FIXED | User data gated behind `--purge-data` flag |
| **SOMA-C11** | ✅ FIXED | `Resolve-Path (Join-Path $ScriptDir "..")` added |
| **SOMA-C12** | ✅ FIXED | New 823-line [uninstall.ps1](file:///home/nseney/.gemini/antigravity/scratch/soma-governance-review/Soma-Governance/install/uninstall.ps1) with manifest/restore parity |
| **SOMA-H01** | ✅ FIXED | Validate recipe exits non-zero on syntax errors |
| **SOMA-H03** | ✅ FIXED | Stale `config/genome`→`config/rules` paths corrected |
| **SOMA-H04** | ✅ FIXED | **91/91** `open()` calls now have `encoding="utf-8"` (mechanically verified) |
| **SOMA-H05** | ✅ FIXED | `-Recurse -Force` flags on `Get-ChildItem` |
| **SOMA-H07** | ✅ FIXED | `--force` separated from `--no-restore`; TTY detection added |
| **SOMA-H08** | ✅ FIXED | Outcome signals now write to nested `fitness` mapping |
| **SOMA-H09** | ✅ FIXED | Frontmatter trailing-newline corruption resolved |
| **SOMA-H11** | ✅ FIXED | `PromptOnlyProvider` raises on non-TTY; all `print()` routed to stderr |
| **SOMA-M01** | ✅ FIXED | `float('inf')` → `None` across all sites |
| **SOMA-M02** | ✅ FIXED | Error detection normalized with explicit `status` field |
| **SOMA-M03** | ✅ FIXED | CLI returns 1 on unknown commands; `cmd_doctor` tracks failures |
| **SOMA-M04** | ✅ FIXED | Fails loudly when `HOME`/`USERPROFILE` both unset |
| **SOMA-M06** | ✅ FIXED | Help text path corrected |

---

## ⚡ Partial / Unfixed Summary

| Finding | Status | Gap |
|:--------|:-------|:----|
| **SOMA-H02** | PARTIAL | Test suite exists but `make test` passes vacuously without pytest |
| **SOMA-H06** | ❌ UNFIXED | CI pipeline unchanged — no pytest, no Windows, no PS1 parsing |
| **SOMA-H10** | PARTIAL | Containment + escalation fixed; oracle fail-open + self-test write remain |
| **SOMA-M05** | PARTIAL | Retention cap added; orphan cleanup for prior installs missing |
| **SOMA-M07** | PARTIAL | importlib.metadata added but fallback defeats purpose |
| **SOMA-M08** | ❌ UNFIXED | 9 unconsumed manifest fields, session expiry not implemented |

---

## New Defects Introduced

| ID | Severity | Location | Issue |
|:---|:---------|:---------|:------|
| **TEMPEST-02** | 🔴 Critical | [test_static_invariants.py:80](file:///home/nseney/.gemini/antigravity/scratch/soma-governance-review/Soma-Governance/tests/test_static_invariants.py#L80) | `or` should be `and` in assertion — masks safety gate regressions |
| **TEMPEST-W04** | ⚠️ Warning | `enzymes/ttc_verifier.py` `__main__` | Self-test writes `src/App.jsx` to cwd |

---

## Verification Methodology

All Spores claims were boundary-verified against the actual codebase:

| Claim | Verification | Result |
|:------|:-------------|:-------|
| Path injection in `uninstall.sh` | `grep -n "SOMA_MANIFEST\|os.environ" install/uninstall.sh` | **REFUTED** — env var is used correctly |
| 24 `open()` calls missing encoding | `grep -c "encoding=" ... / grep -c "open(" ...` | **REFUTED** — 91/91 have encoding |
| CI unchanged | `head -40 .github/workflows/validate.yml` | **CONFIRMED** — no pytest step |
| Oracle fail-open | `sed -n '65,80p' enzymes/ttc_oracle.py` | **CONFIRMED** — returns APPROVED on exception |
| Test assertion bug | `sed -n '75,85p' tests/test_static_invariants.py` | **CONFIRMED** — `or` instead of `and` |
| Makefile vacuous pass | `sed -n '155,170p' Makefile` | **CONFIRMED** — "All tests passed." unconditional |

> Two claims from the Python Runtime Spores prong were independently refuted. The prong reported 24 `open()` calls missing `encoding=`, but mechanical census shows 91/91 are covered. The claimed "6 in ttc_verifier.py" was hallucinated — the file contains 1 `open()` call with encoding. The prong also claimed the path injection in `uninstall.sh` was unfixed, but `uninstall.sh:122-125` uses `SOMA_MANIFEST` env var correctly.

---

## Recommended Action Priority

| # | Action | Findings | Effort |
|:-:|:-------|:---------|:-------|
| 1 | Update CI to install pytest and run `make test`; add `windows-latest` matrix | TEMPEST-01, H06 | ~30 min |
| 2 | Fix Makefile `test` target: fail if pytest missing | H02 | 5 min |
| 3 | Fix test assertion: `or` → `and` at line 80; add exit code check | TEMPEST-02 | 5 min |
| 4 | Make TTC Oracle fail-closed: return `REJECTED` on exception | TEMPEST-03 | 5 min |
| 5 | Add integration test for backup restore (remove `--no-restore`) | TEMPEST-W01 | 30 min |
| 6 | Remove `__main__` self-test write from `ttc_verifier.py` | TEMPEST-W04 | 5 min |

---

## Stats

| Metric | Value |
|:-------|:------|
| Spores dispatched | 4 |
| Spores returned | 4 (100%) |
| Subagent claims refuted | 2 of ~120 (1.7% false positive rate) |
| Findings from genesis | 31 |
| Fixed | 22 (71%) |
| Partial | 6 (19%) |
| Unfixed | 2 (6.5%) |
| New defects | 2 (1 🔴, 1 ⚠️) |
| Wall-clock | ~5 min |
