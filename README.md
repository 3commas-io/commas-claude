# commas-claude

3Commas shared Claude Code configurations: agents, commands, and prompts for company-wide use.

## Setup

Clone this repository anywhere you like:

```bash
git clone git@github.com:3commas/commas-claude.git
cd commas-claude
make install
```

This creates symlinks from the repo to your `~/.claude/` directory, so your personal configurations remain intact.

## Updating

To get the latest agents and commands:

```bash
cd /path/to/commas-claude
make install
```

This pulls the latest changes and updates symlinks.

## Available Commands

```bash
make install    # Install/update (pulls latest first)
make link       # Create symlinks only (for maintainers testing locally)
make uninstall  # Remove all symlinks
make status     # Show installed items
make docs       # Generate AGENTS.md documentation
make help       # Show help
```

## What's Included

### Agents

See **[AGENTS.md](AGENTS.md)** for the full list of 35+ available agents organized by category:

- 🏢 3Commas (github-pr, jira-status-report)
- 🎸 Django, 💎 Rails, 🟠 Laravel
- 🐍 Python, ⚛️ Frontend (React, Vue)
- 🔍 Code Quality, ⚡ Performance
- 🎯 Orchestration, 🛡️ DevOps & Quality
- And more...

### Commands

Coming soon.

## Contributing

1. Create a new branch
2. Add your agent to `agents/` or command to `commands/`
3. Follow the existing format (YAML front matter + markdown)
4. Run `make docs` to update documentation
5. Open a PR with a description of the use case
