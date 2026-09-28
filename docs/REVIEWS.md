# Peer Review Record — ABSTRACT.md

> This document records the peer review process for the Prism AI Steering research abstract.
> Two rounds of review were conducted with 5 independent reviewers across 4 specializations.

---

## Review Panel

| Reviewer | Specialization | Round | Recommendation | Confidence |
|:---------|:---------------|:-----:|:--------------:|:----------:|
| R1 | Claims Verification & Accuracy | 1 | Revise (Minor) | High |
| R2 | Empirical Software Engineering | 1 | Revise (Major) | 4/5 |
| R3 | Evolutionary Computation & Adaptive Systems | 1 | Revise | 4/5 |
| R4 | AI Safety & Alignment | 2 | **Accept** | 5/5 |
| R5 | Senior Research Editor | 2 | Minor Revision | 5/5 |

---

## Round 1: Initial Submission

### Reviewer 1 — Claims Verification & Accuracy

**Approach**: Verified every quantitative claim against the codebase, scripts, and documentation.

**PASS** (Claims that check out):
- "comprising over 7,000 execution steps" — supported and conservative; METRICS.md shows 7,015 steps in governed sessions alone
- "waste rates as low as 1.1%, compared to approximately 56%" — matches live A/B validation in METRICS.md
- "14 phases of empirical refinement" — fully supported by EVOLUTION.md
- "4,380 tokens per turn using a calibrated tokenizer (ratio 1.35)" — confirmed via `token_census.py`
- Dogfooding claim — accurately scoped; states cells *"would have caught"* bugs, not that they caught them live
- File counts (11 rules, 15 skills) — verified against filesystem

**FLAG** (Claims needing correction):
- "66 pre-governance" → should be "66 partially-governed" (they had rules but missing skills due to installer bug)
- "less than 3% of a typical context window" → ambiguous; 3.4% of 128K, 0.4% of 1M
- "evolves its own rules" → E26 (promotion) is still TESTING; infrastructure built but unproven

**SUGGEST**:
- Dataset is undersold — actual data is 12,000+ steps, not 7,000
- Novel Contribution #1 should highlight adversarial falsification mechanisms (Thorns, Refutation Gate)
- Ground biological terminology in standard LLM terms for clarity

---

### Reviewer 2 — Empirical Software Engineering

**Summary**: The concept of evolutionary rule optimization is interesting and the engineering effort is commendable, but the empirical evaluation suffers from methodological flaws, lack of statistical rigor, and conflation of correlation with causation.

**Strengths**:
- Cytogenesis concept is creative and potentially impactful
- Engineering effort is substantial and well-documented
- AI failure mode taxonomy is practically useful

**Weaknesses**:
- **Selection Bias**: 66 baseline sessions were on a different model family and time period than the 17 governed sessions — massive confounding
- **Statistical Invalidity**: 1.1% is best-case from a single validation, not the mean (18.8%). No variance, confidence intervals, or significance tests
- **Unfounded Causal Claims**: "reduction attributable to" implies causation from an observational comparison
- **Reproducibility**: Masked dataset not publicly available for independent verification
- **Missing Related Work**: DSPy, Constitutional AI, Reflexion, LATS not cited

**Questions for Authors**:
1. Can you provide variance and statistical significance tests for waste rates?
2. How do you isolate governance framework effects from confounding variables?
3. How is "waste rate" formally annotated? Single or multi-rater?
4. Will the dataset be open-sourced?

**Recommendation**: Revise (Major)  
**Confidence**: 4/5

---

### Reviewer 3 — Evolutionary Computation & Adaptive Systems

**Summary**: The infrastructure and empirical measurement of AI coding waste are impressive, but the evolutionary framing is biologically imprecise and structurally more akin to heuristic thresholding than true evolutionary computation.

**Strengths**:
- Strong empirical grounding (83 sessions, 7,000+ steps)
- Concrete fitness tracking with end-to-end telemetry pipeline
- Extensive working tooling implementation

**Weaknesses**:
- **Biological Metaphor Inaccuracy**: "Speciation" (divergence) is used where "Fixation" or "Generalization" would be correct; system lacks genetic crossover or random mutation
- **Fitness Function Limitations**: Optimizes for precision only, ignores recall (false negatives); `impact_weight` is subjective
- **Superficial Adaptation**: `cell_adapt.py` uses hardcoded heuristic suggestions; doesn't actually rewrite rule content
- **"Without Human Authorship" Overclaims**: Initial cells are LLM-generated via human-designed prompts; adaptation doesn't rewrite rules autonomously; human feedback required at session boundaries
- **Incomplete Closed Loop**: Generation, scoring, and pruning work; adaptation doesn't programmatically alter rule text

**Questions for Authors**:
1. How do you account for false negatives in the fitness function?
2. Does `cell_adapt.py` actually rewrite cell content or just suggest changes?
3. Why is promotion labeled "Speciation" rather than "Generalization"?

**Recommendation**: Revise  
**Confidence**: 4/5

---

## Revisions Made After Round 1

Based on the 7 issues flagged across 3 reviewers, the following changes were made:

