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

.PHONY: help info install install-gemini install-kiro install-copilot \
        uninstall doctor validate update status

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

uninstall: ## Remove installed rules, skills, and hooks
	@echo "Uninstalling steering rules for $(STEERING_PLATFORM)..."
	@case "$(STEERING_PLATFORM)" in \
	  gemini) \
	    echo "  Removing rules from ~/.gemini/config/rules/"; \
	    rm -f ~/.gemini/config/rules/providence.md ~/.gemini/config/rules/cost-optimization.md \
	      ~/.gemini/config/rules/subagent-delegation.md ~/.gemini/config/rules/testing.md \
	      ~/.gemini/config/rules/git-workflow.md ~/.gemini/config/rules/destructive-ops.md \
	      ~/.gemini/config/rules/documentation.md ~/.gemini/config/rules/architectural-tenets.md \
	      ~/.gemini/config/rules/feature-specs.md ~/.gemini/config/rules/polyglot-standards.md \
	      ~/.gemini/config/rules/desktop-automation.md; \
	    echo "  Removing hooks"; \
	    rm -f ~/.gemini/config/plugins/governance/hooks.json; \
	    echo "Done! Rules and hooks removed."; \
	    ;; \
	  kiro) \
	    echo "  Removing rules from ~/.kiro/steering/"; \
	    rm -rf ~/.kiro/steering/; \
	    echo "Done!"; \
	    ;; \
	  copilot) \
	    echo "  Removing ~/copilot-instructions.md"; \
	    rm -f ~/copilot-instructions.md; \
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
	@for s in scripts/common.sh scripts/governance_init.sh scripts/safety_gate.sh scripts/session_close.sh; do \
	  if [ -f "$$s" ]; then echo "  ✅ $$s"; else echo "  ❌ $$s missing"; fi; \
	done
	@echo ""
	@echo "Hook template:"
	@if [ -f hooks.json.template ]; then echo "  ✅ hooks.json.template"; else echo "  ❌ hooks.json.template missing"; fi
	@echo ""
	@echo "Installed rules ($(STEERING_PLATFORM)):"
	@case "$(STEERING_PLATFORM)" in \
	  gemini) ls ~/.gemini/config/rules/*.md 2>/dev/null | while read f; do echo "  ✅ $$(basename $$f)"; done || echo "  (none)"; \
	    if [ -f ~/.gemini/config/plugins/governance/hooks.json ]; then echo "  ✅ hooks.json installed"; else echo "  ⚠️  hooks.json not installed"; fi ;; \
	  kiro) ls ~/.kiro/steering/*.md 2>/dev/null | while read f; do echo "  ✅ $$(basename $$f)"; done || echo "  (none)" ;; \
	  copilot) if [ -f ~/copilot-instructions.md ]; then echo "  ✅ ~/copilot-instructions.md"; else echo "  (none)"; fi ;; \
	esac

validate: ## Check script syntax and config values
	@echo "Validating..."
	@bash -n install.sh && echo "  ✅ install.sh" || echo "  ❌ install.sh"
	@bash -n scripts/common.sh && echo "  ✅ scripts/common.sh" || echo "  ❌ scripts/common.sh"
	@bash -n scripts/governance_init.sh && echo "  ✅ scripts/governance_init.sh" || echo "  ❌ scripts/governance_init.sh"
	@bash -n scripts/safety_gate.sh && echo "  ✅ scripts/safety_gate.sh" || echo "  ❌ scripts/safety_gate.sh"
	@bash -n scripts/session_close.sh && echo "  ✅ scripts/session_close.sh" || echo "  ❌ scripts/session_close.sh"
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
	    target=~/.gemini/config/rules/$$name; \
	    if [ ! -f "$$target" ]; then echo "  ❌ $$name (not installed)"; \
	    elif diff -q "$$rule" "$$target" > /dev/null 2>&1; then echo "  ✅ $$name (in sync)"; \
	    else echo "  ⚠️  $$name (modified)"; fi; \
	  done ;; \
	  *) echo "  Status check only supported for gemini platform" ;; \
	esac
