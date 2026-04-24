---
name: ship
description: Create a GitHub PR or GitLab MR, capture a Claude Impact Score, and post a work summary to the JIRA issue. Handles the full ship workflow — gather context, create PR/MR, prompt for Claude Impact Score, post JIRA comment. Works with both github.com (via `gh`) and GitLab instances (via `glab`). Can be extended with project-specific team members and JIRA configuration.
---

# Ship Skill

Create a GitHub PR or GitLab MR, capture a Claude Impact Score, and post a work summary to the JIRA issue. Order: PR/MR first, then Claude Impact Score comment, then JIRA summary that references the PR/MR.

Platform is auto-detected from the `origin` remote — github.com → GitHub path (`gh` CLI), any `gitlab.*` host → GitLab path (`glab` CLI).

## When to Use

- User says "ship", "create pr", "create mr", "ship it", "pr + jira", "mr + jira"
- User invokes `/ship`
- End of a feature branch workflow

## Arguments

Optional arguments override auto-detection:
- `--reviewer <name>` or `-r <name>` — override reviewer (partial name match against team list)
- `--assignee <name>` or `-a <name>` — override assignee
- `--claude-score <N>` or `--score <N>` — pre-set the Claude Impact Score (skips the interactive prompt). Must be an integer in `-3..+3`.
- `--no-claude-score` — skip the Claude Impact Score prompt entirely. CI will fail the PR/MR until a `CLAUDE: X` comment is added manually.
- `--no-jira` — skip JIRA summary
- `--no-pr` — skip PR/MR creation (only post JIRA summary)
- `--platform <github|gitlab>` — force platform detection (rarely needed; use only if auto-detection picks the wrong one)
- Bare argument — treated as JIRA issue key if it matches the project pattern

## Team Members

**This section should be overridden in the project-level skill.** Map git usernames to platform handles and real names for auto-assigning:

| Git username | GitHub handle | GitLab handle | Name |
|--------------|---------------|---------------|------|
| `example-user` | `example-gh` | `example.gl` | Name |

When the user says a name (e.g., "assign to me", "john reviews"), match it against the team list:
- "me" / "myself" → resolve via `gh api user` (GitHub) or `glab api user` (GitLab) to get the current login
- Partial name match → e.g., "john" → `john-doe`
- Exact platform username also accepted

Pick the handle from the column matching the detected platform.

## Step 0 — Detect Platform

Look at the `origin` remote URL to decide which CLI to use:

```bash
REMOTE_URL=$(git config --get remote.origin.url)
case "$REMOTE_URL" in
  *github.com*)      PLATFORM=github ;;
  *gitlab.*|*gitlab*) PLATFORM=gitlab ;;
  *) echo "Unknown remote host: $REMOTE_URL"; exit 1 ;;
esac
```

If the user passed `--platform`, use that instead. The rest of the skill branches on `$PLATFORM`.

Also confirm the matching CLI is installed and authenticated:

- **GitHub**: `gh auth status` — must be logged in
- **GitLab**: `glab auth status` — must be logged in to the correct host

If the CLI is missing, tell the user exactly what to install (`brew install gh` / `brew install glab`) and where to get auth set up. Don't try to proceed.

## Step 1 — Gather Context

Run these commands in parallel:

```bash
git status                          # Untracked / modified files
git diff --stat                     # Unstaged changes summary
git log --oneline main..HEAD        # Commits on this branch
git diff main...HEAD --stat         # Full diff stat vs main
git branch --show-current           # Current branch name
```

