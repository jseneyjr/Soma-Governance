#!/usr/bin/env python3
"""Soma Test-Time Compute (TTC) Verifier

Intercepts proposed code changes (diffs) and runs a fast verification pass 
against the currently active JIT playbooks. Prevents the agent from executing 
actions that violate established rules, saving massive costs on rework loops.
"""

import sys
import os
import json
import subprocess
from typing import List, Dict

class TTCVerifier:
    def __init__(self, active_playbooks: List[Dict]):
        self.active_playbooks = active_playbooks

    def verify_proposal(self, proposed_diff: str, file_path: str) -> Dict[str, str]:
        """
        In production, this calls a lightweight LLM (e.g., Gemini Flash) to check 
        if the proposed_diff violates any rules in the active_playbooks.
        
        For this prototype, we simulate the LLM using keyword detection.
        """
        for playbook in self.active_playbooks:
            # Simulate an LLM detecting a violation
            if "React" in playbook.get("name", "") and "class " in proposed_diff:
                return {
                    "status": "REJECTED",
                    "reason": f"Violation of '{playbook['name']}': Class components are forbidden. Use functional components.",
                    "playbook": playbook
                }
            if "Testing" in playbook.get("name", "") and "assert True" in proposed_diff:
                return {
                    "status": "REJECTED",
                    "reason": f"Violation of '{playbook['name']}': Meaningless assertions detected.",
                    "playbook": playbook
                }
                
        return {
            "status": "APPROVED",
            "reason": "Proposal aligns with all active playbooks.",
            "playbook": None
        }

def get_escalation_protocol(file_path: str, workspace: str) -> str:
    sentinel = os.path.join(workspace, "enzymes", "escalation_sentinel.sh")
    if not os.path.exists(sentinel):
        return "breeze"
    try:
        result = subprocess.run([sentinel, file_path], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if line.startswith("PROTOCOL="):
                return line.split("=")[1].strip().lower()
    except Exception:
        pass
    return "breeze"

def soma_propose_change(file_path: str, proposed_content: str, active_playbooks: List[Dict]) -> str:
    """
    The new gateway MCP tool. The agent MUST use this to edit files.
    """
    workspace = os.getcwd()
    d = workspace
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, ".soma")):
            workspace = d
            break
        d = os.path.dirname(d)

    protocol = get_escalation_protocol(file_path, workspace)
    if protocol in ["maelstrom", "tempest"]:
        if "TEMPEST_OVERRIDE" not in proposed_content:
            return (f"🛑 TEMPEST ESCALATION TRIGGERED for {file_path}.\n"
                    "This file is highly sensitive (Core Infrastructure / Auth).\n"
                    "ACTION REQUIRED: You must dispatch the 'Security Audit Organ' and 'Performance Audit Organ' "
                    "subagents to review this proposed change concurrently.\n"
                    "Once they approve, append '# TEMPEST_OVERRIDE' to your proposed content and submit again.")

    print(f"[TTC] Agent proposed change to {file_path}. Protocol: {protocol}. Running Verifier...")
    verifier = TTCVerifier(active_playbooks)
    
    # Generate a mock diff for verification
    diff = proposed_content 
    
    result = verifier.verify_proposal(diff, file_path)
    
    import re
    if result["status"] == "REJECTED":
        # Log as True Positive for the active cell that caught this!
        playbook = result.get("playbook")
        if playbook and playbook.get("_path"):
            full_path = os.path.join(workspace, playbook["_path"])
            if os.path.exists(full_path):
                try:
                    with open(full_path, "r") as f:
                        content = f.read()
                    def inc(m): return f"{m.group(1)}{int(m.group(2)) + 1}"
                    content = re.sub(r'(triggers:\s*)(\d+)', inc, content)
                    content = re.sub(r'(true_positives:\s*)(\d+)', inc, content)
                    with open(full_path, "w") as f:
                        f.write(content)
                except Exception:
                    pass
                    
        return f"CRITICAL ERROR: Proposal Rejected.\nReason: {result['reason']}\nAction: Generate a new proposal that fixes this violation."
    
    # --- NEW: TTC Oracle Evaluation ---
    try:
        from enzymes.ttc_oracle import evaluate_change
        oracle_result = evaluate_change(workspace, file_path, proposed_content)
        if oracle_result.startswith("REJECTED"):
            print(f"[TTC Oracle] {oracle_result}")
            return f"CRITICAL ERROR: TTC Oracle Rejected Proposal.\n{oracle_result}\nAction: Ensure you follow the architectural tenets and standards."
    except Exception as e:
        print(f"[TTC Oracle] Error running oracle: {e}")
        
    print(f"[TTC] Proposal APPROVED. Executing file write to {file_path}...")
    try:
        with open(file_path, "w") as f:
            f.write(proposed_content)
    except Exception as e:
        return f"ERROR: Failed to write to {file_path}: {e}"
        
    return f"SUCCESS: Change verified and applied to {file_path}."

if __name__ == "__main__":
    # Test cases
    mock_playbooks = [
        {"name": "React Guidelines", "content": "Never use class components."},
        {"name": "Testing Guidelines", "content": "Tests must have valid assertions."}
    ]
    
    bad_proposal = "class MyComponent extends React.Component {\n  render() { return <div>Hi</div>; }\n}"
    good_proposal = "const MyComponent = () => <div>Hi</div>;"
    
    print("--- Test 1: Bad Proposal ---")
    print(soma_propose_change("src/App.jsx", bad_proposal, mock_playbooks))
    
    print("\n--- Test 2: Good Proposal ---")
    print(soma_propose_change("src/App.jsx", good_proposal, mock_playbooks))
