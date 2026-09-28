# Soma — Makefile
# Reads soma.conf for team/workflow configuration.
# Without soma.conf, all defaults apply (solo/trunk/all).

-include soma.conf

# Defaults (namespaced to avoid env collisions)
SOMA_PLATFORM ?= gemini
TEAM_SIZE         ?= solo
GIT_STRATEGY      ?= trunk
APPROVAL_CHAIN    ?= none
RULES_SUBSET      ?= all
ENABLE_HOOKS      ?= true

export TEAM_SIZE GIT_STRATEGY APPROVAL_CHAIN
export RULES_SUBSET ENABLE_HOOKS SOMA_PLATFORM

.PHONY: help info install install-windows \
        uninstall doctor validate update status test

help: ## Show available targets
	@echo "Soma — Adaptive Governance"
	@echo ""
	@echo "Workflow:"
	@echo "  1. cp soma.conf.example soma.conf"
	@echo "  2. Edit soma.conf (set SOMA_PLATFORM, TEAM_SIZE, etc.)"
	@echo "  3. make install"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Override any setting inline: make install RULES_SUBSET=core"


info: ## Show current configuration
	@echo "┌───────────────────────────────┐"
	@echo "│  Soma — Configuration         │"
	@echo "├───────────────────────────────┤"
	@echo "│  Platform:        $(SOMA_PLATFORM)"
	@echo "│  Team Size:       $(TEAM_SIZE)"
	@echo "│  Git Strategy:    $(GIT_STRATEGY)"
	@echo "│  Approval Chain:  $(APPROVAL_CHAIN)"
	@echo "│  Rules Subset:    $(RULES_SUBSET)"
	@echo "│  Hooks Enabled:   $(ENABLE_HOOKS)"
	@echo "└───────────────────────────────┘"

install: ## Install for configured platform (SOMA_PLATFORM)
	@bash install/install.sh $(SOMA_PLATFORM)

install-gemini: ## Install rules for Gemini/Antigravity (alias)
	@bash install/install.sh gemini

install-kiro: ## Install rules for Kiro (alias)
	@bash install/install.sh kiro

install-copilot: ## Install rules for GitHub Copilot (alias)
	@bash install/install.sh copilot $(if $(MODE),$(MODE),global)

install-claude: ## Install rules for Claude Code
	@bash install/install.sh claude

install-windows: ## Install rules and skills for Windows using PowerShell
	@powershell -ExecutionPolicy Bypass -File install/install.ps1 -Platform $(SOMA_PLATFORM)

uninstall: ## Remove installed genome, organs, and hooks
	@echo "Uninstalling Soma for $(SOMA_PLATFORM)..."
	@case "$(SOMA_PLATFORM)" in \
	  gemini) \
	    echo "  Removing rules from $(HOME)/.gemini/config/genome/"; \
	    rm -f $(HOME)/.gemini/config/genome/providence.md $(HOME)/.gemini/config/genome/cost-optimization.md \
	      $(HOME)/.gemini/config/genome/subagent-delegation.md $(HOME)/.gemini/config/genome/testing.md \
	      $(HOME)/.gemini/config/genome/git-workflow.md $(HOME)/.gemini/config/genome/destructive-ops.md \
	      $(HOME)/.gemini/config/genome/documentation.md $(HOME)/.gemini/config/genome/architectural-tenets.md \
	      $(HOME)/.gemini/config/genome/feature-specs.md $(HOME)/.gemini/config/genome/polyglot-standards.md \
	      $(HOME)/.gemini/config/genome/desktop-automation.md; \
	    echo "  Removing hooks"; \
	    rm -f $(HOME)/.gemini/config/plugins/governance/hooks.json; \
	    echo "  Removing skills"; \
	    for skill_dir in organs/*/; do \
	      skill=$$(basename "$$skill_dir"); \
	      rm -rf $(HOME)/.gemini/config/organs/$$skill; \
	    done; \
	    echo "Done! Rules, hooks, and skills removed."; \
	    ;; \
	  kiro) \
	    echo "  Removing rules from $(HOME)/.kiro/steering/"; \
	    rm -rf $(HOME)/.kiro/steering/; \
	    echo "  Removing skills from $(HOME)/.kiro/organs/"; \
	    for skill_dir in organs/*/; do \
	      skill=$$(basename "$$skill_dir"); \
	      rm -rf $(HOME)/.kiro/organs/$$skill; \
	    done; \
	    echo "  Removing hooks from $(HOME)/.kiro/hooks/"; \
	    rm -f $(HOME)/.kiro/hooks/hooks.json; \
	    echo "Done! Rules, skills, and hooks removed."; \
	    ;; \
	  copilot) \
	    echo "  Removing $(HOME)/copilot-instructions.md"; \
	    rm -f $(HOME)/copilot-instructions.md; \
	    echo "Done!"; \
	    ;; \
	  claude) \
	    echo "  Removing $(HOME)/.claude/CLAUDE.md and local CLAUDE.md/.mcp.json"; \
	    rm -f $(HOME)/.claude/CLAUDE.md; \
	    rm -f CLAUDE.md .mcp.json; \
	    echo "Done!"; \
	    ;; \
	esac

