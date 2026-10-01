# Soma Release Workflow (Gitflow)

> Codified release procedure for phased governance releases.
> Each phase follows this exact branch → PR → merge → tag → back-merge cycle.

## Release Procedure

```text
develop ──→ release/v0.XX ──→ PR to main ──→ tag v0.XX.0 ──→ back-merge to develop
```

### Steps (execute in order)

1. **Branch from develop**: `git checkout develop && git checkout -b release/v0.XX`
2. **Commit changes**: Use conventional commits. Group logically (bug fix, docs, infrastructure).
3. **Version bump checklist** — update ALL version sources:
   - `pyproject.toml` → `version = "0.XX.0"`
   - `VERSION` → `0.XX.0`
   - `README.md` → version badge (if present)
   - Run `pytest tests/test_static_invariants.py::test_version_is_single_sourced` to verify sync
4. **Push branch**: `git push -u origin release/v0.XX`
5. **Create PR**: `gh pr create --base main --head release/v0.XX --title "release(v0.XX): <summary>"`
6. **Wait for CI**: All matrix jobs must pass before merge
7. **⛔ HUMAN REVIEW GATE**: Stop here. The maintainer reviews the PR and merges via GitHub UI. Agents must NOT merge to main directly — this is the owner's checkpoint.
8. **Tag release** (after merge): `git checkout main && git pull && git tag -a v0.XX.0 -m "<message>" && git push origin v0.XX.0`
9. **Back-merge to develop**: `git checkout develop && git merge main -m "sync: merge main back to develop after v0.XX" && git push origin develop`
10. **Create GitHub Release**: `gh release create v0.XX.0 --title "v0.XX.0 — <Theme>" --notes "<release notes>"`
11. **Cleanup**: Delete release branch `git push origin --delete release/v0.XX`

## Phase → Version Mapping

| Phase | Version | Theme |
|:------|:--------|:------|
| Phase 1 | v0.73 ✅ | Stop the Bleeding — README strip, hook fix, claim registry |
| Phase 2 | v0.74 ✅ | Foundation — canonical parser, scoring unification, error handling |
| Phase 3 | v0.75 ✅ | Credit Where Due — credit assignment, mutation testing, crossover |
| Phase 4 | v0.80 ✅ | Consensus — quorum sensing, gate enforcement DSL, doc cleanup |

## Pre-Release Checklist

Before creating a release PR, verify:
- [ ] All phase verification gate items pass
- [ ] `python3 enzymes/verify_readme_claims.py` passes
- [ ] `pytest tests/` passes with 0 failures
- [ ] Version synced across `pyproject.toml`, `VERSION`, and README badge

### Documentation Hygiene (mandatory per release)

Audit every doc file for staleness. For each file, determine: **UPDATE**, **DELETE**, or **OK**.

- [ ] `README.md` — version references, feature claims match unlocked claims only
- [ ] `docs/research/abstract.md` — figures and architecture match current implementation
- [ ] `docs/project/CHANGELOG.md` — has entry for this release with summary of changes
- [ ] `docs/project/ROADMAP.md` — reflects current phase status (completed phases marked, next phase current)
- [ ] `docs/architecture/scripts.md` — script descriptions match current enzyme signatures and behavior
- [ ] `docs/project/METRICS.md` — metrics are honest, no unverified quantitative claims
- [ ] `docs/architecture/mechanism_design.md` — architecture matches current code (e.g., scoring method, parser)
- [ ] `docs/project/CLAIM_REGISTRY.json` — all unlocked claims have passing tests, no stale locks
- [ ] `docs/project/CONTRIBUTING.md` — setup instructions work, dependencies current
- [ ] `docs/project/RELEASE_WORKFLOW.md` — lessons learned section updated
- [ ] `docs/project/RELEASE_WORKFLOW.md` — consistent with release procedures
- [ ] `docs/archive/` — stale archives reviewed; delete if no longer referenced

**Rule**: If a doc references a version older than `current - 2` (e.g., v0.30 when shipping v0.74), it must be updated or archived.

### Post-Release Cleanup (after back-merge)

- [ ] Delete merged release branch: `git push origin --delete release/v0.XX`
- [ ] Delete any stale feature branches merged into develop
- [ ] Verify `docs/project/CHANGELOG.md` has the release entry
- [ ] Verify GitHub Release notes match PR body

## Lessons Learned

### v0.73
- **VERSION file missed**: `pyproject.toml` was bumped but `VERSION` was not. The `test_version_is_single_sourced` invariant caught it in CI. Always use the version bump checklist above.
- **Cherry-pick after merge**: If a fix is committed to the release branch after the PR is merged, cherry-pick to main rather than creating a new PR.

### v0.74
- **Property test flaky**: `test_interval_narrows_with_more_data` used additive extra (changes proportion), not multiplicative scale (preserves proportion). Hypothesis found the counterexample `tp=1, fp=8, extra=1`. Fix: multiply both by scale factor.
- **Documentation not audited**: No systematic doc review was part of the workflow. Added Documentation Hygiene checklist above.

### v0.75
- **VERSION file again**: CI broke because `VERSION` wasn't bumped alongside `pyproject.toml`. The invariant test caught it, confirming the version bump checklist is essential.
- **Stale CHANGELOG URL**: `pyproject.toml` had a pre-restructure URL to `docs/CHANGELOG.md` (moved to `docs/project/CHANGELOG.md`).

### v0.80
- **Agent merged directly to main**: Agent bypassed the PR review step and merged release branches directly into main via `git merge`. Added explicit **⛔ HUMAN REVIEW GATE** to step 7 to prevent this. Agents must stop at the PR and let the maintainer merge.
- **Doc fixer sandbox failures**: Subagent doc edits silently failed due to read-only sandbox. Only 3 of 9 files were written on first pass. Verified via `git diff --stat` before committing. Always spot-check subagent file writes.
