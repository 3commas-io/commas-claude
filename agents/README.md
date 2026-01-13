# Agents

This directory contains Claude Code agents from two sources:

## Custom 3Commas Agents
- `github-pr.md` - GitHub PR creation agent
- `jira-status-report.md` - Jira status reporting agent

## Vendored External Agents (56)

Synced from [wshobson/agents](https://github.com/wshobson/agents) (MIT License).

| Attribute | Value |
|-----------|-------|
| **Last synced** | 2026-01-13 12:14 UTC |
| **Source commit** | [2d769d4](https://github.com/wshobson/agents/commit/2d769d4) |

### Updating

```bash
make sync-external
```

To add/remove plugins, edit `config/external-agents.txt` and re-run sync.
