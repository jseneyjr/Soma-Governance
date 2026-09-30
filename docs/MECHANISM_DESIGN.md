# Formal Framework: Mechanism Design Mapping

> **Purpose**: This document maps Soma's biological naming to formal mechanism design
> concepts. Agents working in the codebase should reference this to understand
> the theoretical intent behind each component, not just its implementation.

---

## Term Mapping

### Directory Structure

| Codebase (Biology) | Formal Concept (Mechanism Design) | What It Actually Does |
|:---|:---|:---|
| `genome/` | **Constitutional rules** | Immutable foundational governance — rarely amended, high legitimacy cost to change |
| `enzymes/` | **Institutional procedures** | Automated enforcement and measurement scripts — the bureaucracy that makes governance operational |
| `organs/` | **Institutional capabilities** | Complex multi-step competencies (audit, review, onboarding) — what the governance system *can do* |
| `immune_system/` | **Oversight institution** | Independent verification body — structurally separated from the governed entity |
| `.soma/cells/` | **Adaptive policy layer** | Per-repository regulatory instruments — generated, tested, evolved, or sunset |
| `.soma/` | **Regulatory state** | Persistent governance artifacts for a specific jurisdiction (repository) |

### Adaptive Rule Types

| Codebase (Biology) | Formal Concept | Mechanism Design Role |
|:---|:---|:---|
| **Vacuole** | **Precedent / trap rule** | Encodes a known failure mode as a falsifiable hypothesis. Analogous to case law — "this specific thing went wrong, don't repeat it." |
| **Chloroplast** | **Best-practice norm** | Encodes an observed success pattern. Analogous to professional standards — "this approach worked, propagate it." |
| **Cell Wall** | **Hard constraint / invariant** | Non-negotiable safety boundary. Analogous to constitutional amendment — highest enforcement tier, cannot be overridden by lower rules. |
| **Membrane** | **Escalation trigger** | Sensitivity classifier that activates elevated review when specific areas change. Analogous to mandatory regulatory review for sensitive industries. |
| **Plasmodesmata** | **Interface contract** | Cross-service data shape and API agreement. Analogous to treaty — governs interactions between independent jurisdictions. |

### Evolutionary Operators

| Codebase (Biology) | Formal Concept | What It Addresses |
|:---|:---|:---|
| **Fitness scoring** | **Performance evaluation** | Measures rule effectiveness via precision × impact. The social choice function's proxy metric. |
| **Confidence decay / telomeres** | **Sunset clause** | Rules expire unless actively reinforced. Prevents bureaucratic ossification — the accumulation of rules nobody enforces. |
| **Selection / tournament** | **Competitive evaluation** | Diversity-preserving selection among candidate rules. Prevents monoculture in the policy landscape. |
| **Crossover** | **Policy synthesis** | Merges high-performing rules from different contexts. Analogous to synthesizing regulations from multiple jurisdictions. |
| **Metamorphosis** | **Regulatory promotion** | A rule earns a higher enforcement tier through demonstrated effectiveness. Advisory → mechanical → gate. |
| **Horizontal transfer** | **Policy import** | Importing rules from external repositories with probation period. Analogous to adopting foreign regulatory frameworks with adaptation. |
| **Pruning / extinction** | **Regulatory repeal** | Removing rules that fail to demonstrate effectiveness. The enforcement of sunset clauses. |
| **Cytogenesis** | **Rule generation** | Scanning a codebase to generate jurisdiction-specific governance. Analogous to a regulatory agency surveying an industry and drafting targeted regulations. |

### Verification Architecture

| Codebase (Biology) | Formal Concept | Mechanism Design Property |
|:---|:---|:---|
| **Layer 1: Deterministic tools** | **Objective audit** | Produces ungameable evidence. Analogous to financial audit with fixed accounting rules — the auditor cannot exercise judgment on what counts. |
| **Layer 2: Adversarial agents** | **Adversarial proceeding** | Information-partitioned reviewers who cannot collude. Directly implements **information asymmetry exploitation** — each reviewer sees different inputs, so agreement is meaningful. |
| **Arbiter (set algebra)** | **Mechanical adjudication** | Deterministic verdict from reviewer outputs. Removes judicial discretion — the "judge" applies fixed rules to structured inputs. |
| **Transcript verifier** | **Post-hoc audit** | Independently verifies self-reported claims against execution logs. Implements a **revelation mechanism** — agents cannot benefit from misreporting because reports are checked against the tape. |
| **Escaped defect tracking** | **External ground truth** | CI/CD exit codes provide signals outside the governance system's control. Breaks the **self-evaluation loop** — the system cannot grade itself on criteria it defines. |

### Review Intensity

| Codebase (Biology) | Formal Concept | When Applied |
|:---|:---|:---|
| **Breeze** | Expedited review | Low-risk, known-pattern changes |
| **Gale** | Standard review | Routine changes |
| **Trident** | Enhanced review | Features, refactors |
| **Maelstrom** | Intensive review | Architecture, security |
| **Tempest** | Maximum assurance | Catastrophic-risk changes, human gate required |

### Review Prongs

| Codebase (Biology) | Formal Concept |
|:---|:---|
| **Spores** | Preliminary survey — width-first problem identification |
| **Mycelium** | Impact analysis — blast radius mapping |
| **Roots** | Root-cause investigation — depth-first analysis |
| **Thorns** | Adversarial falsification — red team |
| **Bedrock** | Final gate — binary ship/block decision |
| **Mulch** | Learning extraction — post-decision knowledge capture |

---

## Mechanism Design Analysis: What Soma Implements

### Properties Soma HAS:

1. **Information asymmetry exploitation** (Layer 2 verification)
   - Two reviewers see different inputs → agreement is evidence, not collusion
   - This is an independent multi-agent elicitation protocol with deterministic arbitration

