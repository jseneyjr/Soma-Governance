#!/usr/bin/env bash
set -euo pipefail

# Unified Installer — prism-ai-steering
# Replaces install-gemini.sh, install-kiro.sh, install-copilot.sh
# Usage: bash install.sh [platform] [mode] [--dry-run]
#   platform: gemini (default) | kiro | copilot
#   mode:     global (default) | project  (copilot only)
#   options:  --dry-run, -n

# Symlink-safe resolution (Thorns fix #3)
PRG="${BASH_SOURCE[0]}"
while [ -h "$PRG" ]; do
  DIR="$(cd -P "$(dirname "$PRG")" && pwd)"
  PRG="$(readlink "$PRG")"
  [[ $PRG != /* ]] && PRG="$DIR/$PRG"
done
REPO_DIR="$(cd -P "$(dirname "$PRG")" && pwd)"

source "$REPO_DIR/scripts/common.sh"

# Load config FIRST so steering.conf values are available
load_config "$REPO_DIR"

# Parse CLI flags & positional arguments
DRY_RUN=false
POSITIONAL_ARGS=()

for arg in "$@"; do
  case "$arg" in
    --dry-run|-n)
      DRY_RUN=true
      ;;
    *)
      POSITIONAL_ARGS+=("$arg")
      ;;
  esac
done
export DRY_RUN

# CLI arg > steering.conf > default
STEERING_PLATFORM="${POSITIONAL_ARGS[0]:-$STEERING_PLATFORM}"
PLATFORM="$STEERING_PLATFORM"  # alias for use in case statement
MODE="${POSITIONAL_ARGS[1]:-global}"

validate_config
resolve_subset

# OS Detection & Home Resolution
DETECTED_OS="$(detect_os)"
RESOLVED_HOME="$(resolve_home "$DETECTED_OS")"

SOURCE_DIR="$REPO_DIR/rules"
SKILLS_SOURCE="$REPO_DIR/skills"

echo "Installing steering rules for $PLATFORM (OS: $DETECTED_OS, Kernel: $(uname -s))..."
echo "  Source: $(normalize_path "$SOURCE_DIR")"
echo "  Config: TEAM_SIZE=$TEAM_SIZE GIT_STRATEGY=$GIT_STRATEGY RULES_SUBSET=$RULES_SUBSET"
[ "$DRY_RUN" = "true" ] && echo "  Mode:   DRY-RUN (no files will be modified)"
echo ""

case "$PLATFORM" in
  gemini)
    TARGET_RULES="$RESOLVED_HOME/.gemini/config/rules"
    TARGET_SKILLS="$RESOLVED_HOME/.gemini/config/skills"
    TARGET_HOOKS="$RESOLVED_HOME/.gemini/config/plugins/governance"
    [ "$DRY_RUN" = "true" ] || mkdir -p "$TARGET_RULES" "$TARGET_SKILLS"

    # Install rules
    count=0; skipped=0
    for rule in "$SOURCE_DIR"/*.md; do
      name="$(basename "$rule")"
      if ! should_install "$name"; then
        log_skip "$name (not in $RULES_SUBSET subset)"
        skipped=$((skipped + 1))
        continue
      fi
      if [ "$DRY_RUN" = "true" ]; then
        log_info "[dry-run] would install $name -> $(normalize_path "$TARGET_RULES/$name")"
      else
        backup_file "$TARGET_RULES/$name"
        cp -- "$rule" "$TARGET_RULES/$name"
        log_info "$name"
      fi
      count=$((count + 1))
    done

    # Install skills
    skill_count=0
    if [ -d "$SKILLS_SOURCE" ]; then
      for skill in "$SKILLS_SOURCE"/*/; do
        skill_name="$(basename "$skill")"
        if [ "$DRY_RUN" = "true" ]; then
          log_info "[dry-run] would install skill/$skill_name -> $(normalize_path "$TARGET_SKILLS/$skill_name")"
        else
          backup_dir "$TARGET_SKILLS/$skill_name"
          # Remove existing to prevent nesting
          [ -d "$TARGET_SKILLS/$skill_name" ] && rm -rf -- "$TARGET_SKILLS/$skill_name"
          cp -r -- "$skill" "$TARGET_SKILLS/$skill_name"
          log_info "skill/$skill_name"
        fi
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
    if [ "$DRY_RUN" = "true" ]; then
      echo "Dry-run complete. Would install $count rules, $skill_count skills to $(normalize_path "$TARGET_RULES")"
    else
      echo "Done! Installed $count rules, $skill_count skills"
      echo "These will take effect on your next Gemini conversation."
    fi
    if [ "$skipped" -gt 0 ]; then
      echo "  ($skipped rules skipped — not in $RULES_SUBSET subset)"
    fi
    ;;

  kiro)
    TARGET_RULES="$RESOLVED_HOME/.kiro/steering"
    TARGET_SKILLS="$RESOLVED_HOME/.kiro/skills"
    TARGET_HOOKS="$RESOLVED_HOME/.kiro/hooks"
    [ "$DRY_RUN" = "true" ] || mkdir -p "$TARGET_RULES" "$TARGET_SKILLS"

    count=0; skipped=0
    for rule in "$SOURCE_DIR"/*.md; do
      name="$(basename "$rule")"
      if ! should_install "$name"; then
        log_skip "$name (not in $RULES_SUBSET subset)"
        skipped=$((skipped + 1))
        continue
      fi
      if [ "$DRY_RUN" = "true" ]; then
        log_info "[dry-run] would install $name (converted syntax) -> $(normalize_path "$TARGET_RULES/$name")"
      else
        backup_file "$TARGET_RULES/$name"
        # Convert trigger syntax to Kiro inclusion syntax
        sed -e 's/^trigger: always_on$/inclusion: always/' \
            -e 's/^trigger: model_decision$/inclusion: manual/' \
            "$rule" > "$TARGET_RULES/$name"
        log_info "$name"
      fi
      count=$((count + 1))
    done

    # Install skills (parity with Gemini)
    skill_count=0
    if [ -d "$SKILLS_SOURCE" ]; then
      for skill in "$SKILLS_SOURCE"/*/; do
        skill_name="$(basename "$skill")"
        if [ "$DRY_RUN" = "true" ]; then
          log_info "[dry-run] would install skill/$skill_name -> $(normalize_path "$TARGET_SKILLS/$skill_name")"
        else
          backup_dir "$TARGET_SKILLS/$skill_name"
          # Remove existing to prevent nesting
          [ -d "$TARGET_SKILLS/$skill_name" ] && rm -rf -- "$TARGET_SKILLS/$skill_name"
          cp -r -- "$skill" "$TARGET_SKILLS/$skill_name"
          log_info "skill/$skill_name"
        fi
        skill_count=$((skill_count + 1))
      done
    fi

    # Team overrides (parity with Gemini)
    apply_team_overrides "$TARGET_RULES"

    # Hooks (Kiro uses individual .kiro.hook files, not hooks.json)
    if [ "$ENABLE_HOOKS" = "true" ]; then
      install_hooks "$REPO_DIR" "$TARGET_HOOKS"
    fi

    echo ""
    if [ "$DRY_RUN" = "true" ]; then
      echo "Dry-run complete. Would install $count rules, $skill_count skills to $(normalize_path "$TARGET_RULES")"
    else
      echo "Done! Installed $count rules, $skill_count skills to $(normalize_path "$TARGET_RULES")"
      echo "Rules with 'inclusion: always' are active on every interaction."
      echo "Rules with 'inclusion: manual' can be referenced via #rulename."
    fi
    if [ "$skipped" -gt 0 ]; then
      echo "  ($skipped rules skipped — not in $RULES_SUBSET subset)"
    fi
    ;;

  copilot)
    if [ "$MODE" = "project" ]; then
      TARGET_DIR=".github/instructions"
      echo "  Target: $(normalize_path "$TARGET_DIR")"
      [ "$DRY_RUN" = "true" ] || mkdir -p "$TARGET_DIR"

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
        if [ "$DRY_RUN" = "true" ]; then
          log_info "[dry-run] would install ${name}.instructions.md -> $(normalize_path "$target")"
        else
          backup_file "$target"
          strip_frontmatter < "$rule" > "$target"
          log_info "${name}.instructions.md"
        fi
        count=$((count + 1))
      done

      # Team overrides for Copilot project mode
      apply_team_overrides "$TARGET_DIR"

      echo ""
      if [ "$DRY_RUN" = "true" ]; then
        echo "Dry-run complete. Would install $count instruction files to $(normalize_path "$TARGET_DIR")"
      else
        echo "Done! Installed $count instruction files to $(normalize_path "$TARGET_DIR")"
        echo "Commit .github/instructions/ to share with your team."
      fi
      if [ "$skipped" -gt 0 ]; then
        echo "  ($skipped rules skipped — not in $RULES_SUBSET subset)"
      fi

    elif [ "$MODE" = "global" ]; then
      TARGET_FILE="$RESOLVED_HOME/copilot-instructions.md"

      echo "  Target: $(normalize_path "$TARGET_FILE")"
      if [ "$DRY_RUN" = "false" ]; then
        backup_file "$TARGET_FILE"

        echo "# Copilot Global Instructions" > "$TARGET_FILE"
        echo "" >> "$TARGET_FILE"
        echo "> Auto-generated from prism-ai-steering. Do not edit directly." >> "$TARGET_FILE"
        echo "" >> "$TARGET_FILE"
      fi

      count=0; skipped=0
      for rule in "$SOURCE_DIR"/*.md; do
        filename="$(basename "$rule")"
        if ! should_install "$filename"; then
          log_skip "$filename (not in $RULES_SUBSET subset)"
          skipped=$((skipped + 1))
          continue
        fi
        if [ "$DRY_RUN" = "true" ]; then
          log_info "[dry-run] would merge $filename into $(normalize_path "$TARGET_FILE")"
        else
          echo "---" >> "$TARGET_FILE"
          echo "" >> "$TARGET_FILE"
          strip_frontmatter < "$rule" >> "$TARGET_FILE"
          echo "" >> "$TARGET_FILE"
          log_info "$filename"
        fi
        count=$((count + 1))
      done

      echo ""
      if [ "$DRY_RUN" = "true" ]; then
        echo "Dry-run complete. Would merge $count rules into $(normalize_path "$TARGET_FILE")"
      else
        echo "Done! All rules merged into $(normalize_path "$TARGET_FILE")"
        echo "Enable 'Custom Instructions' in your IDE's Copilot settings."
      fi
      if [ "$skipped" -gt 0 ]; then
        echo "  ($skipped rules skipped — not in $RULES_SUBSET subset)"
      fi
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
