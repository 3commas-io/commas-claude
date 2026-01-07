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
│   └── external/              # Vendored from wshobson/agents (~31 agents)
├── commands/
│   └── external/              # External slash commands (~24 commands)
├── skills/
│   └── external/              # External knowledge modules (~44 skills)
│       └── {skill-name}/SKILL.md
├── config/
│   ├── CLAUDE.md              # Org-wide instructions
│   └── external-agents.txt    # Plugins to sync
├── scripts/
│   ├── generate-docs.py       # Generates AGENTS.md
│   └── sync-external.sh       # Syncs external content from GitHub
├── Makefile
├── AGENTS.md                  # Auto-generated documentation
└── README.md
```

## Installation Targets

- `~/.claude/agents/commas/` ← all agents (custom + external)
- `~/.claude/commands/commas/` ← commands (external)
- `~/.claude/skills/commas/` ← skills (external)
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
make sync-external  # Fetch agents, commands, skills from wshobson/agents
make docs           # Regenerate AGENTS.md
make status         # Show installed items count
```

## Adding New Agents

**Custom agents:**
1. Create `.md` file in `agents/`
2. Include YAML front matter with `name`, `description`, `model`
3. Run `make docs` to update documentation

**External agents:**
1. Edit `config/external-agents.txt` to add/remove plugins
2. Run `make sync-external`
