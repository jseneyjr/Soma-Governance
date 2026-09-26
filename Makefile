# AI Steering Rules — Makefile
# Reads steering.conf for team/workflow configuration.
# Without steering.conf, all defaults apply (solo/trunk/python/all).

# Load user config (optional — defaults if missing)
-include steering.conf

# Defaults
TEAM_SIZE       ?= solo
GIT_STRATEGY    ?= trunk
AI_USAGE        ?= individual
APPROVAL_CHAIN  ?= none
TECH_STACK      ?= python
LANGUAGES       ?= python
TEST_COMMAND    ?=
PACKAGE_MANAGER ?=
RULES_SUBSET    ?= all
ENABLE_HOOKS    ?= true
MODE            ?= global

# Export for install scripts
export TEAM_SIZE GIT_STRATEGY AI_USAGE APPROVAL_CHAIN
export TECH_STACK LANGUAGES TEST_COMMAND PACKAGE_MANAGER
export RULES_SUBSET ENABLE_HOOKS

.PHONY: help info install install-gemini install-kiro install-copilot

help: ## Show available targets
	@echo "AI Steering Rules"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Configuration:"
	@echo "  Copy steering.conf.example → steering.conf to customize."
	@echo "  Run 'make info' to see current settings."

info: ## Show current configuration
	@echo "┌─────────────────────────────────────┐"
	@echo "│  AI Steering Rules — Configuration  │"
	@echo "├─────────────────────────────────────┤"
	@echo "│  Team Size:       $(TEAM_SIZE)"
	@echo "│  Git Strategy:    $(GIT_STRATEGY)"
	@echo "│  AI Usage:        $(AI_USAGE)"
	@echo "│  Approval Chain:  $(APPROVAL_CHAIN)"
	@echo "│  Tech Stack:      $(TECH_STACK)"
	@echo "│  Languages:       $(LANGUAGES)"
	@echo "│  Test Command:    $(or $(TEST_COMMAND),auto-detect)"
	@echo "│  Pkg Manager:     $(or $(PACKAGE_MANAGER),auto-detect)"
	@echo "│  Rules Subset:    $(RULES_SUBSET)"
	@echo "│  Hooks Enabled:   $(ENABLE_HOOKS)"
	@echo "└─────────────────────────────────────┘"

install: install-gemini ## Install for default platform (Gemini)

install-gemini: ## Install rules for Gemini/Antigravity
	@bash install-gemini.sh

install-kiro: ## Install rules for Kiro
	@bash install-kiro.sh

install-copilot: ## Install rules for GitHub Copilot (MODE=global|project)
	@bash install-copilot.sh $(MODE)
