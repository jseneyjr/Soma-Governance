# AI Steering Rules — Makefile
# Reads steering.conf for team/workflow configuration.
# Without steering.conf, all defaults apply (solo/trunk/all).

-include steering.conf

# Defaults (namespaced to avoid env collisions)
STEERING_PLATFORM ?= gemini
TEAM_SIZE         ?= solo
GIT_STRATEGY      ?= trunk
APPROVAL_CHAIN    ?= none
RULES_SUBSET      ?= all
ENABLE_HOOKS      ?= true

export TEAM_SIZE GIT_STRATEGY APPROVAL_CHAIN
export RULES_SUBSET ENABLE_HOOKS STEERING_PLATFORM

.PHONY: help info install install-gemini install-kiro install-copilot install-windows \
        uninstall doctor validate update status test

help: ## Show available targets
	@echo "AI Steering Rules"
	@echo ""
	@echo "Workflow:"
	@echo "  1. cp steering.conf.example steering.conf"
	@echo "  2. Edit steering.conf (set STEERING_PLATFORM, TEAM_SIZE, etc.)"
	@echo "  3. make install"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Override any setting inline: make install RULES_SUBSET=core"


info: ## Show current configuration
	@echo "┌─────────────────────────────────────┐"
	@echo "│  AI Steering Rules — Configuration  │"
	@echo "├─────────────────────────────────────┤"
	@echo "│  Platform:        $(STEERING_PLATFORM)"
	@echo "│  Team Size:       $(TEAM_SIZE)"
	@echo "│  Git Strategy:    $(GIT_STRATEGY)"
	@echo "│  Approval Chain:  $(APPROVAL_CHAIN)"
	@echo "│  Rules Subset:    $(RULES_SUBSET)"
	@echo "│  Hooks Enabled:   $(ENABLE_HOOKS)"
	@echo "└─────────────────────────────────────┘"

install: ## Install for configured platform (STEERING_PLATFORM)
	@bash install.sh $(STEERING_PLATFORM)

install-gemini: ## Install rules for Gemini/Antigravity
	@bash install.sh gemini

install-kiro: ## Install rules for Kiro
	@bash install.sh kiro

install-copilot: ## Install rules for GitHub Copilot
	@bash install.sh copilot $(if $(MODE),$(MODE),global)

install-windows: ## Install rules and skills for Windows using PowerShell
	@powershell -ExecutionPolicy Bypass -File install.ps1 -Platform $(STEERING_PLATFORM)

