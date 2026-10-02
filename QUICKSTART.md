# Soma Quickstart Guide

## What Soma Does

Soma is a governance framework for AI coding agents. It installs governance rules, provides a CLI and MCP server, and records evidence for adaptive rule management.

## Installation

Choose the option that matches your environment.

### Option 1: Install the CLI from PyPI

**Requires:** Python 3.9+ and `pip`.

```bash
pip install soma-governance
```

### Option 2: Editable source install

**Requires:** Git, Python 3.9+, and `pip`.

```bash
git clone https://github.com/nseney1/Soma-Governance.git
cd Soma-Governance
pip install -e .
```

### Option 3: Install CLI and agent integration with Make

**Requires:** Git, Python 3.9+, `pip`, Bash, and GNU Make.

```bash
git clone https://github.com/nseney1/Soma-Governance.git
cd Soma-Governance
make install SOMA_PLATFORM=gemini
```

> **PEP 668 (externally managed Python)?** Use an isolated virtual environment. If that is not possible, `pip install --user soma-governance` may be appropriate for your system.

## First Run with `soma init`

`soma init` detects Gemini, Claude Code, Cursor, and Copilot markers. If detection is ambiguous, select one of those platforms explicitly.

```bash
soma init --platform gemini --yes
soma status
# ... do a coding session ...
soma report
```

Useful setup flags verified by `soma --help`:

```bash
soma init --dry-run
soma init --rules minimal --platform claude
soma init --rules standard --mcp --platform cursor --yes
soma init --rules full --platform copilot --force --yes
```

## Kiro and Generic MCP Installation

Kiro is supported by the Bash installer; it is not auto-detected by `soma init`.

```bash
bash install/install.sh kiro --dry-run
bash install/install.sh kiro
```

For any MCP-compatible agent, generate a project-local `.mcp.json` with the Bash installer:

```bash
bash install/install.sh mcp --dry-run
bash install/install.sh mcp
```

## CLI Commands

```bash
# Governance lifecycle
soma init --help        # Set up governance for a supported detected/selected platform
soma status             # Show active rules and fitness stats
soma report             # Session report card
soma doctor             # Verify installation integrity

# Quality gates
soma checkpoint         # Deterministic quality checks
soma checkpoint --pre-commit --strict
soma verify --layer1-only

# Evidence pipeline
soma sync               # Reconcile JSONL evidence with cell frontmatter
soma sync --dry-run --json

# Cell lifecycle
soma genesis --dry-run
soma oracle --json
soma promote --dry-run
soma demote --dry-run
```

## Make Targets

The repository Makefile provides `help`, `info`, `install`, `install-gemini`, `install-kiro`, `install-copilot`, `install-claude`, `install-mcp`, `install-windows`, `uninstall`, `doctor`, `validate`, `update`, `status`, and `test`. Run `make help` for descriptions.

## What the Standard Starter Rules Do

- `providence`: grounds claims in evidence and requires read-before-write.
- `destructive-ops`: requires safety gates for dangerous operations.
- `testing`: requires behavioral tests and meaningful failure coverage.
- `cost-optimization`: limits wasted tokens and compute without sacrificing correctness.
- `git-workflow`: defines safe, consistent Git practices.

## Next Steps

See [README.md](README.md) for MCP configuration, receipt usage, SDK examples, and architecture details.
