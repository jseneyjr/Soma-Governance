#!/usr/bin/env bash
set -euo pipefail

# Unified Installer — ai-steering-rules
# Replaces install-gemini.sh, install-kiro.sh, install-copilot.sh
# Usage: bash install.sh [platform] [mode]
#   platform: gemini (default) | kiro | copilot
#   mode:     global (default) | project  (copilot only)

# Symlink-safe resolution (Thorns fix #3)
PRG="${BASH_SOURCE[0]}"
while [ -h "$PRG" ]; do
  DIR="$(cd -P "$(dirname "$PRG")" && pwd)"
  PRG="$(readlink "$PRG")"
  [[ $PRG != /* ]] && PRG="$DIR/$PRG"
done
REPO_DIR="$(cd -P "$(dirname "$PRG")" && pwd)"

source "$REPO_DIR/scripts/common.sh"

PLATFORM="${1:-${STEERING_PLATFORM:-gemini}}"
MODE="${2:-global}"  # Only used by copilot

load_config "$REPO_DIR"
# Override platform if passed as arg
STEERING_PLATFORM="$PLATFORM"
validate_config
resolve_subset

SOURCE_DIR="$REPO_DIR/rules"
SKILLS_SOURCE="$REPO_DIR/skills"

echo "Installing steering rules for $PLATFORM..."
echo "  Source: $SOURCE_DIR"
echo "  Config: TEAM_SIZE=$TEAM_SIZE GIT_STRATEGY=$GIT_STRATEGY RULES_SUBSET=$RULES_SUBSET"
echo ""

case "$PLATFORM" in
  gemini)
    TARGET_RULES="$HOME/.gemini/config/rules"
    TARGET_SKILLS="$HOME/.gemini/config/skills"
    TARGET_HOOKS="$HOME/.gemini/config/plugins/governance"
    mkdir -p "$TARGET_RULES" "$TARGET_SKILLS"

    # Install rules
    count=0; skipped=0
    for rule in "$SOURCE_DIR"/*.md; do
      name="$(basename "$rule")"
      if ! should_install "$name"; then
        log_skip "$name (not in $RULES_SUBSET subset)"
        skipped=$((skipped + 1))
        continue
      fi
      backup_file "$TARGET_RULES/$name"
      cp -- "$rule" "$TARGET_RULES/$name"
      log_info "$name"
      count=$((count + 1))
    done

    # Install skills
    skill_count=0
    if [ -d "$SKILLS_SOURCE" ]; then
      for skill in "$SKILLS_SOURCE"/*/; do
        skill_name="$(basename "$skill")"
        backup_dir "$TARGET_SKILLS/$skill_name"
        # Remove existing to prevent nesting
        [ -d "$TARGET_SKILLS/$skill_name" ] && rm -rf -- "$TARGET_SKILLS/$skill_name"
        cp -r -- "$skill" "$TARGET_SKILLS/$skill_name"
        log_info "skill/$skill_name"
        skill_count=$((skill_count + 1))
      done
    fi

    # Team overrides
    apply_team_overrides "$TARGET_RULES"

    # Hooks
    if [ "$ENABLE_HOOKS" = "true" ]; then
      install_hooks "$REPO_DIR" "$TARGET_HOOKS"
    fi

    echo ""
    echo "Done! Installed $count rules, $skill_count skills"
    [ "$skipped" -gt 0 ] && echo "  ($skipped rules skipped — not in $RULES_SUBSET subset)"
    echo "These will take effect on your next Gemini conversation."
    ;;

  kiro)
    TARGET_RULES="$HOME/.kiro/steering"
    mkdir -p "$TARGET_RULES"

    count=0; skipped=0
    for rule in "$SOURCE_DIR"/*.md; do
      name="$(basename "$rule")"
      if ! should_install "$name"; then
        log_skip "$name (not in $RULES_SUBSET subset)"
        skipped=$((skipped + 1))
        continue
      fi
      backup_file "$TARGET_RULES/$name"
      # Convert trigger syntax to Kiro inclusion syntax
      sed -e 's/^trigger: always_on$/inclusion: always/' \
          -e 's/^trigger: model_decision$/inclusion: manual/' \
          "$rule" > "$TARGET_RULES/$name"
      log_info "$name"
      count=$((count + 1))
    done

    # Team overrides (parity with Gemini)
    apply_team_overrides "$TARGET_RULES"

    echo ""
    echo "Done! Installed $count rules to $TARGET_RULES"
    [ "$skipped" -gt 0 ] && echo "  ($skipped rules skipped — not in $RULES_SUBSET subset)"
    echo "Rules with 'inclusion: always' are active on every interaction."
    echo "Rules with 'inclusion: manual' can be referenced via #rulename."
    ;;

  copilot)
    if [ "$MODE" = "project" ]; then
      TARGET_DIR=".github/instructions"
      echo "  Target: $TARGET_DIR"
      mkdir -p "$TARGET_DIR"

      count=0; skipped=0
      for rule in "$SOURCE_DIR"/*.md; do
        filename="$(basename "$rule")"
        if ! should_install "$filename"; then
          log_skip "$filename (not in $RULES_SUBSET subset)"
          skipped=$((skipped + 1))
          continue
        fi
        name="$(basename "$rule" .md)"
        target="$TARGET_DIR/${name}.instructions.md"
        backup_file "$target"
        strip_frontmatter < "$rule" > "$target"
        log_info "${name}.instructions.md"
        count=$((count + 1))
      done

      # Team overrides for Copilot project mode
      apply_team_overrides "$TARGET_DIR"

      echo ""
      echo "Done! Installed $count instruction files to $TARGET_DIR"
      echo "Commit .github/instructions/ to share with your team."

    elif [ "$MODE" = "global" ]; then
      # Detect target file path
      # Thorns fix: WSL detection via /proc/version
      if [ -f /proc/version ] && grep -qi microsoft /proc/version 2>/dev/null; then
        # WSL: write to Windows user profile
        win_home="$(wslpath "$(cmd.exe /C 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r')" 2>/dev/null || echo "$HOME")"
        TARGET_FILE="$win_home/copilot-instructions.md"
      elif [[ "${OSTYPE:-}" == msys* || "${OSTYPE:-}" == cygwin* ]]; then
        TARGET_FILE="${USERPROFILE:-$HOME}/copilot-instructions.md"
      else
        TARGET_FILE="$HOME/copilot-instructions.md"
      fi

      echo "  Target: $TARGET_FILE"
      backup_file "$TARGET_FILE"

      echo "# Copilot Global Instructions" > "$TARGET_FILE"
      echo "" >> "$TARGET_FILE"
      echo "> Auto-generated from ai-steering-rules. Do not edit directly." >> "$TARGET_FILE"
      echo "" >> "$TARGET_FILE"

      count=0; skipped=0
      for rule in "$SOURCE_DIR"/*.md; do
        filename="$(basename "$rule")"
        if ! should_install "$filename"; then
          log_skip "$filename (not in $RULES_SUBSET subset)"
          skipped=$((skipped + 1))
          continue
        fi
        echo "---" >> "$TARGET_FILE"
        echo "" >> "$TARGET_FILE"
        strip_frontmatter < "$rule" >> "$TARGET_FILE"
        echo "" >> "$TARGET_FILE"
        log_info "$filename"
        count=$((count + 1))
      done

      echo ""
      echo "Done! All rules merged into $TARGET_FILE"
      echo "Enable 'Custom Instructions' in your IDE's Copilot settings."
    else
      log_error "Unknown mode: $MODE (expected: global|project)"
      exit 1
    fi
    ;;

  *)
    log_error "Unknown platform: $PLATFORM (expected: gemini|kiro|copilot)"
    exit 1
    ;;
esac
