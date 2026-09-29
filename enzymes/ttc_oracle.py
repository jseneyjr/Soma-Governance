#!/usr/bin/env python3
"""
TTC Oracle Engine for Soma.
Evaluates proposed diffs against hidden, hard-blocking foundational rules (.oracles)
using an LLM-as-a-judge before they are allowed to be written to disk.
"""

import os
import sys
import glob

# Ensure we can import inference_provider
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from inference_provider import resolve_provider

def load_oracles(workspace):
    oracles_dir = os.path.join(workspace, 'genome', '.oracles')
    oracles = []
    if not os.path.exists(oracles_dir):
        return oracles
    
    for f in glob.glob(os.path.join(oracles_dir, '*.md')):
        with open(f, 'r', encoding="utf-8") as file:
            oracles.append((os.path.basename(f), file.read()))
    return oracles

def evaluate_change(workspace, target_file, proposed_content):
    oracles = load_oracles(workspace)
    if not oracles:
        return "APPROVED: No oracles defined."

    # Load inference provider
    provider = resolve_provider(workspace)
    if not provider:
        return "APPROVED: No inference provider available to run TTC Oracle."

    # Combine oracles into a single rulebook for the prompt
    rulebook = ""
    for name, content in oracles:
        rulebook += f"\n--- RULEBOOK: {name} ---\n{content}\n"

    prompt = f"""
You are the TTC Oracle, a strict and unforgiving gatekeeper for this repository.
You must evaluate the following proposed change against the foundational rules (Oracles).

{rulebook}

TARGET FILE:
{target_file}

PROPOSED CONTENT:
{proposed_content}

INSTRUCTIONS:
Evaluate if the proposed content violates ANY of the rules defined in the rulebooks.
If it violates a rule, you MUST output exactly:
REJECTED: [Name of Rulebook violated] - [Specific, precise reason for rejection]

If it perfectly aligns with all rules, you MUST output exactly:
APPROVED

Respond ONLY with REJECTED or APPROVED as specified above. Do not include any other text.
"""
    try:
        # Use a lightweight fast model for TTC intercepts
        result = provider.generate(prompt, model="gemini-2.5-flash").strip()
        if not result.startswith("REJECTED") and not result.startswith("APPROVED"):
            # Fallback for weird outputs
            if "REJECTED" in result:
                return result
            return "APPROVED"
        return result
    except Exception as e:
        return f"REJECTED: Oracle evaluation failed ({str(e)})"

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: ttc_oracle.py <workspace> <target_file> [proposed_content_file]")
        sys.exit(1)
        
    workspace = sys.argv[1]
    target_file = sys.argv[2]
    
    # We can either pass content directly or via a file
    if len(sys.argv) >= 4:
        with open(sys.argv[3], 'r', encoding="utf-8") as f:
            proposed_content = f.read()
    else:
        proposed_content = sys.stdin.read()
        
    result = evaluate_change(workspace, target_file, proposed_content)
    print(result)
    
    if result.startswith("REJECTED"):
        sys.exit(1)
    sys.exit(0)
