#!/bin/bash
# cell_create.sh: Programmatic Cell Creation for Prism AI Steering
# Usage: bash scripts/cell_create.sh --type <type> --hypothesis <hypothesis> --prediction <prediction> --falsification <falsification> [options]

# Source common.sh if it exists (for compatibility with existing structure)
if [[ -f "scripts/common.sh" ]]; then
  source "scripts/common.sh"
fi

# Default values
TYPE=""
HYPOTHESIS=""
PREDICTION=""
FALSIFICATION=""
WEIGHT="1.0"
TAGS=""
EXPIRY_SESSIONS="15"
EXPIRY_DAYS="60"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -t|--type)
      TYPE="$2"
      shift 2
      ;;
    -h|--hypothesis)
      HYPOTHESIS="$2"
      shift 2
      ;;
    -p|--prediction)
      PREDICTION="$2"
      shift 2
      ;;
    -f|--falsification)
      FALSIFICATION="$2"
      shift 2
      ;;
    -w|--weight)
      WEIGHT="$2"
      shift 2
      ;;
    --tags)
      TAGS="$2"
      shift 2
      ;;
    --expiry-sessions)
      EXPIRY_SESSIONS="$2"
      shift 2
      ;;
    --expiry-days)
      EXPIRY_DAYS="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

if [[ -z "$TYPE" || -z "$HYPOTHESIS" || -z "$PREDICTION" || -z "$FALSIFICATION" ]]; then
  echo "Error: Missing required arguments."
  echo "Usage: $0 --type <type> --hypothesis <hypothesis> --prediction <prediction> --falsification <falsification>"
  exit 1
fi

TYPE=$(echo "$TYPE" | tr '[:upper:]' '[:lower:]')
TYPE_PLURAL=""

case "$TYPE" in
  vacuole)
    TYPE_PLURAL="vacuoles"
    ;;
  chloroplast)
    TYPE_PLURAL="chloroplasts"
    ;;
  wall)
    TYPE_PLURAL="walls"
    ;;
  membrane)
    TYPE_PLURAL="membranes"
    ;;
  plasmodesmata)
    TYPE_PLURAL="plasmodesmata"
    ;;
  *)
    echo "Error: Invalid type. Must be one of: vacuole, chloroplast, wall, membrane, plasmodesmata."
    exit 2
    ;;
esac

# Generate slug: lowercase, spaces to dashes, remove special chars, truncate to 50 chars
SLUG=$(echo "$HYPOTHESIS" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9 ]//g' | sed 's/ /-/g' | cut -c1-50 | sed 's/-$//')
DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

DIR=".prism/cells/$TYPE_PLURAL"
mkdir -p "$DIR"

FILE_PATH="$DIR/$SLUG.md"

HYPOTHESIS_TRUNCATED=$(echo "$HYPOTHESIS" | cut -c1-60)
if [[ ${#HYPOTHESIS} -gt 60 ]]; then
  HYPOTHESIS_TRUNCATED="${HYPOTHESIS_TRUNCATED}..."
fi

# Convert tags to array format for YAML if not empty
TAGS_YAML="[]"
if [[ -n "$TAGS" ]]; then
  # split by comma, add quotes, join by comma
  IFS=',' read -ra TAG_ARRAY <<< "$TAGS"
  TAGS_YAML="["
  for i in "${!TAG_ARRAY[@]}"; do
    # trim whitespace
    TAG=$(echo "${TAG_ARRAY[$i]}" | xargs)
    if [[ $i -eq 0 ]]; then
      TAGS_YAML+="\"$TAG\""
    else
      TAGS_YAML+=", \"$TAG\""
    fi
  done
  TAGS_YAML+="]"
fi

cat > "$FILE_PATH" << EOF
---
type: $TYPE
hypothesis: "$HYPOTHESIS"
prediction: "$PREDICTION"
falsification: "$FALSIFICATION"
expiry_sessions: $EXPIRY_SESSIONS
expiry_days: $EXPIRY_DAYS
created: "$DATE"
impact_weight: $WEIGHT
tags: $TAGS_YAML
fitness:
  triggers: 0
  true_positives: 0
  false_positives: 0
  score: null
---
## ${TYPE^}: $HYPOTHESIS_TRUNCATED

$HYPOTHESIS

### Prediction
$PREDICTION

### Falsification Criteria
$FALSIFICATION
EOF

echo "Created: $FILE_PATH"
exit 0