| # | Issue | Original Text | Revised Text |
|:-:|:------|:-------------|:-------------|
| 1 | Cherry-picked waste rate | "waste rates as low as 1.1%" | "average waste rate of 18.8%, with best-case results as low as 1.1%" |
| 2 | Inaccurate baseline label | "66 pre-governance" | "66 partially-governed baseline sessions" |
| 3 | Causal overclaiming | "reduction attributable to" | "reduction correlated with" |
| 4 | Autonomous overclaiming | "without human authorship" | "human-in-the-loop evolutionary system" |
| 5 | Ambiguous context window | "less than 3% of a typical context window" | "approximately 3.4% of a 128K context window" |
| 6 | Missing dataset size | "over 7,000 execution steps" | "over 12,000 annotated execution steps" |
| 7 | No limitations | (none) | Added full Limitations and Future Work section |

Additional changes:
- Acknowledged confounding variables explicitly in the results paragraph
- Grounded biological terminology in standard LLM terms (prompt personas, anti-pattern vectors, escalation thresholds)
- Clarified that adaptation provides heuristic suggestions, not autonomous rewriting
- Added adversarial falsification mechanisms to Contribution #1 (Thorns, Refutation Gate)
- Acknowledged fitness function optimizes for precision only, not recall
- Referenced E23–E26 as registered experiments to address gaps

---

## Round 2: Revised Submission

### Reviewer 4 — AI Safety & Alignment

**Summary**: The revised abstract presents a governance framework with well-scoped claims, accurately characterizing it as a human-in-the-loop evolutionary system. The author has effectively addressed prior review concerns.

**Strengths**:
- "Human-in-the-loop evolutionary system" characterization is highly accurate and avoids overstating self-improvement capabilities
- Limitations section is exemplary — directly addresses multi-rater reliability, confounding variables, and lack of end-to-end validation
- Privacy claims are strictly consistent with the NOTICE file
- Biological metaphors are immediately grounded in concrete technical mechanisms

**Remaining Weaknesses**:
- Review mode nomenclature (Breeze through Tempest, Spores through Mulch) is slightly jargon-heavy for an abstract

**Minor Suggestions**:
- Add inline definition of "waste rate" (e.g., "non-productive, hallucinatory, or reworked execution steps") on first mention

**Recommendation**: **Accept**  
**Confidence**: 5/5

---

### Reviewer 5 — Senior Research Editor

**Summary**: The abstract presents a quantitative evaluation of an adaptive governance framework, with transparent reporting alongside its limitations. It follows abstract conventions excellently and tells a complete, self-contained story.

**Strengths**:
- Excellent structure (problem → approach → results → contributions → limitations)
- Biological metaphors immediately paired with technical equivalents — neutralizes alienation risk
- Scientific rigor in reporting: results AND confounding factors presented together
- Self-contained: complete story without requiring external context
- Title and keywords accurate and well-optimized for discoverability

**Remaining Issues**:
- **Length**: ~520 words; reads as an extended abstract rather than a standard conference abstract (150-300 words)
- **Unnecessary nomenclature**: Naming specific modes (Breeze through Tempest, Spores through Mulch) consumes word count without adding conceptual clarity
- **Implementation details**: License, cross-platform support, and privacy invariant could move to Introduction

**Line-level Suggestions**:
- Remove parenthetical mode/prong names to save space and reduce jargon density
- Consider whether the privacy invariant paragraph is necessary in the abstract vs. Introduction
- Compress the dogfooding paragraph

**Recommendation**: Minor Revision  
**Confidence**: 5/5

---

## Round 3: Editorial Revisions

Applied remaining suggestions from Reviewers 4 and 5:

| # | Reviewer | Suggestion | Change Made |
|:-:|:--------:|:-----------|:------------|
| 1 | R4 | Define "waste rate" inline on first mention | Added: "waste rates — non-productive, hallucinatory, or reworked execution steps —" |
| 2 | R5 | Remove mode/prong names from abstract | Removed "(Breeze through Tempest)" and "(Spores through Mulch)" |
| 3 | R5 | Remove prong-specific names (Thorns, Refutation Gate) | Generalized to "adversarial testing prong" and "refutation gate" |
| 4 | R5 | Compress privacy invariant paragraph | Merged with overhead metrics into single sentence |
| 5 | R5 | Compress dogfooding paragraph | Reduced from 2 sentences to 1 |

Word count reduction: ~520 → ~430 words.

---

## Final Status

| Round | Reviewers | Outcome |
|:-----:|:---------:|:--------|
| **Round 1** | R1, R2, R3 | 7 substantive issues found → all corrected |
| **Round 2** | R4, R5 | **Accept** (R4), **Minor Revision** (R5, editorial only) |
| **Round 3** | — | R4/R5 editorial suggestions applied |

All factual claims have been verified against the codebase. All overclaiming identified in Round 1 has been corrected. The limitations section was praised by both Round 2 reviewers for its intellectual honesty. Round 3 editorial changes tightened language and reduced jargon density per R5's recommendations.