2. **Post-hoc revelation mechanism** (Transcript verifier)
   - Agents cannot benefit from false self-reports because claims are verified against logs
   - Partial strategy-proofness: lying about execution is detectable

3. **Sunset provisions** (Confidence decay)
   - Rules that aren't reinforced by evidence expire automatically
   - Prevents institutional accumulation of dead regulations

4. **Graduated enforcement** (Tiered promotion: advisory → mechanical → gate)
   - Rules earn enforcement power through demonstrated effectiveness
   - Low-confidence rules suggest; high-confidence rules block

5. **External ground truth** (Escaped defect tracking)
   - CI/CD exit codes provide signals the governance system cannot manufacture
   - Partially breaks the self-grading loop

6. **Budget balance** (Token economics / ROI)
   - Governance overhead (4,380 tokens/turn) is measurably less than prevented waste
   - The mechanism sustains itself without external subsidy

---

## Mechanism Design Analysis: What Soma is MISSING

> [!IMPORTANT]
> These are structural gaps visible only through the mechanism design lens.
> They represent the difference between "governance that works because the
> LLM happens to comply" and "governance that works because compliance is
> provably optimal."

### 1. No Incentive Compatibility

**The gap**: Soma tells agents what to do but doesn't make compliance instrumentally rational. An LLM follows rules because they're in the context window, not because following them produces better outcomes *for the agent*. The moment prompt pressure exceeds governance pressure, compliance evaporates.

**What this means**: Governance is imposed, not incentive-aligned. The system is fragile to prompt injection, high-pressure user requests, and context window overflow (where governance tokens get evicted first).

**What mechanism design would prescribe**: Design a mechanism where the agent demonstrably achieves its task faster/better when it follows the rules. Provide the agent with evidence of this: "agents that follow read-before-write complete tasks in 36 steps; agents that don't take 547 steps." Make compliance the dominant strategy, not just the mandated one.

### 2. No Formal Social Welfare Function

**The gap**: Soma optimizes for "low waste rate" and "high FPSR," but these are proxy metrics. The true objective — code quality, user satisfaction, task completion — is never formally defined. Without a formal objective, you can't prove the mechanism is optimal.

**What this means**: Soma could achieve 0% waste and 100% FPSR by having the agent do nothing (no steps = no waste). The metrics don't encode "the task must be completed." They assume the agent is trying and just measure efficiency.

**What mechanism design would prescribe**: Define the social welfare function explicitly: `W = task_completion × code_quality × (1 / cost)`. Then design governance to maximize W, not just minimize waste.

### 3. No Strategy-Proofness Guarantee

**The gap**: Can an agent benefit from strategic behavior? The transcript verifier catches *lies about execution*, but what about *strategic execution*? An agent could learn to produce minimal, low-risk changes that always pass review — technically compliant but not maximally useful.

**What this means**: An agent could satisfy every Soma rule while still underperforming. Compliance ≠ quality. This is the regulatory capture risk — the agent learns to satisfy the measurement rather than the intent.

**What mechanism design would prescribe**: Design rules where the agent cannot game the metric without also achieving the actual goal. This requires the metrics to be tightly coupled to real outcomes — which is what escaped defect tracking partially provides.

### 4. No Repeated-Game Dynamics

**The gap**: Each session is independent. The agent has no memory of past sessions, no reputation to protect, no consequences for past defection. In mechanism design, repeated interactions enable cooperation through reputation and punishment.

**What this means**: Every session starts from zero trust. The governance system can't learn "this agent type tends to hallucinate APIs" and adapt preemptively. Cross-session learning is entirely rule-based (cells), not agent-based.

**What mechanism design would prescribe**: Reputation scores per agent-type (Flash, Pro, etc.) that influence initial review intensity. An agent-type that historically produces more escaped defects gets stricter governance by default.

### 5. No Agent-Type Discrimination

**The gap**: Soma treats all agents identically regardless of capability tier. A Flash model gets the same rules as a Pro model, even though their failure modes differ systematically. Flash hallucinates more; Pro over-engineers more.

**What this means**: Governance is one-size-fits-all. In mechanism design with heterogeneous agents, the mechanism should adapt to agent type (Bayesian mechanism design).

**What mechanism design would prescribe**: Type-conditional governance — detect or declare the agent's capability tier and adjust rule strictness, review intensity, and delegation limits accordingly.

### 6. No Contract / Commitment Device

**The gap**: There's no formal specification of mutual obligations. The user doesn't commit to "I will provide clear task specifications" and the agent doesn't commit to "I will follow read-before-write." The governance is unilateral — imposed on the agent, with no obligations on the user.

**What this means**: Poor user specifications (vague prompts, contradictory requirements) cause waste that governance can't prevent. The system optimizes agent behavior but not user behavior.

**What mechanism design would prescribe**: Bilateral contracts — governance rules for the agent AND input quality requirements for the user. E.g., "if the task specification is ambiguous, the agent MUST clarify before acting" (Soma has this in providence §1, but it's not formalized as a contract).

---

## Implications for Development

When working in this codebase, understand that:

1. **"Fitness" is a proxy metric, not a welfare function.** Don't optimize fitness without checking that the underlying goal (code quality, task completion) is still being served.

2. **Rule compliance is imposed, not incentive-compatible.** Rules work because the LLM context window forces attention on them. If you're designing a new rule, ask: "would a rational agent follow this even without being told to?"

3. **The verification architecture is the strongest mechanism design component.** Information partitioning + deterministic arbitration + transcript verification is a genuine mechanism design contribution. Protect its independence.

4. **The gaps (incentive compatibility, strategy-proofness, repeated games) are research opportunities**, not bugs. They represent the frontier between "governance that works empirically" and "governance that works provably."
