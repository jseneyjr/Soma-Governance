# Prism AI Steering: Adaptive Governance Framework

**Author**: Nicholas Seney
**Date**: September 2026
**License**: Apache 2.0

---

## Abstract

We present Prism AI Steering, an adaptive governance framework for AI coding assistants that generates, measures, and prunes its own rules via fitness-based selection. While developed for AI-assisted coding, its core mechanism—hypothesis-driven fitness with selection pressure—is domain-agnostic. It addresses a fundamental challenge: ungoverned AI agents exhibit waste rates exceeding 50% due to cross-session, systemic failure modes.

Rather than prescribing static best practices, Prism AI extracts rules from empirical failure patterns. Analysis of 83 sessions (12,000+ execution steps) showed fully-governed sessions reduce waste from ~56% to 18.8% (best-case 1.1%), eliminating rework loops and hallucinations. 

The framework introduces three contributions:

1. **Structured review architecture**: Five severity modes and six review prongs providing graduated, risk-proportional governance with adversarial falsification to eliminate false-positives.

2. **Cytogenesis**: A self-generating mechanism that scans codebases to produce repo-specific governance extensions ("cells"), including personas (Chloroplasts), persisted traps (Vacuoles), and boundaries (Cell Walls). Each cell carries a falsifiable hypothesis and automatic expiry conditions.

3. **Evolutionary dynamics**: Fitness-based selection infrastructure. Generated extensions are scored on precision (`true_positives / total_triggers × impact_weight`), pruned when ineffective, and promoted to global rules when universally effective.

The system's idle overhead is 4,380 tokens per turn (~3.4% of a 128K context window). All telemetry enforces a strict privacy invariant: aggregate counts and scores only.

### Cross-Domain Applicability

Preliminary analysis suggests this cell architecture transfers beyond code governance. Validated in cross-domain analysis with RL training pipelines, game strategy lessons were modeled as falsifiable Vacuole cells with fitness tracking. This demonstrates the evolutionary governance mechanism transfers to any domain where AI systems accumulate knowledge requiring empirical validation.

### Limitations and Future Work

Evaluation baseline differences prevent causal claims; waste classification lacked multi-rater reliability; the full evolutionary cycle awaits end-to-end validation against human assessment. The fitness function optimizes for precision but ignores recall (false negatives). Four registered experiments address these gaps.

**Keywords**: AI governance, evolutionary computation, software engineering, AI-assisted development, prompt engineering
