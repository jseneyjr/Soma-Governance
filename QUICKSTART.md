# Soma Quickstart Guide

## What Soma Does

Soma is a governance framework for AI coding agents that makes them trustworthy, grounded, and cost-effective. It actively enforces rules against hallucinations, unverified claims, and wasteful rework loops during coding sessions. By validating agent actions against real evidence, Soma keeps development safe, predictable, and verifiable.

## Prerequisites

- Python 3.9+
- git

## Installation

Choose one of three install options:

```bash
# Option 1: PyPI
pip install soma-governance

# Option 2: Clone and editable install
git clone https://github.com/nseney1/Soma-Governance.git && cd Soma-Governance
pip install -e .

# Option 3: Clone and make install
git clone https://github.com/nseney1/Soma-Governance.git && cd Soma-Governance
make install
```

> **PEP 668 (externally managed Python)?** Add `--user` or `--break-system-packages` to pip commands.

## First Run

```bash
soma init --yes        # Detects your platform, installs 5 starter rules
soma status            # See what's active
# ... do a coding session ...
soma report            # Session report card
```

## CLI Commands

```bash
# Governance lifecycle
soma init              # Set up governance (auto-detects platform)
soma status            # Show active rules and fitness stats
soma report            # Session report card
soma doctor            # Verify installation integrity

# Quality gates
soma checkpoint        # Deterministic quality checks (--pre-commit for hooks)
soma verify            # Layer 1 verification on changed files

# Evidence pipeline
soma sync              # Reconcile JSONL evidence with cell frontmatter
soma sync --dry-run    # Preview without writing

# Cell lifecycle
soma genesis           # Scan architecture and generate cell candidates
soma genesis --dry-run # Preview candidates without writing
soma oracle --json     # Cell health classification
soma promote --dry-run # See promotion candidates
soma demote --dry-run  # See demotion candidates
```

## What the 5 Starter Rules Do

- `providence`: Grounds claims in evidence, prevents hallucination
- `destructive-ops`: Requires dry-runs before dangerous operations
- `testing`: Enforces behavioral tests, sad paths, minimal mocks
- `cost-optimization`: Minimizes wasted tokens and compute
- `git-workflow`: Enforces consistent commit practices

## Supported Platforms

- Gemini / Antigravity (auto-detected)
- Claude Code (auto-detected)
- Cursor (auto-detected)
- Copilot (auto-detected)
- Kiro (auto-detected)
- Any MCP-compatible agent

## Next Steps

For advanced configuration, rule customization, and automated verification details, see the full [README.md](README.md).
