# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains 3Commas company-wide Claude Code configurations that are symlinked to engineers' `~/.claude/` directories via `make install`.

## Repository Structure

```
commas-claude/
├── agents/                    # Custom 3Commas agents
│   ├── github-pr.md
│   ├── jira-status-report.md
│   └── external/              # Vendored from wshobson/agents
├── commands/                  # Custom slash commands/skills
├── config/
│   ├── CLAUDE.md              # Org-wide instructions (imported into ~/.claude/CLAUDE.md)
│   └── external-agents.txt    # List of external plugins to sync
├── scripts/
│   ├── generate-docs.py       # Generates AGENTS.md
│   └── sync-external.sh       # Syncs external agents from GitHub
├── Makefile                   # Installation automation
├── AGENTS.md                  # Auto-generated documentation
└── README.md                  # Engineer setup instructions
```

## Installation Targets

- `~/.claude/agents/commas/` ← all agents (custom + external)
- `~/.claude/commands/commas/` ← commands
- `~/.claude/commas/CLAUDE.md` ← org instructions (imported via `@~/.claude/commas/CLAUDE.md`)

## Agent File Format

Agents use YAML front matter followed by markdown:

```markdown
---
name: agent-name
description: Brief description
model: sonnet
---

# Agent Title

## Trigger
When to activate this agent.

## Instructions
Step-by-step instructions for the agent.
```

## Key Commands

```bash
make install        # Pull + symlink (for engineers)
make link           # Symlink only (for maintainers)
make sync-external  # Fetch external agents from wshobson/agents
make docs           # Regenerate AGENTS.md
```

## Adding New Agents

**Custom agents:**
1. Create `.md` file in `agents/`
2. Include YAML front matter with `name`, `description`, `model`
3. Run `make docs` to update documentation

**External agents:**
1. Edit `config/external-agents.txt` to add/remove plugins
2. Run `make sync-external`
