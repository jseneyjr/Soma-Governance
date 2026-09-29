#!/usr/bin/env python3
"""Soma Run — Master Execution Orchestrator

Wires together all Soma engines into a single, unified execution pipeline.

Pipeline order:
  PRE-ACTION:
    1. Interoception  — Check internal state (CLEAR/CAUTION/CRITICAL)
    2. Resilience     — Check stress + drift (NOMINAL/CRITICAL_STRESS/CONTEXT_DRIFT)
    3. TTC Verifier   — Verify proposal against active playbooks

  POST-ACTION:
    4. Outcome        — Score the actual result
    5. Coherence      — Cross-signal integrity check (COHERENT/SUSPICIOUS/INCOHERENT)
    6. Resilience     — Trigger Graceful Reset if INCOHERENT

  SESSION END:
    7. Sleep          — Experience replay, structural pruning, dream compression
    8. HGT            — If any playbook hits 95% fitness, trigger Ribosome

Usage:
  from soma_run import SomaOrchestrator
  soma = SomaOrchestrator(workspace='/path/to/project')
  result = soma.pre_action(proposal="...", files_touched=3, depth=4)
  soma.post_action(outcome_delta=0.3, changes=3, prediction_match=0.9)
  soma.end_session()
"""

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Add Soma enzymes to path
SOMA_DIR = os.path.dirname(os.path.abspath(__file__))
ENZYMES_DIR = os.path.join(SOMA_DIR, "enzymes")
sys.path.insert(0, ENZYMES_DIR)

from resilience_engine import calculate_stress_response
from soma_coherence import CoherenceSignal, check_coherence
from soma_interoception import calculate_internal_state
from ttc_verifier import soma_propose_change


@dataclass
class SomaState:
    """Tracks session state across all engines."""
    consecutive_failures: int = 0
    turns_elapsed: int = 0
    turns_since_grounding: int = 0
    files_touched: int = 0
    token_estimate: int = 0
    token_budget: int = 100_000
    coherence_flags: List[str] = field(default_factory=list)
    last_ttc_approved: bool = True
    last_outcome_delta: float = 0.0


