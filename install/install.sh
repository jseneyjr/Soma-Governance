#!/usr/bin/env bash
set -euo pipefail

# Unified Installer — soma
# Replaces install-gemini.sh, install-kiro.sh, install-copilot.sh
# Usage: bash install.sh [platform] [mode] [--dry-run] [--local]
#   platform: gemini (default) | kiro | copilot | claude
#   mode:     global (default) | project  (copilot only)
#   options:  --dry-run, -n, --local

# Symlink-safe resolution (Thorns fix #3)
PRG="${BASH_SOURCE[0]}"
while [ -h "$PRG" ]; do
  DIR="$(cd -P "$(dirname "$PRG")" && pwd)"
  PRG="$(readlink "$PRG")"
  [[ $PRG != /* ]] && PRG="$DIR/$PRG"
done
REPO_DIR="$(cd -P "$(dirname "$PRG")/.." && pwd)"

source "$REPO_DIR/enzymes/common.sh"

# Load config FIRST so soma.conf values are available
load_config "$REPO_DIR"

# Parse CLI flags & positional arguments
DRY_RUN=false
LOCAL_INSTALL=false
POSITIONAL_ARGS=()

for arg in "$@"; do
  case "$arg" in
    --dry-run|-n)
      DRY_RUN=true
      ;;
    --local)
      LOCAL_INSTALL=true
      ;;
    --hooks)
      INSTALL_GIT_HOOKS=true
      ;;
    *)
      POSITIONAL_ARGS+=("$arg")
      ;;
  esac
done
export DRY_RUN
export LOCAL_INSTALL

# CLI arg > soma.conf > default
SOMA_PLATFORM="${POSITIONAL_ARGS[0]:-$SOMA_PLATFORM}"
PLATFORM="$SOMA_PLATFORM"  # alias for use in case statement
MODE="${POSITIONAL_ARGS[1]:-global}"

validate_config
resolve_subset

# OS Detection & Home Resolution
DETECTED_OS="$(detect_os)"
RESOLVED_HOME="$(resolve_home "$DETECTED_OS")"

# ── Migration: .prism/ → .soma/ ──
# Auto-detect and migrate existing Prism installations
migrate_prism_to_soma() {
  local target_dir="$1"
  local old_dir="$target_dir/.prism"
  local new_dir="$target_dir/.soma"
  
  if [ -d "$old_dir" ] && [ ! -d "$new_dir" ]; then
    log_info "Detected legacy .prism/ directory — migrating to .soma/"
    if [ "$DRY_RUN" = "true" ]; then
      log_info "[DRY-RUN] Would rename $old_dir → $new_dir"
    else
      mv "$old_dir" "$new_dir"
      # Leave a symlink for backward compatibility during transition
      ln -sf ".soma" "$old_dir" 2>/dev/null || true
      log_info "✅ Migrated .prism/ → .soma/"
    fi
  elif [ -d "$old_dir" ] && [ -d "$new_dir" ]; then
    log_warn "Both .prism/ and .soma/ exist. Using .soma/ — remove .prism/ manually if no longer needed."
  fi
}

# Run migration for global home and local project
migrate_prism_to_soma "$RESOLVED_HOME"
if [ "$LOCAL_INSTALL" = "true" ]; then
  migrate_prism_to_soma "$(pwd)"
fi

write_manifest() {
  if [ "$DRY_RUN" = "true" ]; then return 0; fi
  local manifest_dir="$RESOLVED_HOME/.soma"
  local scope="global"
  if [ "$LOCAL_INSTALL" = "true" ] && [ "$PLATFORM" = "gemini" ]; then
    manifest_dir="$(pwd)/.soma"
    scope="local"
  fi
  mkdir -p "$manifest_dir"
  local target_json="$manifest_dir/manifest.json"
  
  local t_repo=${TEAM_REPO:-null}
  [ "$t_repo" != "null" ] && t_repo="\"$t_repo\""
  
  local o_repo=${ORG_REPO:-null}
  [ "$o_repo" != "null" ] && o_repo="\"$o_repo\""
  
  local m_repo=${METRICS_REPO:-null}
  [ "$m_repo" != "null" ] && m_repo="\"$m_repo\""
  
  local files_arr="[]"
  local skills_arr="[]"
  local hooks_arr="[]"
  
  if [ -n "${TARGET_RULES:-}" ] && [ -d "$TARGET_RULES" ]; then
    files_arr="[$(find "$TARGET_RULES" -maxdepth 1 -type f -name "*.md" 2>/dev/null | awk '{print "\""$0"\""}' | tr '\n' ',' | sed 's/,$//')]"
  elif [ -n "${TARGET_DIR:-}" ] && [ -d "$TARGET_DIR" ]; then
    files_arr="[$(find "$TARGET_DIR" -maxdepth 1 -type f -name "*.instructions.md" 2>/dev/null | awk '{print "\""$0"\""}' | tr '\n' ',' | sed 's/,$//')]"
  elif [ -n "${TARGET_FILE:-}" ] && [ -f "$TARGET_FILE" ]; then
    files_arr="[\"$TARGET_FILE\"]"
  fi
  
  if [ -n "${TARGET_SKILLS:-}" ] && [ -d "$TARGET_SKILLS" ]; then
    skills_arr="[$(find "$TARGET_SKILLS" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | awk '{print "\""$0"\""}' | tr '\n' ',' | sed 's/,$//')]"
  fi
  
  if [ -n "${TARGET_HOOKS:-}" ] && [ -d "$TARGET_HOOKS" ]; then
    hooks_arr="[$(find "$TARGET_HOOKS" -maxdepth 1 -type f 2>/dev/null | awk '{print "\""$0"\""}' | tr '\n' ',' | sed 's/,$//')]"
  fi
  
  local ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local backup_path=${BACKUP_DIR:-null}
  [ "$backup_path" != "null" ] && backup_path="\"$backup_path\""
  
  local version
  version=$(cat "$REPO_DIR/VERSION" 2>/dev/null || echo "unknown")
  
  cat > "$target_json" <<EOF
{
  "version": "$version",
  "installed_at": "$ts",
  "platform": "$PLATFORM",
  "scope": "$scope", 
  "rules_subset": "$RULES_SUBSET",
  "source_repo": "$REPO_DIR",
  "team_repo": $t_repo,
  "org_repo": $o_repo,
  "metrics_repo": $m_repo,
  "backup_dir": $backup_path,
  "files": $files_arr,
  "organs": $skills_arr,
  "hooks": $hooks_arr
}
EOF
}

SOURCE_DIR="$REPO_DIR/genome"
SKILLS_SOURCE="$REPO_DIR/organs"

echo "Installing Soma for $PLATFORM (OS: $DETECTED_OS, Kernel: $(uname -s))..."
echo "  Source: $(normalize_path "$SOURCE_DIR")"
echo "  Config: TEAM_SIZE=$TEAM_SIZE GIT_STRATEGY=$GIT_STRATEGY RULES_SUBSET=$RULES_SUBSET"
[ "$DRY_RUN" = "true" ] && echo "  Mode:   DRY-RUN (no files will be modified)"
echo ""

BACKUP_TS=$(date -u +"%Y-%m-%dT%H-%M-%S")
BACKUP_DIR="$RESOLVED_HOME/.soma/backup/$BACKUP_TS"

if [ "$DRY_RUN" = "false" ]; then
  # Keep only the most recent backup — safely recreate
  rm -rf "$RESOLVED_HOME/.soma/backup"
  mkdir -p "$RESOLVED_HOME/.soma/backup"
  mkdir -p "$BACKUP_DIR"
  
  case "$PLATFORM" in
    gemini)
      if [ "$LOCAL_INSTALL" = "true" ]; then
        [ -d "$(pwd)/.soma/genome" ] && cp -r "$(pwd)/.soma/genome" "$BACKUP_DIR/genome"
        [ -d "$(pwd)/.soma/organs" ] && cp -r "$(pwd)/.soma/organs" "$BACKUP_DIR/organs"
        [ -d "$(pwd)/.soma/plugins/governance" ] && cp -r "$(pwd)/.soma/plugins/governance" "$BACKUP_DIR/governance"
        [ -d "$(pwd)/.soma/cells" ] && cp -r "$(pwd)/.soma/cells" "$BACKUP_DIR/cells"
      else
        [ -d "$RESOLVED_HOME/.gemini/config/rules" ] && cp -r "$RESOLVED_HOME/.gemini/config/rules" "$BACKUP_DIR/genome"
        [ -d "$RESOLVED_HOME/.gemini/config/skills" ] && cp -r "$RESOLVED_HOME/.gemini/config/skills" "$BACKUP_DIR/organs"
        [ -d "$RESOLVED_HOME/.gemini/config/plugins/governance" ] && cp -r "$RESOLVED_HOME/.gemini/config/plugins/governance" "$BACKUP_DIR/governance"
      fi
      ;;
    kiro)
      [ -d "$RESOLVED_HOME/.kiro/steering" ] && cp -r "$RESOLVED_HOME/.kiro/steering" "$BACKUP_DIR/genome"
      [ -d "$RESOLVED_HOME/.kiro/skills" ] && cp -r "$RESOLVED_HOME/.kiro/skills" "$BACKUP_DIR/organs"
      [ -d "$RESOLVED_HOME/.kiro/hooks" ] && cp -r "$RESOLVED_HOME/.kiro/hooks" "$BACKUP_DIR/hooks"
      ;;
    copilot)
      [ -f "$RESOLVED_HOME/copilot-instructions.md" ] && cp "$RESOLVED_HOME/copilot-instructions.md" "$BACKUP_DIR/"
      ;;
    claude)
      if [ "$LOCAL_INSTALL" = "true" ]; then
        [ -f "$(pwd)/CLAUDE.md" ] && cp "$(pwd)/CLAUDE.md" "$BACKUP_DIR/"
        [ -f "$(pwd)/.mcp.json" ] && cp "$(pwd)/.mcp.json" "$BACKUP_DIR/"
      else
        [ -f "$RESOLVED_HOME/.claude/CLAUDE.md" ] && cp "$RESOLVED_HOME/.claude/CLAUDE.md" "$BACKUP_DIR/"
      fi
      ;;
  esac
fi

case "$PLATFORM" in
  gemini)
    if [ "$LOCAL_INSTALL" = "true" ]; then
      TARGET_RULES="$(pwd)/.soma/rules"
      TARGET_SKILLS="$(pwd)/.soma/skills"
      TARGET_HOOKS="$(pwd)/.soma/plugins/governance"
    else
      TARGET_RULES="$RESOLVED_HOME/.gemini/config/rules"
      TARGET_SKILLS="$RESOLVED_HOME/.gemini/config/skills"
      TARGET_HOOKS="$RESOLVED_HOME/.gemini/config/plugins/governance"
    fi
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
        rm -f "$TARGET_RULES/$name"  # Remove any existing symlink before copy
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
      write_manifest
      echo "Done! Installed $count rules, $skill_count skills"
      if [ "$LOCAL_INSTALL" = "true" ]; then
        echo "Installed locally to $(pwd)/.soma/ — these rules apply only to this project."
      else
        echo "These will take effect on your next Gemini conversation."
      fi
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
      write_manifest
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
        write_manifest
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
        echo "> Auto-generated from soma. Do not edit directly." >> "$TARGET_FILE"
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
        write_manifest
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

  claude)
    if [ "$LOCAL_INSTALL" = "true" ]; then
      TARGET_DIR="$(pwd)"
      TARGET_FILE="$TARGET_DIR/CLAUDE.md"
      MCP_FILE="$TARGET_DIR/.mcp.json"
    else
      TARGET_DIR="$RESOLVED_HOME/.claude"
      TARGET_FILE="$TARGET_DIR/CLAUDE.md"
      [ "$DRY_RUN" = "true" ] || mkdir -p "$TARGET_DIR"
    fi

    echo "  Target: $(normalize_path "$TARGET_FILE")"
    if [ "$DRY_RUN" = "false" ]; then
      backup_file "$TARGET_FILE"
      echo "# Soma Governance Rules" > "$TARGET_FILE"
      echo "" >> "$TARGET_FILE"
      echo "> Auto-generated by Soma. Do not edit directly." >> "$TARGET_FILE"
      echo "" >> "$TARGET_FILE"
    fi

    count=0; skipped=0; skill_count=0
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

    # Count skills for tracking purposes
    if [ -d "$SKILLS_SOURCE" ]; then
      for skill in "$SKILLS_SOURCE"/*/; do
        skill_count=$((skill_count + 1))
      done
    fi

    if [ "$LOCAL_INSTALL" = "true" ]; then
      if [ "$DRY_RUN" = "true" ]; then
        log_info "[dry-run] would create/update .mcp.json at $(normalize_path "$MCP_FILE")"
      else
        backup_file "$MCP_FILE"
        echo '{"mcpServers": {"soma": {"command": "python3", "args": ["-m", "soma_mcp"]}}}' > "$MCP_FILE"
        log_info "created .mcp.json"
      fi
    fi

    echo ""
    if [ "$DRY_RUN" = "true" ]; then
      echo "Dry-run complete. Would merge $count rules into $(normalize_path "$TARGET_FILE")"
    else
      write_manifest
      echo "Done! All rules merged into $(normalize_path "$TARGET_FILE") ($skill_count skills tracked)"
      if [ "$LOCAL_INSTALL" = "true" ]; then
        echo "Created .mcp.json for local MCP server."
      else
        echo "For global mode, run 'claude mcp add soma python3 -m soma_mcp' manually."
        echo "Note: Global hooks must be configured in ~/.claude/settings.json"
      fi
    fi
    if [ "$skipped" -gt 0 ]; then
      echo "  ($skipped rules skipped — not in $RULES_SUBSET subset)"
    fi
    ;;

  *)
    log_error "Unknown platform: $PLATFORM (expected: gemini|kiro|copilot)"
    exit 1
    ;;
esac

if [ "${INSTALL_GIT_HOOKS:-false}" = "true" ]; then
  if [ -d ".git/hooks" ]; then
    cp "$REPO_DIR/install/hooks/pre-commit" ".git/hooks/pre-commit"
    chmod +x ".git/hooks/pre-commit"
    echo "Installed git pre-commit hook."
  else
    echo "No .git/hooks directory found, skipping pre-commit hook installation."
  fi
fi
