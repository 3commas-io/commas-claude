---
name: ship
description: Create a GitHub PR, capture a Claude Impact Score, and post a work summary to the JIRA issue. Handles the full ship workflow — gather context, create PR, prompt for Claude Impact Score, post JIRA comment. Can be extended with project-specific team members and JIRA configuration.
---

# Ship Skill

Create a GitHub PR, capture a Claude Impact Score, and post a work summary to the JIRA issue. Order: PR first, then Claude Impact Score comment on the PR, then JIRA summary that references the PR.

## When to Use

- User says "ship", "create pr", "ship it", "pr + jira"
- User invokes `/ship`
- End of a feature branch workflow

## Arguments

Optional arguments override auto-detection:
- `--reviewer <name>` or `-r <name>` — override reviewer (partial name match against team list)
- `--assignee <name>` or `-a <name>` — override assignee
- `--claude-score <N>` or `--score <N>` — pre-set the Claude Impact Score (skips the interactive prompt). Must be an integer in `-3..+3`.
- `--no-claude-score` — skip the Claude Impact Score prompt entirely. CI will fail the PR until a `CLAUDE: X` comment is added manually.
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

Save the PR URL and number from the output — both are needed for the next steps.

## Step 4 — Ask for Claude Impact Score

Every PR must carry a Claude Impact Score: a single integer from **-3** to **+3** that captures how much Claude contributed to the work. CI enforces this on every PR, so posting it here avoids a CI failure and a bot reminder comment.

### Skip this step if

- User passed `--no-claude-score` — warn and continue (see below)
- User passed `--claude-score <N>` / `--score <N>` — validate `N` is an integer in `-3..+3`, then skip the prompt and go straight to "Post the comment"

### Display the scale

Show this compact table, then ask for a score:

```
Rate Claude's impact on this PR:

   3  Claude did all the work. You reviewed and made tiny or no adjustments.
   2  Claude did most of the work. You guided it, it delivered.
   1  Claude helped with specific parts, but you did most of the work.
   0  Claude was not used on this task at all.
  -1  Claude's suggestions needed significant rework.
  -2  Claude actively hindered progress in places.
  -3  Claude wasted your time. You'd have been faster without it.
```

Then ask: **"What's your Claude Impact Score for this PR?"**

### Validate

- Must be an integer
- Must be in range `-3..+3` inclusive
- If invalid, re-prompt with a one-line reminder of the valid range

Negative scores are valid and expected. Do not nudge the user upward — honest data is the point.

### Post the comment

```bash
gh pr comment <pr-number> --body "CLAUDE: <score>"
```

The comment must match the CI-enforced format exactly: capital `CLAUDE`, colon, single space, integer. Do not wrap it, prefix it, or add other text on the same line.

Confirm to the user: `✓ Posted CLAUDE: <score> on <pr-url>`

### If the user declines or skips

If the user says "skip", "no", or passed `--no-claude-score`, show this warning and continue the workflow:

```
⚠️  No Claude Impact Score posted.
   CI will fail this PR until a CLAUDE: X comment is added.
   Post it manually with:
     gh pr comment <pr-number> --body "CLAUDE: <score>"
```

## Step 5 — Post JIRA Summary

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

## Step 6 — Report Results

Output a summary:
```
PR: <url>
Claude Impact Score: <score> posted (or "skipped — post manually")
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
- Order is fixed: PR → Claude Impact Score comment → JIRA summary. Each later step depends on the PR URL / number.
- The Claude Impact Score comment must be posted on the PR (GitHub) or MR (GitLab), not on a specific code line — CI only scans PR-level comments and the PR description.
- Don't include sensitive info (API keys, tokens) in PR or JIRA