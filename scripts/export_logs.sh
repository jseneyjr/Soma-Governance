#!/usr/bin/env bash
set -euo pipefail

# Configuration
BRAIN_DIR="${HOME}/.gemini/antigravity/brain"
REPO_DIR="${HOME}/.gemini/antigravity/scratch/ai-conversation-logs"
MIN_STEPS=50

echo "=== Conversation Log Export ==="
echo "Timestamp: $(date -Iseconds)"

cd "$REPO_DIR"

# Non-blocking lock — skip if another export is already running
exec 200>"$REPO_DIR/.export.lock"
flock -n 200 || { echo "Export already running. Skipping."; exit 0; }

# Find all conversations with transcripts
find "$BRAIN_DIR" -maxdepth 5 -name "transcript.jsonl" -path "*/.system_generated/logs/*" 2>/dev/null | while read -r transcript; do
    conv_id=$(echo "$transcript" | grep -oP 'brain/\K[a-f0-9-]+')
    step_count=$(wc -l < "$transcript")

    # Skip tiny conversations
    if [ "$step_count" -lt "$MIN_STEPS" ]; then
        continue
    fi

    # Detect primary vs subagent (primary has USER_INPUT steps)
    is_primary=$(head -20 "$transcript" | grep -c '"type":"USER_INPUT"' || true)

    # Create conversation directory
    conv_dir="$REPO_DIR/conversations/$conv_id"
    mkdir -p "$conv_dir"

    # Copy transcript (only if changed)
    if ! cmp -s "$transcript" "$conv_dir/transcript.jsonl" 2>/dev/null; then
        cp "$transcript" "$conv_dir/transcript.jsonl"
        echo "Updated: $conv_id ($step_count steps, primary=$is_primary)"
    fi

    # Generate metadata
    cat > "$conv_dir/metadata.json" << EOF
{
    "conversation_id": "$conv_id",
    "step_count": $step_count,
    "is_primary": $([ "$is_primary" -gt 0 ] && echo "true" || echo "false"),
    "last_exported": "$(date -Iseconds)",
    "transcript_bytes": $(wc -c < "$transcript")
}
EOF
done

# Generate index
echo "[" > "$REPO_DIR/conversations/index.json"
first=true
for meta in "$REPO_DIR"/conversations/*/metadata.json; do
    [ -f "$meta" ] || continue
    if [ "$first" = true ]; then
        first=false
    else
        echo "," >> "$REPO_DIR/conversations/index.json"
    fi
    cat "$meta" >> "$REPO_DIR/conversations/index.json"
done
echo "]" >> "$REPO_DIR/conversations/index.json"

# Secret scrubbing (basic patterns)
find "$REPO_DIR/conversations" -name "transcript.jsonl" -exec \
    sed -i \
        -e 's/GEMINI_API_KEY=[^ ]*/GEMINI_API_KEY=REDACTED/g' \
        -e 's/sk-[a-zA-Z0-9]\{20,\}/sk-REDACTED/g' \
        -e 's/ghp_[a-zA-Z0-9]\{36\}/ghp_REDACTED/g' \
        -e 's/Bearer [a-zA-Z0-9._-]\{20,\}/Bearer REDACTED/g' \
    {} \;

# Git commit and push if changes
if [ -n "$(git status --porcelain)" ]; then
    git add .
    git commit -m "Log export: $(date -Iseconds) | $(find conversations -name 'metadata.json' | wc -l) conversations"
    git push origin master
    echo "Pushed to GitHub."
else
    echo "No changes to push."
fi

echo "Export complete."
