.PHONY: install update link uninstall status help docs sync-external

REPO_DIR := $(shell pwd)
CLAUDE_DIR := $(HOME)/.claude
AGENTS_DIR := $(CLAUDE_DIR)/agents/commas
COMMANDS_DIR := $(CLAUDE_DIR)/commands/commas
SKILLS_DIR := $(CLAUDE_DIR)/skills/commas
COMMAS_DIR := $(CLAUDE_DIR)/commas
IMPORT_LINE := @~/.claude/commas/CLAUDE.md

help:
	@echo "commas-claude - 3Commas Claude Code configurations"
	@echo ""
	@echo "Usage:"
	@echo "  make install       Pull latest + create symlinks (for users)"
	@echo "  make link          Create symlinks only (for maintainers)"
	@echo "  make sync-external Fetch external content from wshobson/agents"
	@echo "  make uninstall     Remove installed symlinks"
	@echo "  make status        Show currently installed items"
	@echo "  make docs          Generate AGENTS.md documentation"
	@echo "  make help          Show this help message"
	@echo ""
	@echo "Installs to:"
	@echo "  ~/.claude/agents/commas/    - agents"
	@echo "  ~/.claude/commands/commas/  - commands"
	@echo "  ~/.claude/skills/commas/    - skills"
	@echo "  ~/.claude/commas/CLAUDE.md  - org-wide instructions (imported into ~/.claude/CLAUDE.md)"

install: update

update:
	@echo "Pulling latest..."
	@git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || echo "Note: Could not pull (offline or no remote)"
	@$(MAKE) link --no-print-directory

