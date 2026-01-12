# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository is a Claude Code plugin marketplace containing 3Commas custom agents, commands, and skills, plus vendored external content from wshobson/agents.

## Repository Structure

```
commas-claude/
├── .claude-plugin/
│   └── marketplace.json       # Plugin marketplace definition
├── agents/                    # ALL agents (flat structure)
│   ├── github-pr.md           # Custom 3Commas agent
│   ├── jira-status-report.md  # Custom 3Commas agent
│   ├── python-pro.md          # Vendored external
│   └── ...                    # (~40 total)
├── commands/                  # ALL slash commands (~31)
│   ├── tdd-red.md
│   └── ...
├── skills/                    # ALL skills (~56)
│   ├── 3commas-guidelines/    # Custom 3Commas skill
│   │   └── SKILL.md
│   ├── api-design-principles/
│   └── ...
├── config/
│   ├── CLAUDE.md              # Org-wide instructions
│   └── external-agents.txt    # Plugins to sync from wshobson/agents
├── scripts/
│   ├── generate-docs.py       # Generates AGENTS.md
│   └── sync-external.sh       # Syncs external content
├── Makefile
├── AGENTS.md                  # Auto-generated documentation
└── README.md
```

## Installation

This repo is a Claude Code plugin. Install via:

```
/plugin marketplace add 3commas/commas-claude
/plugin install 3commas@3commas
```

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
make install        # Show installation instructions
make sync-external  # Fetch content from wshobson/agents + regenerate docs
make docs           # Regenerate AGENTS.md only
```

## Adding New Agents

**Custom agents:**
1. Create `.md` file in `agents/`
2. Include YAML front matter with `name`, `description`, `model`
3. Run `make docs` to update documentation

**External agents:**
1. Edit `config/external-agents.txt` to add/remove plugins
2. Run `make sync-external`
