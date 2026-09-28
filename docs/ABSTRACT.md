# Prism AI Steering: An Adaptive Governance Framework for AI Coding Assistants with Evolutionary Self-Optimization

**Author**: Nicholas Seney  
**Date**: September 2026  
**License**: Apache 2.0  
**Repository**: [github.com/nseney1/prism-ai-steering](https://github.com/nseney1/prism-ai-steering)

---

## Abstract

We present Prism AI Steering, an adaptive governance framework for AI coding assistants that generates, measures, and prunes its own rules through fitness-based selection. Developed iteratively across 14 phases of empirical refinement, the framework addresses a fundamental challenge in AI-assisted software development: ungoverned AI coding agents exhibit waste rates — non-productive, hallucinatory, or reworked execution steps — exceeding 50% of total steps, with failure modes that are systematic, cross-session, and invisible to the agent itself.

Rather than prescribing static rules from best practices, Prism AI Steering extracts governance rules from measured failure patterns in real development sessions. An analysis of 83 sessions — 66 partially-governed baseline sessions (rules installed but skills absent due to an installer gap) and 17 fully-governed sessions — comprising over 12,000 annotated execution steps established that fully-governed sessions achieve an average waste rate of 18.8%, with best-case results as low as 1.1%, compared to approximately 56% in baseline sessions. This reduction is correlated with the elimination of rework loops, hallucination chains, and scope inversion patterns, though confounding variables (model differences, task complexity, temporal effects) have not been fully isolated in the current dataset.

The framework introduces three novel contributions:

1. **A structured review architecture** with five severity modes and six review prongs, each with calibrated output budgets, providing graduated governance proportional to change risk. The architecture incorporates adversarial falsification mechanisms — an adversarial testing prong validates proposed fixes before they ship, and a refutation gate structurally eliminates false-positive findings.

2. **Cytogenesis** — a self-generating governance mechanism where the system scans unfamiliar codebases and produces repo-specific governance extensions ("cells") including domain-tuned review personas (Chloroplasts), persisted anti-pattern traps (Vacuoles), security boundaries (Cell Walls), and escalation overrides (Membranes). Each generated cell carries a falsifiable hypothesis, prediction criteria, and automatic expiry conditions. The biological terminology is used as a generative design metaphor; the underlying mechanisms are repo-specific prompt personas, persisted anti-pattern vectors, and configurable escalation thresholds.

3. **Evolutionary dynamics** — fitness-based selection infrastructure where generated governance extensions are scored on their precision rate (`true_positives / total_triggers × impact_weight`), pruned when ineffective, and promoted from repo-local extensions to global rules when they demonstrate effectiveness across multiple codebases. The system currently implements automated generation, scoring, and pruning; the adaptation phase provides heuristic refinement suggestions but does not yet autonomously rewrite rule content. Human feedback is collected at session boundaries to update fitness scores, making this a human-in-the-loop evolutionary system rather than a fully autonomous one.

The system's idle overhead is 4,380 tokens per turn (~3.4% of a 128K context window), measured via a calibrated tokenizer validated against the Gemini API. All telemetry enforces a strict privacy invariant: aggregate counts and scores only, never file contents, paths, or user identities. The open-source framework is cross-platform (bash and PowerShell). A self-referential evaluation demonstrates that the system generates governance cells capable of catching bugs historically discovered during its own development.

### Limitations and Future Work

The current evaluation has several threats to validity: the baseline and governed datasets differ in model family, task distribution, and time period, preventing causal claims; waste classification was performed by a single annotator without multi-rater reliability metrics; and the full evolutionary cycle (generate → score → adapt → prune → promote) has not yet been demonstrated end-to-end with sufficient data to validate the fitness function's correlation with human assessment. The fitness function optimizes for precision but does not account for recall (false negatives — issues a cell should have caught but didn't). Four experiments (E23–E26) are registered to address these gaps.

**Keywords**: AI governance, adaptive systems, evolutionary computation, software engineering, AI-assisted development, fitness-based selection, prompt engineering

---

*For the full technical documentation, see [EVOLUTION.md](docs/EVOLUTION.md) (14-phase development history), [METRICS.md](docs/METRICS.md) (quantitative analysis), and [EXPERIMENTS.md](docs/EXPERIMENTS.md) (26 registered experiments, 15 empirical insights).*
