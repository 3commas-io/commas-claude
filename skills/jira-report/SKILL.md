# JIRA Work Report Skill

Generate and post work reports to JIRA issues based on the current Claude Code session context.

## Purpose

This skill analyzes the work completed during a Claude Code session and creates a structured report that can be posted as a comment to a JIRA issue. It's designed to be used at the end of a work day or when completing a task.

## When to Use

- At the end of a work day to summarize progress
- After completing a significant task or milestone
- When switching context to a different task
- Before wrapping up a feature branch

## Usage

The user will invoke this skill by asking Claude to create a JIRA report, for example:
- "Create a JIRA report for today's work"
- "Post a work update to JIRA"
- "Generate end-of-day report for APP-123"
- "Make a report to JIRA task"

## Report Generation Process

### 1. Analyze Session Context

Review the entire conversation history to identify:

- **Files Changed**: All files that were read, edited, or created
- **Tasks Completed**: What was accomplished
- **Commands Run**: Important commands executed (builds, tests, deployments)
- **Issues Resolved**: Bugs fixed or problems solved
- **Features Added**: New functionality implemented
- **Code Reviews**: Review comments and suggestions made
- **Documentation**: Docs written or updated
- **Time Indicators**: Estimate work duration based on conversation timestamps

### 2. Identify JIRA Issue

Determine which JIRA issue to report to:

1. **Explicit mention**: User specifies the issue key (e.g., "APP-123")
2. **Git branch**: Extract from current git branch name (e.g., `feature/APP-123_...`)
3. **Recent context**: Use the most recently discussed JIRA issue in the session
4. **Ask user**: If unclear, ask which issue to report to

### 3. Generate Report Structure

Create a structured markdown report with the following sections:

```markdown
## Work Summary - [Date]

### Completed
- [List of completed items with brief descriptions]
- [Include file references when relevant]

### Code Changes
- **Modified**: [list of modified files]
- **Created**: [list of new files]
- **Deleted**: [list of removed files if any]

### Testing & Quality
- [Test runs and results]
- [Code quality checks performed]
- [Issues found and resolved]

### Technical Details
[Optional: Include important technical decisions or implementation notes]

### Next Steps
- [Planned work for next session]
- [Any blockers or dependencies]

### Links
- [Merge requests]
- [Related documentation]
- [Other relevant links]
```

### 4. Review with User

Before posting to JIRA:
1. Show the generated report to the user
2. Ask if they want to make any modifications
3. Allow them to add additional context
4. Confirm the correct JIRA issue

### 5. Post to JIRA

Use the Atlassian MCP tools to post the report:
- Tool: `mcp__atlassian__addCommentToJiraIssue`
- Format: Use markdown that renders well in JIRA
- Include date/time stamp
- Add emoji for visual clarity

## Report Format Guidelines

### Keep it Concise
- Focus on what was accomplished, not every detail
- Use bullet points for readability
- Group related items together

### Be Specific
- Reference file paths: `src/components/Header.tsx:45`
- Include PR/MR numbers if available
- Mention test results or build status

### Highlight Impact
- What value was delivered
- What problems were solved
- What's unblocked now

### Note Blockers
- Clearly state any impediments
- Mention if waiting on external dependencies
- Flag issues that need attention

## Examples

### Example 1: Feature Development Report

```markdown
## Work Summary - January 16, 2026

### Completed
- Implemented user authentication flow with Auth0
- Created AuthGuard component for protected routes
- Added session management with React Query

### Code Changes
- **Modified**: `apps/web/src/App.tsx`, `apps/web/src/router.tsx`
- **Created**: `apps/web/src/components/AuthGuard/AuthGuard.tsx`
- Added 120 lines of code

### Technical Details
Implemented Auth0 integration with:
- JWT token validation
- Automatic token refresh
- Protected route wrapper component

### Next Steps
- Add user profile page
- Implement logout functionality
- Write tests for auth components

### Links
- PR: #45
```

### Example 2: Bug Fix Report

```markdown
## Work Summary - January 16, 2026

### Completed
- Fixed WebSocket connection timeout issue
- Added retry logic for failed connections
- Updated error handling in connection manager

### Code Changes
- **Modified**:
  - `apps/web/src/libs/webSocketService.ts:67-89`
  - `apps/web/src/contexts/WebSocketContext.tsx:34-45`
- **Created**: `apps/web/src/__tests__/webSocketRetry.spec.ts`

### Testing & Quality
- Added 12 unit tests for retry logic
- All tests passing (127/127)
- Manual testing confirmed fix

### Technical Details
Implemented exponential backoff for WebSocket retry:
- Max 3 retries
- Delay: 1s, 2s, 4s
- Only retry on network errors

### Issues Resolved
- Fixes intermittent connection failures during high load
- Improves user experience during network instability

### Next Steps
- Monitor error rates in production
- Consider applying same pattern to other connections
```

### Example 3: End of Day Report

```markdown
## End of Day Report - January 16, 2026

### Today's Progress

**Features**
- Added Claude Code skills to project
- Set up GitHub MCP integration
- Created CI/CD review pipeline

**Code Quality**
- Fixed 5 linting issues in web app
- Updated TypeScript types for API responses

**Testing**
- Fixed failing tests in auth module
- Added test coverage for new utilities

### Statistics
- Files modified: 12
- Tests added: 8
- Test coverage: +2.5%
- Build status: Passing

### Blockers
- Waiting for API key for Claude review pipeline
- Need access to staging environment

### Tomorrow's Plan
- Complete Claude review script implementation
- Review PR #48
- Update CLAUDE.md documentation
```

## Important Notes

### JIRA Markdown Compatibility

JIRA uses a different markdown flavor. Format accordingly:
- Use `*bold*` instead of `**bold**`
- Use `-` for bullet points
- Headers work with `##` syntax
- Code blocks use `{code}` blocks in some JIRA versions

### Privacy & Security

- Don't include sensitive information (API keys, tokens, passwords)
- Avoid posting internal URLs or IP addresses
- Review content before posting

### Frequency

Recommended reporting frequency:
- **Daily**: Brief end-of-day summary
- **Task completion**: Detailed report when closing issues
- **Weekly**: Comprehensive summary of week's work (optional)

## Integration with Git

When appropriate, correlate the report with git activity:
- Mention commit messages
- Reference branch names
- Link to pull requests
- Note if changes are pushed/deployed

## Error Handling

If unable to post to JIRA:
1. Show the generated report to the user
2. Provide instructions for manual posting
3. Save report to a local file as backup
4. Suggest checking MCP connection with `/mcp`

## Skill Activation

This skill should be activated when:
- User explicitly asks for a JIRA report
- User mentions "end of day" or "daily report"
- User says "report to JIRA" or similar phrases
- User asks to "summarize today's work"

## Success Criteria

A successful report should:
- Accurately reflect work completed in the session
- Be posted to the correct JIRA issue
- Be easy to read and understand
- Provide value to team members and project managers
- Include actionable next steps