(If the default branch isn't `main` — e.g., `master`, `develop` — substitute accordingly. Detect via `git symbolic-ref refs/remotes/origin/HEAD`.)

Extract the JIRA issue key from:
1. Explicit argument (e.g., `PROJ-82`)
2. Branch name pattern: `feature/PROJ-XXX_...` or `fix/PROJ-XXX_...`
3. Ask user if not found

## Step 2 — Warn About Uncommitted Changes

If `git status` shows uncommitted changes:
- Show the user what's uncommitted
- Ask if they want to commit first or proceed without those changes
- Do NOT auto-commit

## Step 3 — Create the PR/MR

### Determine assignee and reviewer

- **Assignee**: Default to current login. Resolve via `gh api user` (GitHub) or `glab api user` (GitLab). Override with `--assignee` or if user says "assign to X".
- **Reviewer**: If not specified, pick the most likely reviewer from the team list (not the assignee). Override with `--reviewer`.

### Build PR/MR content

Analyze ALL commits on the branch (`git log main..HEAD`) and the full diff (`git diff main...HEAD`).

**PR/MR title**: Short (under 70 chars), imperative mood. Prefix with JIRA key: `PROJ-XXX: <description>`.

**PR/MR body** format:

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

### Push the branch first

Before creating the PR/MR, make sure the branch is on the remote:

```bash
git push -u origin <branch-name>
```

### Create the PR/MR

**GitHub** (`$PLATFORM = github`):

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

**GitLab** (`$PLATFORM = gitlab`):

```bash
glab mr create \
  --title "PROJ-XXX: <title>" \
  --assignee <gitlab-username> \
  --reviewer <gitlab-username> \
  --source-branch "$(git branch --show-current)" \
  --target-branch main \
  --remove-source-branch \
  --description "$(cat <<'EOF'
<body content>
EOF
)"
```

(On GitLab, swap `main` for the actual default branch if different — e.g., `master`, `develop`.)

Save the PR/MR URL and its number/iid from the output — both are needed for the next steps.

## Step 4 — Ask for Claude Impact Score

Every PR/MR must carry a Claude Impact Score: a single integer from **-3** to **+3** that captures how much Claude contributed to the work. CI enforces this on every PR/MR, so posting it here avoids a CI failure and a bot reminder comment.

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

### Propose a score and justification based on session context

Before asking the user, synthesize what actually happened in this session and offer a draft:

- **Suggested score**: look at how much of the diff Claude produced vs. edited-after-Claude, how many course-corrections the user made, whether the user expressed frustration or satisfaction, whether generated code required significant rework. Pick a starting score.
- **Suggested justification** (one line): summarise what Claude actually did for this PR — the concrete thing, not a category. Examples: "Claude drafted the new component and tests; I adjusted the RTK Query cache tags", "Claude proposed the migration but got transaction boundaries wrong twice".

Present it like:

```
Based on this session:
  Score: 2
  Justification: Claude drafted the new component and tests; I adjusted the RTK Query cache tags.

What's your Claude Impact Score for this PR? (accept / different score / edit justification)
```

If there's no useful context (e.g., user ran `/ship` in a fresh session), skip the draft and just ask for the score.

### Validate

- Must be an integer
- Must be in range `-3..+3` inclusive
- If invalid, re-prompt with a one-line reminder of the valid range

Negative scores are valid and expected. Do not nudge the user upward — honest data is the point. The suggested score is a draft; always accept what the user types without pushing back.

### Post the comment

Post the `CLAUDE: X` line on its own, then append the justification (if any) on the next line.

**GitHub** (`$PLATFORM = github`):

```bash
gh pr comment <pr-number> --body "CLAUDE: <score>
<justification>"
```

**GitLab** (`$PLATFORM = gitlab`):

```bash
glab mr note <mr-iid> --message "CLAUDE: <score>
<justification>"
```

If the user declined the justification, post just the score line:

```bash
# GitHub
gh pr comment <pr-number> --body "CLAUDE: <score>"

# GitLab
glab mr note <mr-iid> --message "CLAUDE: <score>"
```

The `CLAUDE: X` line must match the CI-enforced format exactly: capital `CLAUDE`, colon, single space, integer. The justification goes on a separate line so it doesn't confuse the regex.

Confirm to the user: `✓ Posted CLAUDE: <score> on <pr-or-mr-url>`

### If the user declines or skips

If the user says "skip", "no", or passed `--no-claude-score`, show this warning and continue the workflow:

```
⚠️  No Claude Impact Score posted.
   CI will fail this PR/MR until a CLAUDE: X comment is added.
   Post it manually with:
     # GitHub
     gh pr comment <pr-number> --body "CLAUDE: <score>"
     # GitLab
     glab mr note <mr-iid> --message "CLAUDE: <score>"
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
- PR/MR: <pr-or-mr-url>
```

Keep it concise. Focus on what was accomplished, not every detail.

### If Atlassian MCP fails

1. Show the generated JIRA comment to the user in a code block
2. Tell them to post it manually
3. Suggest running `/mcp` to reconnect

## Step 6 — Report Results

Output a summary:
```
Platform: <github|gitlab>
PR/MR: <url>
Claude Impact Score: <score> posted (or "skipped — post manually")
JIRA: PROJ-XXX comment posted (or "manual post needed")
Assignee: <name>
Reviewer: <name>
```

## Error Handling

- **No commits on branch**: Warn and abort — nothing to ship.
- **PR/MR already exists**: Show the existing URL. Ask if user wants to update the JIRA comment only.
- **Push fails**: Show the error. Don't retry automatically.
- **CLI not installed / not authenticated**: Stop with clear install + auth instructions (`gh auth login` / `glab auth login --hostname <host>`). Never silently fall back to the other platform.
- **Platform auto-detection ambiguous**: If `origin` URL matches neither github.com nor any gitlab host, ask the user to pass `--platform`.
- **Atlassian MCP down**: Fall back to showing the comment for manual posting.

## Important Notes

- NEVER force-push
- NEVER amend commits
- NEVER skip pre-commit hooks
- Always push before creating the PR/MR
- Order is fixed: PR/MR → Claude Impact Score comment → JIRA summary. Each later step depends on the PR/MR URL / number.
- The Claude Impact Score comment must be posted on the PR (GitHub) or MR (GitLab), not on a specific code line — CI only scans PR/MR-level comments and the PR/MR description.
- Don't include sensitive info (API keys, tokens) in PR/MR or JIRA
