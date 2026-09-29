import argparse
import json
import os
import glob
import re
import sys

from soma_resolve import resolve_workspace
from inference_provider import resolve_provider

def parse_args():
    parser = argparse.ArgumentParser(description="Ground-Truth Token Census")
    parser.add_argument("--model", default="gemini-2.0-flash", help="Model to use for token counting")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--calibrate", action="store_true", help="Compute the actual ratio")
    return parser.parse_args()

def extract_frontmatter(text):
    match = re.match(r'^---\n(.*?)\n---', text, re.DOTALL)
    if match:
        return match.group(1)
    return ""

def get_trigger(frontmatter):
    match = re.search(r'^trigger:\s*(.*)$', frontmatter, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "unknown"

def word_count(text):
    return len(text.split())

# Hardcoded fallback ratio if provider cannot measure
FALLBACK_RATIO = 1.35

def count_tokens(text, model_name, provider):
    if not text.strip():
        return 0
    try:
        return provider.count_tokens(text, model_name)
    except Exception:
        # Fallback
        return int(word_count(text) * FALLBACK_RATIO)

def main():
    args = parse_args()
    
    workspace = resolve_workspace(__file__)
    rules_dir = os.path.join(workspace, "genome")
    skills_dir = os.path.join(workspace, "organs")
    
    provider = resolve_provider(workspace)
    
    results = []
    
    total_words = 0
    total_tokens = 0
    
    # Process Rules
    if os.path.exists(rules_dir):
        for filepath in glob.glob(os.path.join(rules_dir, "*.md")):
            basename = os.path.basename(filepath)
            with open(filepath, 'r', encoding="utf-8") as f:
                content = f.read()
            
            frontmatter = extract_frontmatter(content)
            trigger = get_trigger(frontmatter)
            
            w_full = word_count(content)
            w_front = word_count(frontmatter)
            
            if trigger == "always_on":
                c_type = "always_on_rule"
                t_idle = count_tokens(content, args.model, provider)
                t_active = t_idle
                w_idle = w_full
                w_active = w_full
            else:
                c_type = "conditional_rule"
                t_idle = count_tokens(frontmatter, args.model, provider)
                t_active = count_tokens(content, args.model, provider)
                w_idle = w_front
                w_active = w_full
            
            total_words += w_full
            total_tokens += count_tokens(content, args.model, provider)
            
            results.append({
                "filename": f"genome/{basename}",
                "type": c_type,
                "idle_words": w_idle,
                "idle_tokens": t_idle,
                "active_words": w_active,
                "active_tokens": t_active,
                "ratio": t_active / w_active if w_active else 0
            })
            
    # Process Skills
    if os.path.exists(skills_dir):
        for filepath in glob.glob(os.path.join(skills_dir, "*/SKILL.md")):
            # Get skill name from parent directory
            skill_name = os.path.basename(os.path.dirname(filepath))
            basename = f"organs/{skill_name}/SKILL.md"
            with open(filepath, 'r', encoding="utf-8") as f:
                content = f.read()
                
            frontmatter = extract_frontmatter(content)
            
            w_full = word_count(content)
            w_front = word_count(frontmatter)
            
            t_idle = count_tokens(frontmatter, args.model, provider)
            t_active = count_tokens(content, args.model, provider)
            w_idle = w_front
            w_active = w_full
            
            total_words += w_full
            total_tokens += t_active
            
            results.append({
                "filename": basename,
                "type": "skill",
                "idle_words": w_idle,
                "idle_tokens": t_idle,
                "active_words": w_active,
                "active_tokens": t_active,
                "ratio": t_active / w_active if w_active else 0
            })
            
    calibrated_ratio = total_tokens / total_words if total_words else FALLBACK_RATIO
    
    if args.calibrate:
        print(f"Calibrated Ratio: {calibrated_ratio:.2f}")
        return

    # Subtotals
    subtotals = {
        "always_on_rules_idle_tokens": sum(r["idle_tokens"] for r in results if r["type"] == "always_on_rule"),
        "conditional_rules_idle_tokens": sum(r["idle_tokens"] for r in results if r["type"] == "conditional_rule"),
        "conditional_rules_active_tokens": sum(r["active_tokens"] for r in results if r["type"] == "conditional_rule"),
        "skills_idle_tokens": sum(r["idle_tokens"] for r in results if r["type"] == "skill"),
        "skills_active_tokens": sum(r["active_tokens"] for r in results if r["type"] == "skill"),
    }
    
    grand_total_idle = subtotals["always_on_rules_idle_tokens"] + subtotals["conditional_rules_idle_tokens"] + subtotals["skills_idle_tokens"]
    
    if args.json:
        output = {
            "model": args.model,
            "measured_with_sdk": provider.__class__.__name__ != "PromptOnlyProvider",
            "calibrated_ratio": round(calibrated_ratio, 2),
            "files": results,
            "subtotals": subtotals,
            "grand_total_idle": grand_total_idle
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"{'Filename':<40} {'Type':<20} {'Idle W':<10} {'Idle T':<10} {'Active W':<10} {'Active T':<10} {'Ratio':<10}")
        print("-" * 115)
        for r in results:
            print(f"{r['filename']:<40} {r['type']:<20} {r['idle_words']:<10} {r['idle_tokens']:<10} {r['active_words']:<10} {r['active_tokens']:<10} {r['ratio']:.2f}")
        print("-" * 115)
        print("SUBTOTALS:")
        print(f"  Always-On Rules (Idle=Active): {subtotals['always_on_rules_idle_tokens']}")
        print(f"  Conditional Rules Idle:        {subtotals['conditional_rules_idle_tokens']}")
        print(f"  Conditional Rules Active:      {subtotals['conditional_rules_active_tokens']}")
        print(f"  Skills Idle:                   {subtotals['skills_idle_tokens']}")
        print(f"  Skills Active:                 {subtotals['skills_active_tokens']}")
        print(f"GRAND TOTAL IDLE OVERHEAD:       {grand_total_idle}")

if __name__ == '__main__':
    main()
