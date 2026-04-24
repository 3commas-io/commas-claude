---
name: release-notes
description: Generate business-level release note digests for a domain by gathering Jira tickets and GitHub PRs, correlating them, and producing a categorized summary. Use when the user asks to generate release notes, create a domain digest or changelog, see what shipped or changed, produce a weekly digest, or summarize what was released for a date range.
---

# Release Notes Generator

Generate a categorized, business-level digest of what shipped in a domain over a given date range. Pulls from Jira (done tickets) and GitHub (merged PRs), correlates them, and synthesizes a summary suitable for engineering leads and product managers.

## When to Use

User says something like:
- "generate release notes for platform domain for the last 3 days"
- "release notes for platform since March 24"
- "platform domain digest for this week"
- "what shipped in platform this week"

## Prerequisites

Before gathering any data, verify both integrations are working. Run these checks in parallel:

1. **Jira:** Call the Atlassian MCP `getAccessibleAtlassianResources` tool. If it fails, STOP and tell the user: "Atlassian MCP is not connected. Set up the Atlassian MCP integration before running release notes."
2. **GitHub:** Run `gh auth status` via Bash. If it fails, STOP and tell the user: "GitHub CLI is not authenticated. Run `gh auth login` first."

Both must succeed. No fallbacks. No partial results.

## Step 1: Parse Input

Extract two pieces of information from the user's request:

1. **Domain name** (e.g., "platform")
2. **Date range** — convert any relative dates to absolute `YYYY-MM-DD` format using today's date as reference:
   - "last 3 days" → `{today - 3}` to `{today}`
   - "since March 24" → `2026-03-24` to `{today}`
   - "this week" → Monday of current week to `{today}`

If the user doesn't specify a date range, ask them for one.

## Step 2: Load Domain Configuration

Read `skills/release-notes/domains.yaml`. Use the Glob tool to find the file: search for `**/skills/release-notes/domains.yaml`. This works regardless of where the plugin is installed.

If the file is not found, check for `domains.yaml.example` and tell the user: "Copy `domains.yaml.example` to `domains.yaml` and fill in your domain configuration."

Look up the requested domain name under the `domains` key. Extract:
- `jira.base_url` — the Jira instance URL (e.g., `https://your-instance.atlassian.net`)
- `jira.project` — the Jira project key (e.g., `PROJ`)
- `jira.done_statuses` — list of statuses that mean "done" (e.g., `["Done", "Resolved", "Closed"]`)
- `slack.channel` — the Slack channel to post to (e.g., `#platform-release-notes`)
- `github.org` — the GitHub organization (e.g., `your-org`)
- `github.repos` — list of repository names

If the domain is not found, list all available domains from the YAML and ask the user to pick one.

## Step 3: Gather Data

Fetch Jira tickets and GitHub PRs **in parallel** — issue all tool calls in a single message.

### Jira Query

Use the Atlassian MCP `searchJiraIssuesUsingJql` tool with this JQL:

```
project = {jira.project} AND status changed to ("{status1}", "{status2}", ...) DURING ("{start_date}", "{end_date}")
```

Replace `{jira.project}` with the project key and `{status1}`, etc. with each entry from `jira.done_statuses`. Replace dates with the parsed absolute dates.

From the results, extract for each ticket:
- **Key** (e.g., `PROJ-1234`)
- **Summary** (the ticket title)
- **Issue type** (Bug, Story, Task, etc.)
- **Description** (the ticket body — used for synthesis context)

### GitHub Queries

For **each repo** in `github.repos`, run via Bash:

```bash
gh pr list --repo {github.org}/{repo} --state merged --search "merged:{start_date}..{end_date}" --json number,title,body,mergedAt,headRefName --limit 100 --jq '[.[] | .body = (.body[:500])]'
```

This truncates PR bodies to 500 characters to avoid wasting context on verbose descriptions.

Issue all repo queries as separate Bash tool invocations alongside the Jira MCP call — all in a single response message for parallel execution.

If any repo returns exactly 100 PRs, warn the user that results may be truncated and suggest narrowing the date range.

From each PR result, extract:
- **number** (PR number)
- **title**
- **body** (PR description)
- **mergedAt** (merge timestamp)
- **headRefName** (branch name — used for Jira key correlation)
- **repo** (add this yourself — the repo name this PR came from, needed for building links)

### Error Handling

If any Jira query or any single `gh` call fails: **STOP immediately.** Show the user the exact error and which tool/repo failed. Do not continue with partial data.

## Step 4: Correlate Jira Tickets and PRs

For each merged PR, scan its `title` and `headRefName` (branch name) for Jira key patterns matching the domain's project. The pattern is: `{jira.project}-\d+` (e.g., `PROJ-123`, `PROJ-4567`).

Produce three buckets:

1. **Correlated changes:** A Jira ticket matched with one or more PRs. The ticket provides the business context ("why"), and the PRs provide the technical detail ("what"). Multiple PRs can link to the same ticket.
2. **Uncorrelated PRs:** Merged PRs where no Jira key was found in the title or branch name, or the key didn't match any ticket in the gathered set.
3. **Uncorrelated tickets:** Done Jira tickets with no matching PR.

All three buckets feed into the synthesis step. Uncorrelated PRs and uncorrelated tickets are classified into the same four categories using whatever information is available (PR title/body or ticket summary/type).

## Step 5: Synthesize the Digest

Using all three buckets from Step 4, produce a categorized release notes digest.

### Classification

Classify each change into one of these categories (skip empty categories in the output):
- **New Features** — new user-facing or system capabilities
- **Bug Fixes** — corrections to existing behavior
- **Improvements** — enhancements to existing features, performance, UX
- **Infrastructure / DevOps** — CI/CD, deployment, monitoring, config changes

