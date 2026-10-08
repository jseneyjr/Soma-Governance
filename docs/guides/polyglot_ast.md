# Polyglot AST Analysis Guide

Soma v1.1.0 introduces the **Normalized AST Driver (NAD) Protocol**, enabling deterministic Layer 1 verification (call graph reachability, orphan detection, and mutation testing) across polyglot codebases without adding third-party dependencies or bundling large grammar binaries into the core distribution.

---

## 1. How It Works

1. **Native Python Fast-Path (In-Process)**:
   All `.py` files are parsed in-process using Python's standard library `ast` module. This fast-path has zero overhead, executes in sub-millisecond time, and requires no external tooling.

2. **Host-Native Process Drivers (External)**:
   When Soma encounters non-Python files (e.g. `.ts`, `.js`, `.go`, `.rs`), it delegates AST extraction to a lightweight external driver configured in `.soma/slots.yaml`. The driver parses the source file and emits standard JSON conforming to the `NormalizedAST` schema to `stdout`.

3. **Strict Confinement & Timeouts**:
   All external drivers execute with `shell=False`, argument confinement to prevent path traversal outside the workspace, and an enforced strict 3.0-second timeout.

---

## 2. Configuration via `.soma/slots.yaml`

To enable polyglot AST verification in your workspace, configure drivers in `.soma/slots.yaml` using extension-specific keys (`ast_driver_{ext}`) or a global fallback key (`ast_driver`):

```yaml
# .soma/slots.yaml

# Extension-specific drivers
ast_driver_ts: "node install/drivers/ts_ast.js"
ast_driver_js: "node install/drivers/ts_ast.js"
ast_driver_go: "go run install/drivers/go_ast.go"

# Optional global fallback driver
# ast_driver: "my-universal-ast-cli"
```

If no driver is configured for a file extension, Soma gracefully bypasses external AST checks for that file without raising false-positive pipeline errors.

---

## 3. The Normalized AST JSON Contract (v1.0)

External drivers must accept the target file path as an argument:
```bash
<driver_command> <path/to/source/file>
```
and output a valid JSON object to `stdout` matching the following schema:

```json
{
  "version": "1.0",
  "file_path": "src/service.ts",
  "language": "typescript",
  "definitions": [
    {
      "name": "calculateTax",
      "kind": "function",
      "line": 10,
      "column": 0,
      "end_line": 25,
      "is_exported": true,
      "is_method": false,
      "class_name": null,
      "docstring": null
    }
  ],
  "call_sites": [
    {
      "target": "helperFunction",
      "line": 15,
      "column": 4,
      "caller_scope": "calculateTax"
    }
  ],
  "imports": [
    {
      "source": "./utils",
      "imported_symbols": ["helperFunction"],
      "line": 1,
      "is_type_only": false
    }
  ],
  "mutation_points": [
    {
      "line": 12,
      "col": 11,
      "original_op": "===",
      "replacement_op": "!==",
      "mutation_type": "cmpop",
      "function_scope": "calculateTax",
      "byte_offset": 142
    }
  ]
}
```

### Schema Nodes

| Node | Field | Type | Description |
|:---|:---|:---|:---|
| **DefinitionNode** | `name` | string | Identifier of the function, method, class, or type |
| | `kind` | string | `"function"`, `"method"`, `"class"`, `"type"`, or `"interface"` |
| | `line` | integer | 1-indexed starting line number |
| | `is_exported` | boolean | `true` if public/exported outside the module; `false` otherwise |
| | `is_method` | boolean | `true` if defined within a class/struct |
| | `class_name` | string / null | Enclosing class or receiver type name |
| **CallSiteNode** | `target` | string | Target function/method name being invoked |
| | `line` | integer | 1-indexed call site line number |
| | `caller_scope` | string / null | Enclosing function/method name, if known |
| **ImportNode** | `source` | string | Module specifier (e.g. `./utils`, `fmt`) |
| | `imported_symbols` | array[string] | Imported function/symbol names |
| | `line` | integer | 1-indexed import statement line number |
| **MutationPoint** | `line` | integer | 1-indexed line of candidate operator |
| | `col` | integer | 0-indexed column of candidate operator |
| | `original_op` | string | Operator to mutate (e.g. `===`, `&&`, `+`) |
| | `replacement_op` | string | Mutated operator replacement (e.g. `!==`, `\|\|`, `-`) |
| | `mutation_type` | string | `"cmpop"`, `"boolop"`, or `"binop"` |
| | `byte_offset` | integer / null | Exact 0-indexed byte offset in file (enables fast replacement) |

---

## 4. Built-in Reference Recipes

Soma provides zero-dependency reference recipe scripts in the `install/drivers/` directory:

### Node.js / TypeScript Driver (`install/drivers/ts_ast.js`)
- Requires Node.js (≥ 18) installed on the host.
- Automatically leverages the official `typescript` compiler API if installed in the workspace's `node_modules` or globally.
- Automatically falls back to a deterministic, zero-dependency built-in regex lexer when running in bare environments without `node_modules`.

### Go Driver (`install/drivers/go_ast.go`)
- Requires Go (≥ 1.18) installed on the host.
- Uses Go's standard library packages (`go/parser`, `go/token`, `go/ast`, `encoding/json`).
- Has zero external third-party dependencies.

---

## 5. Diagnostics & Verification

Run `soma doctor` to verify that your configured AST drivers are resolvable on your system:

```bash
soma doctor
```

Output:
```text
  ✅ AST driver (.ts): node resolvable (/usr/bin/node)
  ✅ AST driver (.go): go resolvable (/usr/bin/go)
```

Run Layer 1 verification across your repository:
```bash
soma verify --layer 1
```
