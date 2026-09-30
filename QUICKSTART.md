# Soma Quickstart Guide

## What Soma Does

Soma is a governance framework for AI coding agents that makes them trustworthy, grounded, and cost-effective. It actively enforces rules against hallucinations, unverified claims, and wasteful rework loops during coding sessions. By validating agent actions against real evidence, Soma keeps development safe, predictable, and verifiable.

## Prerequisites

- Python 3.9+
- git

## Installation

Choose one of three install options:

```bash
# Option 1: PyPI (coming soon)
pip install soma-governance

# Option 2: Clone and editable install
git clone https://github.com/nseney1/soma.git && cd soma
pip install -e .

# Option 3: Clone and make install
git clone https://github.com/nseney1/soma.git && cd soma
make install
```

## First Run

```bash
soma init --yes        # Detects your platform, installs 5 starter rules
soma status            # See what's active
# ... do a coding session ...
soma report            # Session report card
```

## What the 5 Starter Rules Do

- `providence`: Grounds claims in evidence, prevents hallucination
- `destructive-ops`: Requires dry-runs before dangerous operations
- `testing`: Enforces behavioral tests, sad paths, minimal mocks
- `cost-optimization`: Minimizes wasted tokens and compute
- `git-workflow`: Enforces consistent commit practices

## Supported Platforms

- Gemini (auto-detected)
- Claude (auto-detected)
- Cursor (auto-detected)
- Copilot (auto-detected)

## Next Steps

For advanced configuration, rule customization, and automated verification details, see the full [README.md](README.md).
