import re

with open('scripts/cell_fitness.py', 'r') as f:
    content = f.read()

# 1. Add bayesian_fitness and antifragile_bonus
funcs = """
def bayesian_fitness(tp, fp, confidence=0.90):
    \"\"\"Beta-Binomial posterior with Jeffrey's prior.\"\"\"
    a = tp + 0.5
    b = fp + 0.5
    mean = a / (a + b)
    import math
    std = math.sqrt((a * b) / ((a + b) ** 2 * (a + b + 1)))
    z = 1.645
    lower = max(0, mean - z * std)
    upper = min(1, mean + z * std)
    certainty = 'low' if (tp + fp) < 5 else 'medium' if (tp + fp) < 20 else 'high'
    return {
        'mean': round(mean, 4),
        'lower_90': round(lower, 4),
        'upper_90': round(upper, 4),
        'certainty': certainty
    }

def antifragile_bonus(metadata):
    \"\"\"Cells gain +5% fitness per survived high-intensity review.\"\"\"
    stress_events = metadata.get('fitness', {}).get('stress_survived', 0)
    return 1.0 + (0.05 * min(stress_events, 10))

"""
content = content.replace('def decayed_fitness', funcs + 'def decayed_fitness')

# 2. Add --bayesian
content = content.replace(
    'parser.add_argument("--cross-repo", action="store_true", help="Aggregate fitness across multiple repos in METRICS_REPO")',
    'parser.add_argument("--cross-repo", action="store_true", help="Aggregate fitness across multiple repos in METRICS_REPO")\n    parser.add_argument("--bayesian", action="store_true", help="Output bayesian estimates")'
)

# 3. Add TOTAL_SESSIONS parsing logic in main()
parse_sessions = """
    workspace = resolve_workspace(__file__)
    total_sessions = 30
    conf_path = os.path.join(workspace, "steering.conf")
    if os.path.exists(conf_path):
        with open(conf_path) as f:
            for line in f:
                if line.startswith("TOTAL_SESSIONS="):
                    try:
                        total_sessions = int(line.strip().split("=")[1])
                    except:
                        pass
"""
content = content.replace('    workspace = resolve_workspace(__file__)', parse_sessions)

# 4. Anti-Goodhart Specificity Penalty, Antifragile Fitness Bonus, SNR Quality Metric, Wall Extinction Immunity
scoring_logic = """
        if triggers == 0:
            score = None
            snr_db = 0.0
        else:
            score = (tp / triggers) * impact_weight
            
            trigger_rate = triggers / max(total_sessions, 1)
            specificity_penalty = 1.0 - min(trigger_rate, 1.0)
            if trigger_rate > 0.8:
                score = score * specificity_penalty
                
            score = score * antifragile_bonus(metadata)
            
            import math
            if tp > 0 and fp > 0:
                snr_db = round(10 * math.log10(tp / fp), 1)
            elif tp > 0:
                snr_db = float('inf')
            else:
                snr_db = 0.0
"""
content = re.sub(r'        if triggers == 0:\n.*?score = \(tp / triggers\) \* impact_weight', scoring_logic, content, flags=re.DOTALL)

apoptosis_logic = """
        # Apoptosis: immediate eviction if false positives dominate
        if fp > 0 and tp > 0 and fp > 2 * tp:
            if cell_type == 'wall':
                status = "APOPTOSIS_WARNING"
            else:
                status = "APOPTOSIS"
"""
content = content.replace(
    '        # Apoptosis: immediate eviction if false positives dominate\n        if fp > 0 and tp > 0 and fp > 2 * tp:\n            status = "APOPTOSIS"',
    apoptosis_logic
)

results_append_old = """
        results.append({
            "cell": cell_name,
            "type": cell_type,
            "hypothesis": metadata.get('hypothesis', ''),
            "triggers": triggers,
            "tp": tp,
            "fp": fp,
            "score": score,
            "decayed_score": dec_score,
            "status": status
        })
"""
results_append_new = """
        res = {
            "cell": cell_name,
            "type": cell_type,
            "hypothesis": metadata.get('hypothesis', ''),
            "triggers": triggers,
            "tp": tp,
            "fp": fp,
            "score": score,
            "decayed_score": dec_score,
            "status": status,
            "snr_db": snr_db
        }
        if args.bayesian:
            res['bayesian'] = bayesian_fitness(tp, fp)
        results.append(res)
"""
content = content.replace(results_append_old, results_append_new)

printing_logic = """
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        if args.bayesian:
            print(f"{'Cell':<20} | {'Type':<12} | {'Triggers':<8} | {'TP':<4} | {'FP':<4} | {'Raw':<6} | {'Decayed':<7} | {'Status':<10} | {'Bayesian Mean':<13} | {'SNR':<5}")
            print("-" * 105)
            for r in results:
                score_str = f"{r['score']:.2f}" if r['score'] is not None else "null"
                dec_score_str = f"{r['decayed_score']:.2f}" if r['decayed_score'] is not None else "null"
                bayes_mean = f"{r['bayesian']['mean']:.2f} ({r['bayesian']['certainty']})" if 'bayesian' in r else ""
                print(f"{r['cell']:<20} | {r['type']:<12} | {r['triggers']:<8} | {r['tp']:<4} | {r['fp']:<4} | {score_str:<6} | {dec_score_str:<7} | {r['status']:<10} | {bayes_mean:<13} | {r.get('snr_db', 0):<5}")
        else:
            print(f"{'Cell':<20} | {'Type':<12} | {'Triggers':<8} | {'TP':<4} | {'FP':<4} | {'Raw':<6} | {'Decayed':<7} | {'Status':<10} | {'SNR':<5}")
            print("-" * 93)
            for r in results:
                score_str = f"{r['score']:.2f}" if r['score'] is not None else "null"
                dec_score_str = f"{r['decayed_score']:.2f}" if r['decayed_score'] is not None else "null"
                print(f"{r['cell']:<20} | {r['type']:<12} | {r['triggers']:<8} | {r['tp']:<4} | {r['fp']:<4} | {score_str:<6} | {dec_score_str:<7} | {r['status']:<10} | {r.get('snr_db', 0):<5}")
"""
content = re.sub(r'    if args.json:\n        print\(json\.dumps\(results, indent=2\)\)\n    else:\n.*?        print\(f"\{r\[\'cell\'\]:<20\}.*?\{r\[\'status\'\]:<10\}"\)', printing_logic, content, flags=re.DOTALL)

with open('scripts/cell_fitness.py', 'w') as f:
    f.write(content)
