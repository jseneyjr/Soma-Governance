import re

with open('scripts/cell_selection.sh', 'r') as f:
    content = f.read()

content = content.replace(
    "tp = get_val('true_positives', 0)",
    "tp = get_val('true_positives', 0)\n        fp = get_val('false_positives', 0)\n        type_match = re.search(r'type:\s*([^\\s\\n]+)', fm)\n        cell_type = type_match.group(1) if type_match else ''"
)

old_scoring = """        if triggers == 0:
            category = "DORMANT"
            score = 0.0
        else:
            score = tp / triggers
            if score > 0.7: category = "SURVIVE"
            elif score >= 0.3: category = "ADAPT"
            else: category = "EXTINCT"
"""
new_scoring = """        if triggers == 0:
            category = "DORMANT"
            score = 0.0
        else:
            score = tp / triggers
            if fp > 0 and tp > 0 and fp > 2 * tp:
                if cell_type == 'wall':
                    category = "APOPTOSIS_WARNING"
                else:
                    category = "APOPTOSIS"
            elif score > 0.7: category = "SURVIVE"
            elif score >= 0.3: category = "ADAPT"
            else: category = "EXTINCT"
"""
content = content.replace(old_scoring, new_scoring)

content = content.replace(
    'if category == "EXTINCT":',
    'if category in ("EXTINCT", "APOPTOSIS"):'
)

with open('scripts/cell_selection.sh', 'w') as f:
    f.write(content)