link:
	@echo "Syncing symlinks..."
	@mkdir -p $(AGENTS_DIR)
	@mkdir -p $(COMMANDS_DIR)
	@mkdir -p $(SKILLS_DIR)
	@mkdir -p $(COMMAS_DIR)
	@# Clean up orphaned agent symlinks (check both agents/ and agents/external/)
	@if [ -d "$(AGENTS_DIR)" ]; then \
		for link in $(AGENTS_DIR)/*.md; do \
			if [ -L "$$link" ]; then \
				name=$$(basename "$$link"); \
				if [ ! -f "$(REPO_DIR)/agents/$$name" ] && [ ! -f "$(REPO_DIR)/agents/external/$$name" ]; then \
					rm -f "$$link"; \
					echo "  ✗ agents/commas/$$name (removed)"; \
				fi \
			fi \
		done 2>/dev/null || true; \
	fi
	@# Clean up orphaned command symlinks (check both commands/ and commands/external/)
	@if [ -d "$(COMMANDS_DIR)" ]; then \
		for link in $(COMMANDS_DIR)/*.md; do \
			if [ -L "$$link" ]; then \
				name=$$(basename "$$link"); \
				if [ ! -f "$(REPO_DIR)/commands/$$name" ] && [ ! -f "$(REPO_DIR)/commands/external/$$name" ]; then \
					rm -f "$$link"; \
					echo "  ✗ commands/commas/$$name (removed)"; \
				fi \
			fi \
		done 2>/dev/null || true; \
	fi
	@# Clean up orphaned skill symlinks
	@if [ -d "$(SKILLS_DIR)" ]; then \
		for link in $(SKILLS_DIR)/*/; do \
			if [ -d "$$link" ]; then \
				name=$$(basename "$$link"); \
				if [ ! -d "$(REPO_DIR)/skills/external/$$name" ]; then \
					rm -rf "$$link"; \
					echo "  ✗ skills/commas/$$name (removed)"; \
				fi \
			fi \
		done 2>/dev/null || true; \
	fi
	@# Symlink agents (custom)
	@find $(REPO_DIR)/agents -maxdepth 1 -name "*.md" -type f -exec sh -c 'ln -sf "$$1" $(AGENTS_DIR)/$$(basename "$$1") && echo "  → agent: $$(basename "$$1")"' _ {} \;
	@# Symlink agents (external, skip README.md)
	@if [ -d "$(REPO_DIR)/agents/external" ]; then \
		find $(REPO_DIR)/agents/external -maxdepth 1 -name "*.md" -type f ! -name "README.md" -exec sh -c 'ln -sf "$$1" $(AGENTS_DIR)/$$(basename "$$1") && echo "  → agent: $$(basename "$$1") (external)"' _ {} \; 2>/dev/null || true; \
	fi
	@# Symlink commands (custom)
	@find $(REPO_DIR)/commands -maxdepth 1 -name "*.md" -type f ! -name ".gitkeep" -exec sh -c 'ln -sf "$$1" $(COMMANDS_DIR)/$$(basename "$$1") && echo "  → command: $$(basename "$$1")"' _ {} \; 2>/dev/null || true
	@# Symlink commands (external, skip README.md)
	@if [ -d "$(REPO_DIR)/commands/external" ]; then \
		find $(REPO_DIR)/commands/external -maxdepth 1 -name "*.md" -type f ! -name "README.md" -exec sh -c 'ln -sf "$$1" $(COMMANDS_DIR)/$$(basename "$$1") && echo "  → command: $$(basename "$$1") (external)"' _ {} \; 2>/dev/null || true; \
	fi
	@# Symlink skills (external - preserve directory structure)
	@if [ -d "$(REPO_DIR)/skills/external" ]; then \
		for skill_dir in $(REPO_DIR)/skills/external/*/; do \
			if [ -d "$$skill_dir" ] && [ -f "$$skill_dir/SKILL.md" ]; then \
				skill_name=$$(basename "$$skill_dir"); \
				mkdir -p "$(SKILLS_DIR)/$$skill_name"; \
				ln -sf "$$skill_dir/SKILL.md" "$(SKILLS_DIR)/$$skill_name/SKILL.md"; \
				echo "  → skill: $$skill_name"; \
			fi \
		done 2>/dev/null || true; \
	fi
	@# Symlink org CLAUDE.md
	@if [ -f "$(REPO_DIR)/config/CLAUDE.md" ]; then \
		ln -sf "$(REPO_DIR)/config/CLAUDE.md" "$(COMMAS_DIR)/CLAUDE.md"; \
		echo "  → commas/CLAUDE.md"; \
	fi
	@# Add import line to ~/.claude/CLAUDE.md if not present
	@if [ -f "$(REPO_DIR)/config/CLAUDE.md" ]; then \
		if [ ! -f "$(CLAUDE_DIR)/CLAUDE.md" ]; then \
			echo "$(IMPORT_LINE)" > "$(CLAUDE_DIR)/CLAUDE.md"; \
			echo "  ✓ Created ~/.claude/CLAUDE.md with import"; \
		elif ! grep -qF "$(IMPORT_LINE)" "$(CLAUDE_DIR)/CLAUDE.md"; then \
			echo "" >> "$(CLAUDE_DIR)/CLAUDE.md"; \
			echo "$(IMPORT_LINE)" >> "$(CLAUDE_DIR)/CLAUDE.md"; \
			echo "  ✓ Added import to ~/.claude/CLAUDE.md"; \
		else \
			echo "  ✓ Import already in ~/.claude/CLAUDE.md"; \
		fi \
	fi
	@echo ""
	@echo "✓ Linked to ~/.claude/"

uninstall:
	@echo "Removing commas-claude symlinks..."
	@# Remove agent symlinks
	@if [ -d "$(AGENTS_DIR)" ]; then \
		find $(REPO_DIR)/agents -maxdepth 1 -name "*.md" -type f -exec sh -c 'rm -f $(AGENTS_DIR)/$$(basename "$$1") && echo "  ✗ agents/commas/$$(basename "$$1")"' _ {} \; ; \
		if [ -d "$(REPO_DIR)/agents/external" ]; then \
			find $(REPO_DIR)/agents/external -maxdepth 1 -name "*.md" -type f ! -name "README.md" -exec sh -c 'rm -f $(AGENTS_DIR)/$$(basename "$$1") && echo "  ✗ agents/commas/$$(basename "$$1")"' _ {} \; 2>/dev/null || true ; \
		fi \
	fi
	@# Remove command symlinks
	@if [ -d "$(COMMANDS_DIR)" ]; then \
		find $(REPO_DIR)/commands -maxdepth 1 -name "*.md" -type f ! -name ".gitkeep" -exec sh -c 'rm -f $(COMMANDS_DIR)/$$(basename "$$1") && echo "  ✗ commands/commas/$$(basename "$$1")"' _ {} \; 2>/dev/null || true ; \
		if [ -d "$(REPO_DIR)/commands/external" ]; then \
			find $(REPO_DIR)/commands/external -maxdepth 1 -name "*.md" -type f ! -name "README.md" -exec sh -c 'rm -f $(COMMANDS_DIR)/$$(basename "$$1") && echo "  ✗ commands/commas/$$(basename "$$1")"' _ {} \; 2>/dev/null || true ; \
		fi \
	fi
	@# Remove skill symlinks
	@if [ -d "$(SKILLS_DIR)" ]; then \
		if [ -d "$(REPO_DIR)/skills/external" ]; then \
			for skill_dir in $(REPO_DIR)/skills/external/*/; do \
				skill_name=$$(basename "$$skill_dir"); \
				rm -rf "$(SKILLS_DIR)/$$skill_name" 2>/dev/null && echo "  ✗ skills/commas/$$skill_name" || true; \
			done; \
		fi \
	fi
	@# Remove org CLAUDE.md symlink
	@rm -f "$(COMMAS_DIR)/CLAUDE.md" 2>/dev/null && echo "  ✗ commas/CLAUDE.md" || true
	@# Clean up empty directories
	@rmdir $(AGENTS_DIR) 2>/dev/null || true
	@rmdir $(COMMANDS_DIR) 2>/dev/null || true
	@rmdir $(SKILLS_DIR) 2>/dev/null || true
	@rmdir $(COMMAS_DIR) 2>/dev/null || true
	@echo ""
	@echo "Note: Import line in ~/.claude/CLAUDE.md was not removed (manual cleanup if needed)"
	@echo "✓ Uninstalled"

