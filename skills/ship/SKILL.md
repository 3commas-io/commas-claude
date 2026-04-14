---
name: ship
description: Create a GitHub PR and post a work summary to the JIRA issue. Handles the full ship workflow — gather context, create PR, post JIRA comment. Can be extended with project-specific team members and JIRA configuration.
---

# Ship Skill

Create a GitHub PR and post a work summary to the JIRA issue. PR is always created first, then JIRA summary references it.

## When to Use

- User says "ship", "create pr", "ship it", "pr + jira"
- User invokes `/ship`
- End of a feature branch workflow

## Arguments

Optional arguments override auto-detection:
- `--reviewer <name>` or `-r <name>` — override reviewer (partial name match against team list)
- `--assignee <name>` or `-a <name>` — override assignee
- `--no-jira` — skip JIRA summary
- `--no-pr` — skip PR creation (only post JIRA summary)
- Bare argument — treated as JIRA issue key if it matches the project pattern

## Team Members

**This section should be overridden in the project-level skill.** Map git usernames to GitHub handles and real names for auto-assigning:

| Git / GitHub username | Name |
|-----------------------|------|
| `example-user`        | Name |

When the user says a name (e.g., "assign to me", "john reviews"), match it against the team list:
- "me" / "myself" → resolve via `gh api user` to get the current GitHub login
- Partial name match → e.g., "john" → `john-doe`
- Exact GitHub username also accepted

## Step 1 — Gather Context

Run these commands in parallel:

```bash
git status                          # Untracked / modified files
git diff --stat                     # Unstaged changes summary
git log --oneline main..HEAD        # Commits on this branch
git diff main...HEAD --stat         # Full diff stat vs main
git branch --show-current           # Current branch name
```

Extract the JIRA issue key from:
1. Explicit argument (e.g., `PROJ-82`)
2. Branch name pattern: `feature/PROJ-XXX_...` or `fix/PROJ-XXX_...`
3. Ask user if not found

## Step 2 — Warn About Uncommitted Changes

If `git status` shows uncommitted changes:
- Show the user what's uncommitted
- Ask if they want to commit first or proceed without those changes
- Do NOT auto-commit

## Step 3 — Create the PR

### Determine assignee and reviewer

- **Assignee**: Default to current `gh api user` login. Override with `--assignee` or if user says "assign to X".
- **Reviewer**: If not specified, pick the most likely reviewer from the team list (not the assignee). Override with `--reviewer`.

### Build PR content

Analyze ALL commits on the branch (`git log main..HEAD`) and the full diff (`git diff main...HEAD`).

**PR title**: Short (under 70 chars), imperative mood. Prefix with JIRA key: `PROJ-XXX: <description>`.

**PR body** format:

```markdown
[PROJ-XXX](<jira-browse-url>/PROJ-XXX)

## Summary
- [2-4 bullet points describing what changed and why]

## Changes
- **Created**: [new files]
- **Modified**: [changed files]
- **Deleted**: [removed files]

## Test plan
- [ ] [Verification steps]
```

The first line must always be the Jira issue link using the key extracted from the branch name.

### Create the PR

```bash
gh pr create \
  --title "PROJ-XXX: <title>" \
  --assignee <github-username> \
  --reviewer <github-username> \
  --body "$(cat <<'EOF'
<body content>
EOF
)"
```

Push the branch first if it hasn't been pushed or is behind remote:

```bash
git push -u origin <branch-name>
```

Save the PR URL from the output for the JIRA step.

## Step 4 — Post JIRA Summary

Use `mcp__atlassian__getAccessibleAtlassianResources` to get the cloud ID, then `mcp__atlassian__addCommentToJiraIssue` to post.

### JIRA comment format

```markdown
## Work Summary

### Completed
- [List of completed items with brief descriptions]

### Code Changes
- **Created**: [new files]
- **Modified**: [changed files]
- **Deleted**: [removed files]

### Testing & Quality
- All checks pass (typecheck, lint, stylelint, tests, knip)

### Links
- PR: <pr-url>
```

Keep it concise. Focus on what was accomplished, not every detail.

### If Atlassian MCP fails

1. Show the generated JIRA comment to the user in a code block
2. Tell them to post it manually
3. Suggest running `/mcp` to reconnect

## Step 5 — Report Results

Output a summary:
```
PR: <url>
JIRA: PROJ-XXX comment posted (or "manual post needed")
Assignee: <name>
Reviewer: <name>
```

## Error Handling

- **No commits on branch**: Warn and abort — nothing to ship.
- **PR already exists**: Show the existing PR URL. Ask if user wants to update the JIRA comment only.
- **Push fails**: Show the error. Don't retry automatically.
- **Atlassian MCP down**: Fall back to showing the comment for manual posting.

## Important Notes

- NEVER force-push
- NEVER amend commits
- NEVER skip pre-commit hooks
- Always push before creating the PR
- PR creation comes BEFORE JIRA summary (JIRA needs the PR link)
- Don't include sensitive info (API keys, tokens) in PR or JIRA