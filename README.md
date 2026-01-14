# 3commas

3Commas Claude Code plugin: agents, commands, skills, and org-wide guidelines.

## Installation

Run these commands in Claude Code:

```
/plugin marketplace add 3commas-io/commas-claude
/plugin install 3commas@3commas
```

### Migrating from old version

If you previously used `make install` (symlink-based), run cleanup first:

```bash
cd /path/to/commas-claude
git pull
make cleanup
```

Then install the new plugin version in Claude Code.

### Alternative: settings.json

Or add to `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "3commas": {
      "source": { "source": "github", "repo": "3commas-io/commas-claude" }
    }
  },
  "enabledPlugins": { "3commas@3commas": true }
}
```

## What's Included

### Agents (40+)

See **[AGENTS.md](AGENTS.md)** for the full list.

**Custom (3Commas):**
- `github-pr` - Creates GitHub PRs with Jira integration
- `jira-status-report` - Posts daily status reports to Jira

**External ([wshobson/agents](https://github.com/wshobson/agents)):**
- 38+ agents for Python, DevOps, databases, frontend, security, and more

### Commands (32)

Slash commands including:
- `/tdd-red`, `/tdd-green`, `/tdd-refactor` - TDD workflow
- `/python-scaffold`, `/typescript-scaffold` - Project scaffolding
- `/git-workflow` - Git operations
- `/doc-generate` - Documentation generation

### Skills (57)

Knowledge modules for:
- `3commas-guidelines` - Organization coding standards
- Python patterns (async, testing, packaging)
- Architecture patterns (microservices, CQRS, event sourcing)
- DevOps (GitOps, GitHub Actions, Terraform)
- Security (STRIDE, SAST, threat modeling)

## For Maintainers

### Update external content

```bash
# Edit the plugin list
vim config/external-agents.txt

# Sync from upstream
make sync-external
```

> **Note:** Some external agents from wshobson/agents may lack YAML front matter and won't appear in the generated `AGENTS.md`. These agents still work but aren't documented. To fix, submit a PR upstream to add front matter.

### Add a custom agent

1. Add your agent to `agents/`
2. Follow the existing format (YAML front matter + markdown)
3. Run `make docs` to update documentation
4. Open a PR

### Available commands

| Command | Description |
|---------|-------------|
| `make install` | Show installation instructions |
| `make cleanup` | Remove old symlink-based installation |
| `make sync-external` | Sync external content from wshobson/agents |
| `make docs` | Regenerate AGENTS.md |
