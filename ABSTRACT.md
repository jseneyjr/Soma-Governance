# Prism AI Steering: An Adaptive Governance Framework for AI Coding Assistants with Evolutionary Self-Optimization

**Author**: Nicholas Seney  
**Date**: September 2026  
**License**: Apache 2.0  
**Repository**: [github.com/nseney1/prism-ai-steering](https://github.com/nseney1/prism-ai-steering)

---

## Abstract

We present Prism AI Steering, an adaptive governance framework for AI coding assistants that generates, measures, and evolves its own rules through fitness-based natural selection. Developed iteratively across 14 phases of empirical refinement, the framework addresses a fundamental challenge in AI-assisted software development: ungoverned AI coding agents exhibit waste rates exceeding 50% of total execution steps, with failure modes that are systematic, cross-session, and invisible to the agent itself.

Rather than prescribing static rules from best practices, Prism AI Steering extracts governance rules from measured failure patterns in real development sessions. An analysis of 83 production sessions (66 pre-governance, 17 governed) comprising over 7,000 execution steps established that governed sessions achieve waste rates as low as 1.1%, compared to approximately 56% in ungoverned sessions — a reduction attributable to the elimination of rework loops, hallucination chains, and scope inversion patterns.

The framework introduces three novel contributions:

1. **A structured review architecture** with five severity modes (Breeze through Tempest) and six review prongs (Spores through Mulch), each with calibrated output budgets, providing graduated governance proportional to change risk.

2. **Cytogenesis** — a self-generating governance mechanism where the system scans unfamiliar codebases and produces repo-specific governance extensions ("cells") including domain-tuned review personas (Chloroplasts), persisted anti-pattern traps (Vacuoles), security boundaries (Cell Walls), and escalation overrides (Membranes). Each generated cell carries a falsifiable hypothesis, prediction criteria, and automatic expiry conditions.

3. **Evolutionary dynamics** — a fitness-based selection cycle where generated governance extensions are scored on their true-positive rate, adapted when mediocre, pruned when ineffective, and promoted from repo-local extensions to global rules when they demonstrate universal effectiveness across multiple codebases. This creates a closed loop where the governance system discovers, validates, and evolves its own rules without human authorship.

The system's idle overhead is measured at 4,380 tokens per turn using a calibrated tokenizer (ratio 1.35, validated against the Gemini count_tokens API), representing less than 3% of a typical context window. All measurement, metrics, and telemetry enforce a strict privacy invariant: the system collects aggregate counts and scores only — never file contents, paths, usernames, or project-specific data.

The framework is open source (Apache 2.0), cross-platform (bash and PowerShell), and designed for installation into existing AI assistant configurations. A self-referential validation ("dogfooding") demonstrates that the system's Genesis scanner, when applied to its own repository, generates governance cells that would have caught bugs discovered during its own development.

**Keywords**: AI governance, adaptive systems, evolutionary computation, software engineering, AI-assisted development, self-improving systems, fitness-based selection, prompt engineering

---

*For the full technical documentation, see [EVOLUTION.md](docs/EVOLUTION.md) (14-phase development history), [METRICS.md](docs/METRICS.md) (quantitative analysis), and [EXPERIMENTS.md](docs/EXPERIMENTS.md) (26 registered experiments, 15 empirical insights).*
