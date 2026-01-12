.PHONY: install sync-external docs help cleanup

REPO_DIR := $(shell pwd)
CLAUDE_DIR := $(HOME)/.claude

# Old paths from previous symlink-based installation
OLD_AGENTS_DIR := $(CLAUDE_DIR)/agents/commas
OLD_COMMANDS_DIR := $(CLAUDE_DIR)/commands/commas
OLD_SKILLS_DIR := $(CLAUDE_DIR)/skills/commas
OLD_COMMAS_DIR := $(CLAUDE_DIR)/commas
OLD_IMPORT_LINE := @~/.claude/commas/CLAUDE.md

help:
	@echo "3commas - 3Commas Claude Code Plugin"
	@echo ""
	@echo "Usage:"
	@echo "  make install       Show installation instructions"
	@echo "  make cleanup       Remove old symlink-based installation"
	@echo "  make sync-external Sync external content from wshobson/agents"
	@echo "  make docs          Generate AGENTS.md documentation"
	@echo "  make help          Show this help message"
	@echo ""
	@echo "This repo is a Claude Code plugin. Install via:"
	@echo ""
	@echo "  /plugin marketplace add 3commas/commas-claude"
	@echo "  /plugin install 3commas@3commas"

install:
	@echo "============================================"
	@echo "3commas Claude Code Plugin Installation"
	@echo "============================================"
	@echo ""
	@echo "Step 1: Add the marketplace (run in Claude Code):"
	@echo ""
	@echo "  /plugin marketplace add 3commas/commas-claude"
	@echo ""
	@echo "Step 2: Install the plugin:"
	@echo ""
	@echo "  /plugin install 3commas@3commas"
	@echo ""
	@echo "============================================"
	@echo ""
	@echo "Alternative: Add to ~/.claude/settings.json:"
	@echo ""
	@echo '  {'
	@echo '    "extraKnownMarketplaces": {'
	@echo '      "3commas": {'
	@echo '        "source": { "source": "github", "repo": "3commas/commas-claude" }'
	@echo '      }'
	@echo '    },'
	@echo '    "enabledPlugins": { "3commas@3commas": true }'
	@echo '  }'
	@echo ""
	@echo "============================================"

sync-external:
	@$(REPO_DIR)/scripts/sync-external.sh
	@$(MAKE) docs --no-print-directory

docs:
	@python3 $(REPO_DIR)/scripts/generate-docs.py

cleanup:
	@echo "Cleaning up old symlink-based installation..."
	@# Remove old agent symlinks
	@if [ -d "$(OLD_AGENTS_DIR)" ]; then \
		rm -rf "$(OLD_AGENTS_DIR)"; \
		echo "  Removed ~/.claude/agents/commas/"; \
	fi
	@# Remove old command symlinks
	@if [ -d "$(OLD_COMMANDS_DIR)" ]; then \
		rm -rf "$(OLD_COMMANDS_DIR)"; \
		echo "  Removed ~/.claude/commands/commas/"; \
	fi
	@# Remove old skill symlinks
	@if [ -d "$(OLD_SKILLS_DIR)" ]; then \
		rm -rf "$(OLD_SKILLS_DIR)"; \
		echo "  Removed ~/.claude/skills/commas/"; \
	fi
	@# Remove old commas directory (CLAUDE.md symlink)
	@if [ -d "$(OLD_COMMAS_DIR)" ]; then \
		rm -rf "$(OLD_COMMAS_DIR)"; \
		echo "  Removed ~/.claude/commas/"; \
	fi
	@# Remove old import line from ~/.claude/CLAUDE.md
	@if [ -f "$(CLAUDE_DIR)/CLAUDE.md" ] && grep -qF "$(OLD_IMPORT_LINE)" "$(CLAUDE_DIR)/CLAUDE.md" 2>/dev/null; then \
		echo "  Removing import line from ~/.claude/CLAUDE.md..."; \
		sed -i.bak '/^@~\/.claude\/commas\/CLAUDE.md/d' "$(CLAUDE_DIR)/CLAUDE.md" 2>/dev/null || \
		sed -i '' '/^@~\/.claude\/commas\/CLAUDE.md/d' "$(CLAUDE_DIR)/CLAUDE.md" 2>/dev/null || true; \
		rm -f "$(CLAUDE_DIR)/CLAUDE.md.bak" 2>/dev/null || true; \
	fi
	@# Clean up empty parent directories
	@rmdir "$(CLAUDE_DIR)/agents" 2>/dev/null || true
	@rmdir "$(CLAUDE_DIR)/commands" 2>/dev/null || true
	@rmdir "$(CLAUDE_DIR)/skills" 2>/dev/null || true
	@echo ""
	@echo "Cleanup complete. Now install the new plugin version:"
	@echo ""
	@echo "  /plugin marketplace add 3commas/commas-claude"
	@echo "  /plugin install 3commas@3commas"