class SomaOrchestrator:
    """
    The unified Soma execution pipeline.
    All engines run in sequence. Blocks proceed only when each gate passes.
    """

    def __init__(self, workspace: str, active_playbooks: Optional[List[Dict]] = None):
        self.workspace = workspace
        self.active_playbooks = active_playbooks or []
        self.state = SomaState()
        print(f"🧬 Soma Orchestrator initialized. Workspace: {workspace}")

    # ─────────────────────────────────────────────
    # PRE-ACTION PIPELINE
    # ─────────────────────────────────────────────
    def pre_action(
        self,
        proposal: str,
        file_path: str = "unknown",
        files_touched: int = 0,
        dependency_depth: int = 0,
        token_estimate: Optional[int] = None,
    ) -> Dict:
        """Run the full pre-action gate before any file is written."""
        self.state.turns_elapsed += 1
        self.state.turns_since_grounding += 1
        self.state.files_touched = max(self.state.files_touched, files_touched)
        if token_estimate:
            self.state.token_estimate = token_estimate

        print(f"\n{'═'*60}")
        print(f"🧬 SOMA PRE-ACTION | Turn {self.state.turns_elapsed}")
        print(f"{'═'*60}")

        # ── Stage 1: Interoception ──────────────────────────────
        intero = calculate_internal_state(
            token_count=self.state.token_estimate,
            token_budget=self.state.token_budget,
            files_touched=self.state.files_touched,
            dependency_depth=dependency_depth,
            turns_since_grounding=self.state.turns_since_grounding,
        )
        print(f"\n[1/3] Interoception: {intero['status']} (score={intero['score']})")
        if intero["status"] == "CRITICAL":
            print(f"  ⚠️  {intero['message']}")
            return {"gate": "BLOCKED", "stage": "interoception", "detail": intero}

        # ── Stage 2: Resilience ─────────────────────────────────
        resilience = calculate_stress_response(
            self.state.consecutive_failures,
            self.state.turns_since_grounding,
        )
        print(f"[2/3] Resilience: {resilience['status']}")
        if resilience["status"] == "CRITICAL_STRESS":
            print("  ⚠️  Graceful Reset triggered.")
            print(f"  {resilience['payload']}")
            self.state.consecutive_failures = 0  # Reset after intervention
            self.state.turns_since_grounding = 0
            return {"gate": "RESET", "stage": "resilience", "detail": resilience}
        elif resilience["status"] == "CONTEXT_DRIFT":
            print("  ⚠️  Grounding Probe triggered.")
            print(f"  {resilience['payload']}")
            self.state.turns_since_grounding = 0  # Reset drift counter

        # ── Stage 3: TTC Verifier ───────────────────────────────
        print("[3/3] TTC Verifier: running...")
        ttc_result = soma_propose_change(file_path, proposal, self.active_playbooks)
        approved = "SUCCESS" in ttc_result
        self.state.last_ttc_approved = approved
        print(f"  → {'APPROVED ✅' if approved else 'REJECTED ❌'}")
        if not approved:
            self.state.consecutive_failures += 1
            print(f"  {ttc_result}")
            return {"gate": "BLOCKED", "stage": "ttc", "detail": ttc_result}

        return {"gate": "PASS", "interoception": intero, "resilience": resilience}

    # ─────────────────────────────────────────────
    # POST-ACTION PIPELINE
    # ─────────────────────────────────────────────
    def post_action(
        self,
        outcome_delta: float,
        changes: int = 1,
        prediction_match: float = 0.9,
    ) -> Dict:
        """Run post-action scoring and coherence check."""
        self.state.last_outcome_delta = outcome_delta

        print(f"\n{'─'*60}")
        print(f"🧬 SOMA POST-ACTION | Turn {self.state.turns_elapsed}")
        print(f"{'─'*60}")

        # ── Stage 4: Outcome ────────────────────────────────────
        outcome_str = "PASS ✅" if outcome_delta > 0 else "FAIL ❌"
        print(f"[4/5] Outcome Engine: {outcome_str} (delta={outcome_delta:+.2f})")
        if outcome_delta <= 0:
            self.state.consecutive_failures += 1
        else:
            self.state.consecutive_failures = 0  # Reset on success

        # ── Stage 5: Signal Coherence ───────────────────────────
        signal = CoherenceSignal(
            ttc_approved=self.state.last_ttc_approved,
            outcome_delta=outcome_delta,
            stress_level=self.state.consecutive_failures,
            interoception_score=min(1.0, self.state.files_touched / 20.0),
            prediction_match=prediction_match,
            change_magnitude=changes,
        )
        coherence = check_coherence(signal)
        print(f"[5/5] Signal Coherence: {coherence.verdict} (score={coherence.score})")

        if coherence.flags:
            self.state.coherence_flags.extend(coherence.flags)
            for flag in coherence.flags:
                print(f"  ⚡ {flag[:80]}...")

        if coherence.verdict == "INCOHERENT":
            print("  🛑 HARD BLOCK — Triggering Graceful Reset.")
            self.state.consecutive_failures = self.state.consecutive_failures + 3  # Force reset next turn

        return {"coherence": coherence.verdict, "flags": coherence.flags}

    # ─────────────────────────────────────────────
    # SESSION END PIPELINE
    # ─────────────────────────────────────────────
    def end_session(self) -> Dict:
        """Run Sleep Engine + check for HGT triggers."""
        print(f"\n{'═'*60}")
        print("🧬 SOMA SESSION END — Sleep Cycle Starting")
        print(f"{'═'*60}")

        sleep_script = os.path.join(ENZYMES_DIR, "soma_sleep.py")
        if os.path.exists(sleep_script):
            import subprocess
            result = subprocess.run(
                [sys.executable, sleep_script],
                cwd=self.workspace,
                capture_output=True,
                text=True,
            )
            print(result.stdout)
        else:
            print("  [Sleep Engine not found — skipping]")

        # Log coherence flags for sleep analysis
        if self.state.coherence_flags:
            flags_path = os.path.join(self.workspace, ".soma", "metrics", "coherence_flags.jsonl")
            os.makedirs(os.path.dirname(flags_path), exist_ok=True)
            with open(flags_path, "a") as f:
                f.writelines(json.dumps({"flag": flag, "turns": self.state.turns_elapsed}) + "\n" for flag in self.state.coherence_flags)
            print(f"  📋 {len(self.state.coherence_flags)} coherence flag(s) logged for Sleep analysis.")

        summary = {
            "turns": self.state.turns_elapsed,
            "failures": self.state.consecutive_failures,
            "coherence_flags": len(self.state.coherence_flags),
        }
        print(f"\n✅ Session complete. Summary: {summary}")
        return summary
