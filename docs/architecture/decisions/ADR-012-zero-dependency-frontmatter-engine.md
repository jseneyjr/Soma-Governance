# ADR-012: Zero-Dependency Pure-Stdlib Frontmatter Engine

## Status
**Accepted** (v0.96.1 — 2026-10-06)

## Context
Soma's primary architectural value proposition is an adaptive, resilient governance layer for AI coding assistants. Because Soma is installed into developer workspaces, virtual environments, CI/CD pipelines, and agent sandbox containers, its runtime dependency footprint directly affects its reliability and security.

Prior to v0.96.1, `pyyaml>=6.0` was the single required package in `pyproject.toml` (`dependencies = ["pyyaml>=6.0"]`). While PyYAML is ubiquitous, requiring it introduced several failure modes:
1. **Bootstrap & Sandbox Brittleness**: In minimal sandbox containers, bare Python environments, or systems where pre-commit hooks run before `pip install`, any bare import of `yaml` caused immediate tool failure (surfaced historically in SOMA-C01, where MCP servers failed to start on bare interpreters).
2. **Maintenance Overhead**: Contradictory guidance between oracle rules (`optional-import-guard.md`) and package manifests led agents to introduce 118 lines of fragile fallback guards across 28 files during earlier releases.
3. **Supply-Chain Attack Surface**: Even single dependencies add supply-chain risk and potential C-extension build failures on esoteric architectures or locked-down enterprise runners.

All 102 markdown cells across `.soma/cells/`, `genome/`, `templates/`, and `organs/` utilize YAML frontmatter for metadata (e.g., `id`, `type`, `hypothesis`, `prediction`, `target_paths`, `fitness`, `lineage`). However, these files use a structured, predictable subset of YAML rather than complex YAML features like arbitrary Python tags, cyclic references, or custom type constructors.

## Decision
1. **100% Zero-Dependency Runtime**: Completely eliminate `pyyaml` from runtime `pyproject.toml` (`dependencies = []`). Move PyYAML to `[project.optional-dependencies] dev` solely for testing GitHub Actions workflows.
2. **Pure Standard Library Frontmatter Engine**: Upgrade `soma_core/frontmatter.py` to a full-featured, pure Python standard library YAML subset parser (`parse_frontmatter`, `parse_yaml_subset`, `parse_cell_frontmatter`) and serializer (`dump_frontmatter`).
3. **Syntax Coverage**: Implement native support in `soma_core/frontmatter.py` for:
   - Nested block mappings and block sequences (`- item` and same-indent `key:\n- item`).
   - Sequences of mappings (`- key: val`).
   - Multiline wrapped plain scalars with automatic line-continuation joining.
   - Literal (`|`) and folded (`>`) block scalars with chomping indicators (`-`, `+`, clip).
   - Double-quoted and single-quoted multiline strings with unicode (`\uXXXX`) and escape handling (`\ `, `\\\n`, `\"`).
   - Flow-style scalar types (integers, floats, booleans, nulls, ISO-8601 timestamps).
4. **Repository-Wide SOMA-C02 Invariant**: Elevate the MCP-only `SOMA-C01` invariant to repo-wide `SOMA-C02` in `tests/test_static_invariants.py`, statically guaranteeing zero third-party runtime package imports across `soma_cli/`, `soma_core/`, `soma_mcp/`, `soma_sdk/`, and `enzymes/`.

## Consequences

### Positive
- **Instant Portability**: Soma can now be imported and executed anywhere a Python ≥ 3.9 interpreter exists, with zero external wheels to download or build.
- **Sub-Millisecond Cold Starts**: MCP server startup and CLI execution avoid third-party C-extension dynamic linking and module discovery overhead.
- **100% Behavioral Parity**: All 102 frontmatter-bearing markdown files in the repository parse identically to PyYAML's parsed dictionary output (verified by roundtrip parity tests).
- **Reduced Attack Surface**: Zero supply-chain dependencies at runtime eliminates vulnerabilities in external parsers.

### Negative / Trade-offs
- **Subset Scope**: `soma_core.frontmatter` is intentionally an application-tailored subset, not a full YAML 1.2 specification engine. It does not support complex YAML anchors (`&`, `*`), custom tags (`!tag`), or merge keys (`<<`).
- **Engine Maintenance**: Any future syntax additions required by new cell types must be implemented and tested within `soma_core.frontmatter` and covered by `tests/test_frontmatter_engine.py`.

## Verification & Compliance
- **Unit Testing**: 18 specialized behavioral tests in `tests/test_frontmatter_engine.py` validate all supported YAML constructs against edge cases (chomping, unicode escapes, wrapped plain scalars, nested sequences).
- **Regression Suite**: All 2,522 tests across 140+ test files pass cleanly with zero failures.
- **Runtime Import Audit**: `python -c "import sys; sys.modules['yaml'] = None; ..."` verifies that all runtime CLI, MCP, SDK, and core modules import and operate successfully with PyYAML completely blocked from `sys.modules`.
