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

### Agents (43)

See **[AGENTS.md](AGENTS.md)** for the full list.

**Custom (3Commas):**
- `github-pr` - Creates GitHub PRs with Jira integration
- `jira-status-report` - Posts daily status reports to Jira

**External ([wshobson/agents](https://github.com/wshobson/agents)):**
- 40+ agents for Python, DevOps, databases, frontend, security, and more

### Commands (32)

Slash commands including:
- `/tdd-red`, `/tdd-green`, `/tdd-refactor` - TDD workflow
- `/python-scaffold`, `/typescript-scaffold` - Project scaffolding
- `/git-workflow` - Git operations
- `/doc-generate` - Documentation generation

### Skills (64)

Knowledge modules for:
- `release-notes` - Generate business-level release note digests from Jira + GitHub, post to Slack
- `write-tech-design` - Write technical design documents
- `ship` - Create a PR, capture a Claude Impact Score comment on it, then post a JIRA summary
- `notion-docs` - Generate and push documentation to Notion
- `jira-report` - Generate Jira status reports
- `optimize-claude-md` - Optimize CLAUDE.md files
- `3commas-guidelines` - Organization coding standards
- Python patterns (async, testing, packaging)
- Architecture patterns (microservices, CQRS, event sourcing)
- DevOps (GitOps, GitHub Actions, Terraform)
- Security (STRIDE, SAST, threat modeling)

## Using the Release Notes Skill

Generate a business-level digest of what shipped across a domain (Jira tickets + GitHub PRs), with optional Slack posting.

### Quick start

In Claude Code, say:
```
generate release notes for platform domain for the last 7 days
```

Or with Slack posting:
```
generate release notes for platform since Monday and post to slack
```

### Local development testing

To test the skill from a local checkout without pushing:

```bash
claude --plugin-dir /path/to/commas-claude
```

Then invoke it normally. After editing skill files, run `/reload-plugins` to pick up changes without restarting.

### Prerequisites

- **Jira:** Atlassian MCP integration must be connected
- **GitHub:** `gh` CLI must be authenticated (`gh auth login`)
- **Slack (optional):** Slack MCP integration for posting digests

### Domain configuration

Copy the example config and fill in your details:

```bash
cp skills/release-notes/domains.yaml.example skills/release-notes/domains.yaml
```

Then edit `domains.yaml` with your Jira project, GitHub repos, and Slack channel. The real `domains.yaml` is gitignored — only the example file is committed.

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
