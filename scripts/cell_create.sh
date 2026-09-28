#!/bin/bash
# cell_create.sh: Programmatic Cell Creation for Prism AI Steering
# Usage: bash scripts/cell_create.sh --type <type> --hypothesis <hypothesis> --prediction <prediction> --falsification <falsification> [options]

# Source common.sh if it exists (for compatibility with existing structure)
if [[ -f "scripts/common.sh" ]]; then
  source "scripts/common.sh"
fi

# Default values
# Walk up from CWD to find project root with .prism/cells/
if [ -n "${PRISM_ROOT:-}" ] && [ -d "$PRISM_ROOT" ]; then
  REPO_DIR="$PRISM_ROOT"
else
  _d="$(pwd)"
  REPO_DIR="$_d"
  while [ "$_d" != "/" ]; do
    if [[ "$_d" == */vendor/* ]] || [[ "$_d" == */vendor ]]; then
      _d="$(dirname "$_d")"
      continue
    fi
    if [ -d "$_d/.prism/cells" ]; then
      REPO_DIR="$_d"
      break
    fi
    _d="$(dirname "$_d")"
  done
fi

TYPE=""
HYPOTHESIS=""
PREDICTION=""
FALSIFICATION=""
WEIGHT="1.0"
TAGS=""
EXPIRY_SESSIONS="15"
EXPIRY_DAYS="60"
RESPONSE_TYPE=""
MINIMUM_MODE=""
ACTIVATION=""
EFFECTOR=false
MEMORY=false
DECAY_TO_YAML=""
TARGET_PATHS=""

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
    --effector)
      EFFECTOR=true
      shift
      ;;
    --memory)
      MEMORY=true
      shift
      ;;
    --target-paths)
      TARGET_PATHS="$2"
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

if [[ "$EFFECTOR" == "true" && "$MEMORY" == "true" ]]; then
  echo "Error: --effector and --memory are mutually exclusive."
  exit 1
fi

if [[ "$EFFECTOR" == "true" ]]; then
  EXPIRY_SESSIONS=3
  WEIGHT="3.0"
  RESPONSE_TYPE="effector"
  MINIMUM_MODE="tempest"
  DECAY_TO_YAML="decay_to:
  type: membrane
  impact_weight: 1.0
  minimum_mode: trident
  response_type: memory
  activation: dormant"
fi

if [[ "$MEMORY" == "true" ]]; then
  EXPIRY_SESSIONS="null"
  WEIGHT="1.5"
  RESPONSE_TYPE="memory"
  MINIMUM_MODE="maelstrom"
  ACTIVATION="dormant"
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

DIR="$REPO_DIR/.prism/cells/$TYPE_PLURAL"
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

# Convert target_paths to array format for YAML if not empty
TARGET_PATHS_YAML="[]"
if [[ -n "$TARGET_PATHS" ]]; then
  # split by comma, add quotes, join by comma
  IFS=',' read -ra TP_ARRAY <<< "$TARGET_PATHS"
  TARGET_PATHS_YAML="["
  for i in "${!TP_ARRAY[@]}"; do
    # trim whitespace
    TP=$(echo "${TP_ARRAY[$i]}" | xargs)
    if [[ $i -eq 0 ]]; then
      TARGET_PATHS_YAML+="\"$TP\""
    else
      TARGET_PATHS_YAML+=", \"$TP\""
    fi
  done
  TARGET_PATHS_YAML+="]"
fi

# Build optional fields
OPTIONAL_YAML=""
if [[ -n "$RESPONSE_TYPE" ]]; then
  OPTIONAL_YAML+="response_type: $RESPONSE_TYPE"$'\n'
fi
if [[ -n "$MINIMUM_MODE" ]]; then
  OPTIONAL_YAML+="minimum_mode: $MINIMUM_MODE"$'\n'
fi
if [[ -n "$ACTIVATION" ]]; then
  OPTIONAL_YAML+="activation: $ACTIVATION"$'\n'
fi
if [[ -n "$DECAY_TO_YAML" ]]; then
  OPTIONAL_YAML+="$DECAY_TO_YAML"$'\n'
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
target_paths: $TARGET_PATHS_YAML
lineage:
  parent_id: null
  created_by: "manual"
  generation: 0
  siblings: []
${OPTIONAL_YAML}fitness:
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
