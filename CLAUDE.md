# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains 3Commas company-wide Claude Code configurations that are symlinked to engineers' `~/.claude/` directories via `make install`.

## Repository Structure

```
commas-claude/
├── agents/           # Custom agent definitions (.md files with YAML front matter)
├── commands/         # Custom slash commands/skills
├── Makefile          # Installation automation
└── README.md         # Engineer setup instructions
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

## Installation

The Makefile symlinks individual files to `~/.claude/`:
- `agents/*.md` → `~/.claude/agents/`
- `commands/*` → `~/.claude/commands/`

This preserves engineers' personal configurations while adding shared resources.

## Adding New Agents

1. Create a new `.md` file in `agents/`
2. Include YAML front matter with `name`, `description`, `model`
3. Write clear trigger conditions and step-by-step instructions
4. Test locally before committing
