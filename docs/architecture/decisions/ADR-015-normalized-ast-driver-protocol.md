# ADR-015: Language-Agnostic AST Analysis via Normalized AST Drivers (NAD)

## Status
**Accepted** (v1.1.0 — 2026-10-08)

## Context
Soma's Layer 1 verification subsystem enforces deterministic, evidence-based code quality checks before any AI-generated change can be arbitrated or committed. Among these tools, the Call Graph Completeness Checker (`call_graph.py`) and Mutation Tester (`mutation_tester.py`) rely fundamentally on Abstract Syntax Tree (AST) analysis to:
1. Extract function, method, class, and export definitions.
2. Resolve intra-module and inter-module call sites without false-positive regex collisions.
3. Identify syntactically valid operator and comparison mutation candidates.

Historically, these checkers were implemented directly against Python's standard library `ast` module (`ast.parse`, `ast.NodeVisitor`). While effective for pure Python projects, this created severe limitations for polyglot codebases:
1. **Language Inequity**: Non-Python source files (TypeScript, JavaScript, Go, Rust) in polyglot repositories were either silently skipped or blocked from Layer 1 reachability and mutation verification.
2. **Repository Bloat Trap**: Naively bundling third-party multi-language parsers (such as Tree-Sitter grammars, Babel, or compiled C/WASM binaries) would bloat the distribution repository by dozens of megabytes, add native platform compilation dependencies, and directly violate Soma's strict SOMA-C02 zero-dependency runtime guarantee (`dependencies = []`).
3. **Sandbox & Architecture Portability**: Binary distribution or heavy language runtime bundling would break execution on minimal containers, BSD/Solaris, ARM, or locked-down developer environments.

## Decision
1. **The Normalized AST Driver (NAD) Protocol**: Establish a language-agnostic Intermediate Representation (`NormalizedAST`) and driver contract. The schema decouples AST consumers (call graph reachability, mutation testing) from language-specific AST producers.
2. **Standard Intermediate Representation Schema (`soma_core.ast.schema`)**:
   - `DefinitionNode`: Canonical function, method, class, and type definitions with export status.
   - `CallSiteNode`: Explicit invocation targets, source lines/columns, and caller scope.
   - `ImportNode`: Module specifiers and imported symbols.
   - `MutationPoint`: Syntactically valid mutation candidates with operator swaps, byte offsets, and line/column coordinates.
3. **Dual Execution Paths**:
   - **Native Python Fast-Path (In-Process)**: Python source files continue to be parsed directly in-process via stdlib `ast.parse` in `soma_core.ast.drivers.python`, maintaining sub-millisecond execution with zero process overhead.
   - **Host-Native Process Drivers (External)**: Non-Python source files execute lightweight host-native CLI drivers resolved via `.soma/slots.yaml` (`ast_driver_{ext}` or `ast_driver`) or registered in `ASTDriverRegistry`.
4. **Strict Confinement and Timeouts**:
   - Drivers execute via vector arguments (`shell=False`) with a non-blocking, enforced 3.0-second timeout (`ASTDriverTimeoutError`).
   - Workspace confinement verifies that source files cannot traverse outside the active workspace directory.
5. **Zero Bundled Grammars / Zero Runtime Dependencies**:
   - The core distribution bundles zero external grammar packages or compiled binaries.
   - Reference driver recipes (`install/drivers/ts_ast.js`, `install/drivers/go_ast.go`) use host tools (Node.js, Go stdlib `go/parser`) and standard system utilities.
6. **Diagnostic Transparency**:
   - `soma doctor` inspects configured AST drivers, verifying executable resolution or falling back gracefully to native Python analysis.

## Consequences

### Positive
- **Polyglot Verification**: Layer 1 Call Graph reachability and Mutation Testing now seamlessly analyze TypeScript, JavaScript, Go, and any language with a configured driver.
- **Zero Bloat**: Repository and package wheel size remain minimal; pure Python standard library runtime is strictly preserved (`dependencies = []`).
- **Decoupled Evolution**: Supporting a new language (e.g., Rust, Java, C#) requires only a small CLI recipe emitting JSON, with zero changes to Soma's core verification logic.
- **Fast and Resilient**: Python files experience zero performance regression; polyglot files execute in <150ms per file, bounded by strict 3.0s timeouts.

### Negative / Trade-offs
- **Host Runtime Dependency for Polyglot Files**: Analyzing non-Python files requires the corresponding language runtime (e.g., `node` for TypeScript, `go` for Go) to be installed on the host or configured in `.soma/slots.yaml`. If missing, Soma fails closed or skips gracefully according to slot configuration.
- **Inter-Process Serialization**: Parsing polyglot files involves JSON serialization and subprocess launch, adding ~50–150ms overhead per polyglot file analyzed compared to Python's in-process parser.

## Verification & Compliance
- **Schema & Roundtrip Tests**: `tests/unit/core/test_normalized_ast_schema.py` validates serialization, deserialization, and lookup semantics.
- **Driver Runner Tests**: `tests/unit/core/test_ast_driver_runner.py` verifies timeout enforcement, error propagation, and workspace confinement.
- **Polyglot Call Graph Tests**: `tests/unit/verification/test_polyglot_call_graph.py` validates reachability, orphan detection, and comment/string filtering across polyglot files.
- **Polyglot Recipes & Mutation Tests**: `tests/unit/core/test_polyglot_recipes.py` verifies Node.js/TypeScript driver recipes, Go recipe syntax, and byte-offset mutation application.
