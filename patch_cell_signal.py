import re

with open('scripts/cell_signal.sh', 'r') as f:
    content = f.read()

# Update usage
content = content.replace(
    '#   bash scripts/cell_signal.sh <cell_id> <tp|fp|fn> [--metric key=value]',
    '#   bash scripts/cell_signal.sh <cell_id> <tp|fp|fn> [--metric key=value] [--stress]'
)

# Replace argument parsing
old_arg_parsing = """METRIC_KEY=""
METRIC_VAL=""
if [ "$#" -ge 2 ] && [ "$1" == "--metric" ]; then
  # Split on first equals sign
  METRIC_KEY="${2%%=*}"
  METRIC_VAL="${2#*=}"
fi"""

new_arg_parsing = """METRIC_KEY=""
METRIC_VAL=""
STRESS="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --metric)
      if [ "$#" -ge 2 ]; then
        METRIC_KEY="${2%%=*}"
        METRIC_VAL="${2#*=}"
        shift 2
      else
        shift
      fi
      ;;
    --stress)
      STRESS="true"
      shift
      ;;
    *)
      shift
      ;;
  esac
done"""

content = content.replace(old_arg_parsing, new_arg_parsing)

# Update python call
content = content.replace(
    'python3 -c "$PYTHON_HELPER" "$TARGET_CELL" "$OUTCOME" "$METRIC_KEY" "$METRIC_VAL" "$METRICS_FILE"',
    'python3 -c "$PYTHON_HELPER" "$TARGET_CELL" "$OUTCOME" "$METRIC_KEY" "$METRIC_VAL" "$METRICS_FILE" "$STRESS"'
)

# Update python script args
old_python_args = """file_path = sys.argv[1]
outcome = sys.argv[2]
metric_key = sys.argv[3]
metric_val = sys.argv[4]
metrics_file = sys.argv[5]"""

new_python_args = """file_path = sys.argv[1]
outcome = sys.argv[2]
metric_key = sys.argv[3]
metric_val = sys.argv[4]
metrics_file = sys.argv[5]
stress = True if sys.argv[6] == 'true' else False"""

content = content.replace(old_python_args, new_python_args)

# Update python metadata modification
old_metadata_mod = """if outcome == 'tp':
    triggers += 1
    tp += 1
elif outcome == 'fp':
    triggers += 1
    fp += 1
elif outcome == 'fn':
    triggers += 1

new_score = (tp / triggers) if triggers > 0 else 0.0
fitness['triggers'] = triggers
fitness['true_positives'] = tp
fitness['false_positives'] = fp
fitness['score'] = new_score
fitness['last_trigger_date'] = datetime.utcnow().isoformat() + "Z\"\"\"
"""
# Oops, let's just do a regex replace for the fitness modification

metadata_mod = """if outcome == 'tp':
    triggers += 1
    tp += 1
elif outcome == 'fp':
    triggers += 1
    fp += 1
elif outcome == 'fn':
    triggers += 1

new_score = (tp / triggers) if triggers > 0 else 0.0
fitness['triggers'] = triggers
fitness['true_positives'] = tp
fitness['false_positives'] = fp
fitness['score'] = new_score
fitness['last_trigger_date'] = datetime.utcnow().isoformat() + "Z"

if stress:
    fitness['stress_survived'] = fitness.get('stress_survived', 0) + 1"""

content = re.sub(
    r"if outcome == 'tp':.*?fitness\['last_trigger_date'\] = datetime\.utcnow\(\)\.isoformat\(\) \+ \"Z\"",
    metadata_mod,
    content,
    flags=re.DOTALL
)

with open('scripts/cell_signal.sh', 'w') as f:
    f.write(content)
