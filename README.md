# commas-claude

3Commas shared Claude Code configurations: agents, commands, and org-wide instructions.

## Setup

Clone this repository anywhere you like:

```bash
git clone git@github.com:3commas/commas-claude.git
cd commas-claude
make install
```

This creates symlinks from the repo to your `~/.claude/` directory:
- `~/.claude/agents/commas/` ← agents
- `~/.claude/commands/commas/` ← commands (slash commands)
- `~/.claude/skills/commas/` ← skills (knowledge modules)
- `~/.claude/commas/CLAUDE.md` ← org instructions

Your personal configurations remain intact.

## Updating

```bash
cd /path/to/commas-claude
make install
```

This pulls the latest changes and updates symlinks.

## Commands

| Command | Description |
|---------|-------------|
| `make install` | Pull latest + create symlinks (for engineers) |
| `make link` | Create symlinks only (for maintainers testing locally) |
| `make sync-external` | Fetch external agents, commands, skills from wshobson/agents |
| `make uninstall` | Remove all symlinks |
| `make status` | Show installed items |
| `make docs` | Regenerate AGENTS.md |
| `make help` | Show help |

## What's Included

### Agents

See **[AGENTS.md](AGENTS.md)** for the full list organized by category.

**Custom (3Commas):**
- `github-pr` - Creates GitHub PRs with Jira integration
- `jira-status-report` - Posts daily status reports to Jira

**External ([wshobson/agents](https://github.com/wshobson/agents)):**
- 30+ agents for Python, DevOps, databases, frontend, security, and more

### Commands (Slash Commands)

24 slash commands from external plugins, including:
- `/python-scaffold` - Scaffold Python projects
- `/tdd-red`, `/tdd-green`, `/tdd-refactor` - TDD workflow
- `/git-workflow` - Git operations
- See `commands/external/` for full list

### Skills (Knowledge Modules)

44 skills providing context and best practices:
- Python patterns (async, testing, packaging)
- Architecture patterns (microservices, CQRS, event sourcing)
- DevOps (GitOps, GitHub Actions, Terraform)
- Security (STRIDE, SAST, threat modeling)
- See `skills/external/` for full list

### Org-Wide Instructions

The file `config/CLAUDE.md` contains organization-wide instructions that are automatically imported into every engineer's Claude Code via `@~/.claude/commas/CLAUDE.md`.

## Contributing

### Add a custom agent

1. Create a new branch
2. Add your agent to `agents/`
3. Follow the existing format (YAML front matter + markdown)
4. Run `make docs` to update documentation
5. Open a PR

### Update external content

```bash
# Edit the plugin list
vim config/external-agents.txt

# Sync from upstream
make sync-external

# Commit changes
git add agents/external/ commands/external/ skills/external/
git commit -m "Update external agents, commands, skills"
```