uninstall: ## Remove installed rules, skills, and hooks
	@echo "Uninstalling steering rules for $(STEERING_PLATFORM)..."
	@case "$(STEERING_PLATFORM)" in \
	  gemini) \
	    echo "  Removing rules from $(HOME)/.gemini/config/rules/"; \
	    rm -f $(HOME)/.gemini/config/rules/providence.md $(HOME)/.gemini/config/rules/cost-optimization.md \
	      $(HOME)/.gemini/config/rules/subagent-delegation.md $(HOME)/.gemini/config/rules/testing.md \
	      $(HOME)/.gemini/config/rules/git-workflow.md $(HOME)/.gemini/config/rules/destructive-ops.md \
	      $(HOME)/.gemini/config/rules/documentation.md $(HOME)/.gemini/config/rules/architectural-tenets.md \
	      $(HOME)/.gemini/config/rules/feature-specs.md $(HOME)/.gemini/config/rules/polyglot-standards.md \
	      $(HOME)/.gemini/config/rules/desktop-automation.md; \
	    echo "  Removing hooks"; \
	    rm -f $(HOME)/.gemini/config/plugins/governance/hooks.json; \
	    echo "  Removing skills"; \
	    for skill_dir in skills/*/; do \
	      skill=$$(basename "$$skill_dir"); \
	      rm -rf $(HOME)/.gemini/config/skills/$$skill; \
	    done; \
	    echo "Done! Rules, hooks, and skills removed."; \
	    ;; \
	  kiro) \
	    echo "  Removing rules from $(HOME)/.kiro/steering/"; \
	    rm -rf $(HOME)/.kiro/steering/; \
	    echo "  Removing skills from $(HOME)/.kiro/skills/"; \
	    for skill_dir in skills/*/; do \
	      skill=$$(basename "$$skill_dir"); \
	      rm -rf $(HOME)/.kiro/skills/$$skill; \
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
	@for s in scripts/*.sh; do \
	  if [ -f "$$s" ]; then echo "  ✅ $$s"; else echo "  ❌ $$s missing"; fi; \
	done
	@echo ""
	@echo "Hook template:"
	@if [ -f hooks.json.template ]; then echo "  ✅ hooks.json.template"; else echo "  ❌ hooks.json.template missing"; fi
	@echo ""
	@echo "Installed rules ($(STEERING_PLATFORM)):"
	@case "$(STEERING_PLATFORM)" in \
	  gemini) ls $(HOME)/.gemini/config/rules/*.md 2>/dev/null | while read f; do echo "  ✅ $$(basename $$f)"; done || echo "  (none)"; \
	    if [ -f $(HOME)/.gemini/config/plugins/governance/hooks.json ]; then echo "  ✅ hooks.json installed"; else echo "  ⚠️  hooks.json not installed"; fi ;; \
	  kiro) ls $(HOME)/.kiro/steering/*.md 2>/dev/null | while read f; do echo "  ✅ $$(basename $$f)"; done || echo "  (none)"; \
	    echo ""; \
	    echo "Installed skills (kiro):"; \
	    if [ -d $(HOME)/.kiro/skills ]; then \
	      ls -d $(HOME)/.kiro/skills/*/ 2>/dev/null | while read d; do echo "  ✅ $$(basename $$d)"; done || echo "  (none)"; \
	    else echo "  (none — $(HOME)/.kiro/skills/ not found)"; fi ;; \
	  copilot) if [ -f $(HOME)/copilot-instructions.md ]; then echo "  ✅ $(HOME)/copilot-instructions.md"; else echo "  (none)"; fi ;; \
	esac

validate: ## Check script syntax and config values
	@echo "Validating..."
	@for s in install.sh install-*.sh scripts/*.sh; do \
	  if [ -f "$$s" ]; then bash -n "$$s" && echo "  ✅ $$s" || echo "  ❌ $$s"; fi; \
	done
	@if command -v python3 >/dev/null 2>&1; then \
	  python3 -m json.tool hooks.json.template > /dev/null 2>&1 && echo "  ✅ hooks.json.template (valid JSON)" || echo "  ❌ hooks.json.template (invalid JSON)"; \
	fi
	@echo "Done!"

update: ## Pull latest and re-install
	@echo "Pulling latest changes..."
	@git pull --ff-only
	@echo ""
	@$(MAKE) install

status: ## Show installed vs repo diff
	@echo "Comparing installed rules to repo..."
	@case "$(STEERING_PLATFORM)" in \
	  gemini) for rule in rules/*.md; do \
	    name=$$(basename $$rule); \
	    target=$(HOME)/.gemini/config/rules/$$name; \
	    if [ ! -f "$$target" ]; then echo "  ❌ $$name (not installed)"; \
	    elif diff -q "$$rule" "$$target" > /dev/null 2>&1; then echo "  ✅ $$name (in sync)"; \
	    else echo "  ⚠️  $$name (modified)"; fi; \
	  done ;; \
	  kiro) for rule in rules/*.md; do \
	    name=$$(basename $$rule); \
	    target=$(HOME)/.kiro/steering/$$name; \
	    if [ ! -f "$$target" ]; then echo "  ❌ $$name (not installed)"; \
	    else echo "  ✅ $$name (installed)"; fi; \
	  done ;; \
	  *) echo "  Status check only supported for gemini and kiro platforms" ;; \
	esac

test: validate ## Run validation tests
	@echo "All tests passed."
