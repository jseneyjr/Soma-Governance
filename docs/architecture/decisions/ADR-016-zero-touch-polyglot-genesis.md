# ADR-016: Zero-Touch Genesis Polyglot Provisioning & Rust Driver

## Status
**Accepted** (v1.2.0 — 2026-10-08)

## Context
Following ADR-015 (Normalized AST Driver Protocol), Soma introduced language-agnostic verification capabilities for non-Python source code (TypeScript, JavaScript, Go). However, adoption in real-world polyglot repositories faced significant friction:
1. **Manual Provisioning Barrier**: Developers onboarding polyglot repositories had to manually create or edit `.soma/slots.yaml` with language driver slots (`ast_driver_ts`, `ast_driver_go`) and copy template drivers.
2. **Missing Rust Support**: Rust source files (`.rs`) lacked an AST driver recipe, leaving Rust definitions, imports, calls, and mutation points unverifiable by Layer 1.
3. **CI/Release Verification Drift**: On clean release tags or merge commits without PR base branches, Layer 1 deterministic verification suffered fallback disconnects when `HEAD~1` was queried without passing the resolved diff base into `runner.py::_get_modified_lines`.

## Decision
1. **Zero-Touch Polyglot Detection & Provisioning (`soma_core.ast.detect`)**:
   - `detect_project_languages(workspace_root)`: Fast-scans the repository for primary programming languages (Python, TypeScript, JavaScript, Go, Rust) via manifest inspection (`package.json`, `go.mod`, `Cargo.toml`) and directory file extension sampling with standard ignores (`target/`, `node_modules/`, `.git/`, `dist/`, `build/`).
   - `resolve_recommended_drivers(detected_languages)`: Maps detected non-Python languages to recommended driver templates and slot commands.
   - `provision_ast_driver_slots(workspace_root, detected_languages)`: Automatically provisions `.soma/slots.yaml` and copies driver templates into `.soma/drivers/` (or repository-appropriate locations) without requiring manual developer configuration.
2. **First-Class Rust AST Driver (`install/drivers/rust_ast.py`)**:
   - A pure Python standard library driver (`rust_ast.py`) parsing Rust files into Normalized AST JSON.
   - Extracts:
     - Function, struct, enum, trait, and impl definitions with `pub` visibility.
     - `use` import declarations.
     - Function/method invocation call sites and macro invocations (`println!`, etc.).
     - Binary and comparison operator mutation points (`+` ↔ `-`, `*` ↔ `/`, `==` ↔ `!=`, `<` ↔ `>`, etc.).
3. **Genesis & Init Integration (`soma init`, `soma genesis`)**:
   - Both commands automatically run polyglot language detection and provision driver slots during project setup.
4. **Self-Healing Diagnostics (`soma doctor --fix`)**:
   - `soma doctor` reports unconfigured AST drivers for detected repository languages.
   - Passing `--fix` automatically provisions missing `.soma/slots.yaml` slots and driver files.
5. **Deterministic Verification Diff-Base Synchronization (`runner.py`, `verify.py`)**:
   - `verify.py::resolve_target_files` records the matching diff reference (`_diff_base`) and passes it into `runner.run_layer1(..., diff_base=ref)`.
   - `runner.py::_get_modified_lines` accepts `diff_base` and falls back to `HEAD~1...HEAD` and `HEAD~1`, ensuring consistent modified-line scoping on clean post-merge pushes, release tags, and PRs alike.

## Consequences

### Positive
- **True Zero-Touch Onboarding**: `soma init` and `soma genesis` configure complete polyglot AST verification out of the box with zero manual yaml authoring.
- **Pure Stdlib Runtime Maintained**: The Rust AST driver is written entirely in Python stdlib (`dependencies = []`), adhering strictly to Soma's SOMA-C02 zero-dependency runtime standard.
- **Robust CI & Release Publishing**: Layer 1 verification reliably resolves modified lines on release workflows and post-merge `main` pushes without false-positive whole-file regressions.
- **Self-Healing Workspaces**: `soma doctor --fix` remediates unconfigured driver slots seamlessly.

### Negative / Trade-offs
- **Rust Driver Heuristics**: The standard-library Rust driver relies on token-level scanning rather than full compiler-grade macro expansion (e.g., `rustc -Z ast-json`), prioritizing zero external dependencies and fast (<10ms) execution over deep macro expansion.

## Verification & Compliance
- **Detection & Provisioning Tests**: `tests/unit/core/test_polyglot_detect.py` (7 tests).
- **Rust AST Driver Tests**: `tests/unit/core/test_rust_ast_driver.py` (2 tests).
- **CLI Polyglot Integration Tests**:
  - `tests/unit/cli/test_init_polyglot.py` (2 tests).
  - `tests/unit/cli/test_genesis_polyglot.py` (2 tests).
  - `tests/unit/cli/test_doctor_polyglot.py` (3 tests).
- **Layer 1 Diff-Base & Fallback Tests**: `tests/unit/verification/test_layer1.py`.