doctor: ## Verify installation health & dependencies
	@echo "Running health check..."
	@echo ""
	@echo "Dependencies:"
	@command -v bash >/dev/null 2>&1 && echo "  ✅ bash" || echo "  ❌ bash not found"
	@command -v python3 >/dev/null 2>&1 && echo "  ✅ python3" || echo "  ⚠️  python3 not found (hooks will not install)"
	@command -v git >/dev/null 2>&1 && echo "  ✅ git" || echo "  ❌ git not found"
	@command -v sed >/dev/null 2>&1 && echo "  ✅ sed" || echo "  ❌ sed not found"
	@command -v awk >/dev/null 2>&1 && echo "  ✅ awk" || echo "  ❌ awk not found"
	@echo ""
	@echo "Scripts:"
	@for s in enzymes/*.sh; do \
	  if [ -f "$$s" ]; then echo "  ✅ $$s"; else echo "  ❌ $$s missing"; fi; \
	done
	@echo ""
	@echo "Hook template:"
	@if [ -f install/hooks.json.template ]; then echo "  ✅ install/hooks.json.template"; else echo "  ❌ install/hooks.json.template missing"; fi
	@echo ""
	@echo "Installed genome ($(SOMA_PLATFORM)):"
	@case "$(SOMA_PLATFORM)" in \
	  gemini) ls $(HOME)/.gemini/config/genome/*.md 2>/dev/null | while read f; do echo "  ✅ $$(basename $$f)"; done || echo "  (none)"; \
	    if [ -f $(HOME)/.gemini/config/plugins/governance/hooks.json ]; then echo "  ✅ hooks.json installed"; else echo "  ⚠️  hooks.json not installed"; fi ;; \
	  kiro) ls $(HOME)/.kiro/steering/*.md 2>/dev/null | while read f; do echo "  ✅ $$(basename $$f)"; done || echo "  (none)"; \
	    echo ""; \
	    echo "Installed skills (kiro):"; \
	    if [ -d $(HOME)/.kiro/skills ]; then \
	      ls -d $(HOME)/.kiro/organs/*/ 2>/dev/null | while read d; do echo "  ✅ $$(basename $$d)"; done || echo "  (none)"; \
	    else echo "  (none — $(HOME)/.kiro/organs/ not found)"; fi ;; \
	  copilot) if [ -f $(HOME)/copilot-instructions.md ]; then echo "  ✅ $(HOME)/copilot-instructions.md"; else echo "  (none)"; fi ;; \
	  claude) if [ -f $(HOME)/.claude/CLAUDE.md ]; then echo "  ✅ $(HOME)/.claude/CLAUDE.md"; else echo "  (none)"; fi ;; \
	esac

validate: ## Check script syntax and config values
	@echo "Validating..."
	@for s in install/install.sh enzymes/*.sh; do \
	  if [ -f "$$s" ]; then bash -n "$$s" && echo "  ✅ $$s" || echo "  ❌ $$s"; fi; \
	done
	@if command -v python3 >/dev/null 2>&1; then \
	  python3 -m json.tool install/hooks.json.template > /dev/null 2>&1 && echo "  ✅ install/hooks.json.template (valid JSON)" || echo "  ❌ install/hooks.json.template (invalid JSON)"; \
	fi
	@echo "Done!"

update: ## Pull latest and re-install
	@echo "Pulling latest changes..."
	@git pull --ff-only
	@echo ""
	@$(MAKE) install

status: ## Show installed vs repo diff
	@echo "Comparing installed rules to repo..."
	@case "$(SOMA_PLATFORM)" in \
	  gemini) for rule in genome/*.md; do \
	    name=$$(basename $$rule); \
	    target=$(HOME)/.gemini/config/genome/$$name; \
	    if [ ! -f "$$target" ]; then echo "  ❌ $$name (not installed)"; \
	    elif diff -q "$$rule" "$$target" > /dev/null 2>&1; then echo "  ✅ $$name (in sync)"; \
	    else echo "  ⚠️  $$name (modified)"; fi; \
	  done ;; \
	  kiro) for rule in genome/*.md; do \
	    name=$$(basename $$rule); \
	    target=$(HOME)/.kiro/steering/$$name; \
	    if [ ! -f "$$target" ]; then echo "  ❌ $$name (not installed)"; \
	    else echo "  ✅ $$name (installed)"; fi; \
	  done ;; \
	  *) echo "  Status check only supported for gemini and kiro platforms" ;; \
	esac

test: validate ## Run validation tests
	@echo "All tests passed."
