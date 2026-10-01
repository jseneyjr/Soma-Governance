# Contributing to Soma

Thank you for your interest in contributing!

## How to Contribute

### Reporting Issues
- Open a GitHub issue with a clear description
- Include your platform (gemini/kiro/copilot) and OS
- Include `make doctor` output if relevant

### Submitting Changes
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-change`
3. Make your changes
4. Run `make validate` to verify
5. Submit a pull request

### Contributing Cells
If your Genesis scan produced useful cells, you can contribute them:
1. Run `python3 enzymes/cell_fitness.py` to verify fitness > 0.7
2. Submit the cell file via PR to `.soma/cells/`
3. Include the cell's hypothesis and fitness data

### Contributing Rules
New global rules must:
- Trace back to observed failure patterns (Design Principle §1)
- Include a falsifiable hypothesis (Design Principle §6)
- Be measured by `enzymes/token_census.py` for token impact
- Pass `make validate`

## Contributor License Agreement

By submitting a pull request, you agree that your contributions are licensed under the same Apache License 2.0 that covers this project, and you certify that you have the right to grant this license.

You retain copyright to your contributions. The project maintainer (Nicholas Seney) retains the right to relicense contributions as part of the overall project.

## Code of Conduct

Be respectful, constructive, and evidence-driven — the same principles that govern the AI should govern the humans.

## Privacy Invariant

All contributions must respect the Privacy Invariant:
- ✅ Aggregate counts, booleans, sanitized strings
- ❌ Never: file paths, usernames, hostnames, project names, code content

See the [NOTICE](../NOTICE) file for the full privacy statement.