status:
	@echo "commas-claude status"
	@echo "===================="
	@echo ""
	@echo "Org instructions (in ~/.claude/commas/):"
	@if [ -L "$(COMMAS_DIR)/CLAUDE.md" ]; then \
		echo "  ✓ CLAUDE.md"; \
		if grep -qF "$(IMPORT_LINE)" "$(CLAUDE_DIR)/CLAUDE.md" 2>/dev/null; then \
			echo "  ✓ Import present in ~/.claude/CLAUDE.md"; \
		else \
			echo "  ✗ Import missing from ~/.claude/CLAUDE.md"; \
		fi \
	else \
		echo "  ✗ CLAUDE.md (not installed)"; \
	fi
	@echo ""
	@echo "Installed agents (in ~/.claude/agents/commas/):"
	@agent_count=0; \
	if [ -d "$(AGENTS_DIR)" ]; then \
		for f in $(AGENTS_DIR)/*.md; do \
			if [ -L "$$f" ]; then \
				agent_count=$$((agent_count + 1)); \
			fi \
		done; \
		echo "  $$agent_count agents installed"; \
	else \
		echo "  (commas/ directory not found - run make install)"; \
	fi
	@echo ""
	@echo "Installed commands (in ~/.claude/commands/commas/):"
	@cmd_count=0; \
	if [ -d "$(COMMANDS_DIR)" ]; then \
		for f in $(COMMANDS_DIR)/*.md; do \
			if [ -L "$$f" ]; then \
				cmd_count=$$((cmd_count + 1)); \
			fi \
		done; \
		echo "  $$cmd_count commands installed"; \
	else \
		echo "  (none)"; \
	fi
	@echo ""
	@echo "Installed skills (in ~/.claude/skills/commas/):"
	@skill_count=0; \
	if [ -d "$(SKILLS_DIR)" ]; then \
		for d in $(SKILLS_DIR)/*/; do \
			if [ -d "$$d" ]; then \
				skill_count=$$((skill_count + 1)); \
			fi \
		done; \
		echo "  $$skill_count skills installed"; \
	else \
		echo "  (none)"; \
	fi

docs:
	@python3 $(REPO_DIR)/scripts/generate-docs.py

sync-external:
	@$(REPO_DIR)/scripts/sync-external.sh
	@$(MAKE) docs --no-print-directory