Use the Jira issue type as a hint (Bug → Bug Fixes, Story → likely New Features), but override based on the actual content when the type is misleading.

### Noise Filtering

Omit these from the digest entirely:
- Dependency version bumps (unless security-related)
- CI/CD config tweaks with no user-facing impact
- Typo or formatting-only fixes
- Test-only changes (unless they indicate a significant quality issue that was fixed)

### Writing Rules

- **Readability first.** This is a digest for humans, not a link dump. Write 2-3 sentences per item explaining what changed, why it matters, and what impact it has. Use plain language a PM would understand.
- For correlated items: synthesize the Jira ticket summary and PR description into one coherent narrative. Do not list them separately.
- **Minimal links.** Include only the primary Jira ticket key in parentheses at the end — e.g., `(PROJ-123)`. Do NOT include PR links, multiple Jira links, or full URLs inline. If a change spans multiple tickets, mention the primary one and note "and related tickets."
- **No repo names** in the text — the audience thinks in features, not repos.
- **No implementation details** — don't mention specific code constructs, module names, file paths, or internal architecture unless it directly helps the reader understand the business impact.
- Tone: conversational, clear, no jargon. Write as if you're telling a colleague what shipped over coffee.
- When multiple PRs/tickets contribute to one logical feature, merge them into a single bullet — don't list each PR separately.
- **Documentation links.** When reviewing PR bodies and diffs, look for documentation changes — updated or new docs for APIs, strategy language (Starlark/quant scripts), configuration, user-facing guides, etc. If a change includes meaningful documentation, mention it in the item description and link to it (e.g., "See updated docs: <url>"). Use your judgment — only link docs that are useful to the reader (API references, language guides, migration notes). Don't link internal READMEs, changelogs, or trivial doc fixes.

### Volume Handling

If there are 30+ items after correlation, group related changes more aggressively. Combine PRs that address the same feature area into a single entry. The digest should be scannable in under 2 minutes.

### Output Format

```
## {Domain} Domain — Changes {start_date} to {end_date}

### New Features
- **{Title}** — 2-3 sentence description of what's new and why it matters. (PROJ-123)

### Bug Fixes
- **{Title}** — 2-3 sentence description of what was broken and how it's fixed. (PROJ-456)

### Improvements
- **{Title}** — 2-3 sentence description of what got better. (PROJ-789)

### Infrastructure / DevOps
- **{Title}** — 2-3 sentence description of what changed operationally.
```

### No Data

If no merged PRs and no done tickets exist in the date range, output:

> No notable changes in {domain} for {start_date} to {end_date}.

## Step 6: Post to Slack

After generating the digest, format it for Slack and post it to the domain's configured channel using the Slack MCP `slack_send_message` tool.

### Slack Formatting Rules

Slack uses mrkdwn, not Markdown. Convert the digest as follows:

**Headers:** Use bold text with emoji on its own line.
- `## Platform Domain — Changes ...` → `*📋 Platform Domain — Changes Mar 13 to Mar 27, 2026*`
- Category headers get their own emoji (see template below)

**Item titles are clickable links.** The title should link to the primary source:
- If a Jira ticket exists: `*<{jira.base_url}/browse/{KEY}|{Title}>*` — e.g., `*<https://your-instance.atlassian.net/browse/PROJ-100|New Feature Name>*`
- If no Jira ticket (uncorrelated PR): `*<https://github.com/{org}/{repo}/pull/{number}|{Title}>*`
- Every item must have a linked title. No item should be un-linked if a source exists.

**Item body:** Plain text, 2-3 sentences. The only exception for links in the body: if the change includes relevant documentation (API docs, strategy language guides, etc.), include a clickable link using Slack format `<url|link text>` — e.g., "See <https://docs.example.com/api|updated API docs>."

**No parenthetical ticket references.** In Slack format the title IS already the clickable link to the primary ticket. Do NOT add "(PROJ-123)" or "(PROJ-123, PROJ-456, ...)" at the end of the body text — that's redundant and clutters the message. If multiple tickets contributed to one item, that's fine — just link the primary one in the title and don't list the rest.

**No service or repo names.** Don't mention internal service names or repo names. Describe what the service does in plain terms instead — e.g., "the execution engine" not the repo name, "the data service" not its internal codename.

**Spacing:**
- One blank line between each bullet point for readability
- A divider line `———` between category sections
- One blank line before and after each divider

### Slack Output Template

```
*📋 {Domain} Domain — Changes {start_date} to {end_date}*

🚀 *New Features*

• *<jira_url|Title>* — 2-3 sentence description.

• *<jira_url|Title>* — 2-3 sentence description.

———

🐛 *Bug Fixes*

• *<jira_url|Title>* — 2-3 sentence description.

• *<pr_url|Title>* — 2-3 sentence description.

———

✨ *Improvements*

• *<jira_url|Title>* — 2-3 sentence description.

———

⚙️ *Infrastructure / DevOps*

• *<jira_url|Title>* — 2-3 sentence description.
```

### Posting

**Post as a single message.** The entire digest must be sent in one `slack_send_message` call — do NOT split it into multiple messages. Slack supports messages up to 40,000 characters; the digest will fit.

Use the Slack MCP `slack_send_message` tool to post the formatted message to the channel from `slack.channel` in the domain config.

If the user didn't ask to post to Slack, show the formatted digest and ask: "Want me to post this to {slack.channel}?"

If Slack MCP is not available, show the formatted Slack message to the user and tell them to copy-paste it manually.
