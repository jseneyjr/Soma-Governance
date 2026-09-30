---
id: optional-import-guard
domain: correctness
name: Optional Import Guard
description: Enforces try/except guards on optional dependencies to prevent CI and runtime crashes.
trigger: model_decision
---

# Optional Import Guard

**Role**: Prevents bare imports of optional packages that crash the module when the dependency isn't installed.

## Rule

Any `import` of a package not in the Python standard library and not listed as a **required** dependency in `pyproject.toml` or `requirements.txt` MUST be wrapped in a `try/except ImportError` guard:

```python
try:
    import yaml
except ImportError:
    yaml = None
```

## Scope

This applies to ALL files in `enzymes/`, `soma_mcp/`, `immune_system/`, and `install/`.

## Required Dependencies (bare import OK)

These are listed in `pyproject.toml [project.dependencies]` — bare `import` is correct:

| Package | Used For |
|:--------|:---------|
| `yaml` (pyyaml) | YAML frontmatter parsing |

## Known Optional Dependencies

| Package | Used For | Fallback |
|:--------|:---------|:---------|
| `anthropic` | Anthropic API provider | Skip provider |
| `google.generativeai` | Gemini API provider | Skip provider |
| `openai` | OpenAI API provider | Skip provider |

## Why This Matters

Unguarded imports of truly optional packages crash the entire test suite when
the dependency isn't installed. The blast radius is recursive: `test_foo.py`
imports `module_a.py` which imports `module_b.py` which has `import optional_lib`
→ ALL tests touching `module_a` fail with `ModuleNotFoundError`.

> **Historical note (2026-09-30):** `pyyaml` was previously listed in this
> table as optional, which caused agents to add `try/except ImportError` guards
> across 28 files. This contradicted `pyproject.toml` which declared pyyaml as
> a required dependency. The guards introduced 118 lines of fragile fallback
> code that produced bugs in 3 of 4 audit rounds. The table was the root cause.

## Enforcement

When reviewing or writing code that adds an `import` statement:

1. Check if the package is in the standard library → if yes, bare import is fine
2. Check if it's a required dependency in `pyproject.toml` → if yes, bare import is fine
3. Otherwise → MUST use `try/except ImportError` guard

## Violation Detection

The naive `grep '^import yaml$'` misses compound imports (`import os, yaml`)
and indented imports inside functions. Use AST-based detection:

```bash
# AST-based scan for unguarded yaml imports
python3 -c "
import ast, glob
for f in glob.glob('enzymes/**/*.py', recursive=True) + \
         glob.glob('soma_mcp/**/*.py', recursive=True) + \
         glob.glob('soma_sdk/**/*.py', recursive=True):
    if '__pycache__' in f: continue
    tree = ast.parse(open(f).read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name == 'yaml' for a in node.names):
                in_try = any(isinstance(p, ast.Try) and
                    any(c is node for c in ast.walk(p))
                    for p in ast.walk(tree))
                if not in_try:
                    print(f'{f}:{node.lineno}')
"
```

Also check shell scripts with embedded Python:
```bash
grep -n 'import.*yaml' enzymes/*.sh | grep -v 'try:'
```

Any match is a violation.
