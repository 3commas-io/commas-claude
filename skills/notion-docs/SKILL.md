---
name: notion-docs
description: Interact with Notion workspace to search, read, create, and update documentation. Supports syncing local markdown files to Notion via notion-sync.yaml config. Can be extended with project-specific workflows and integration points.
---

# Notion Documentation Skill

Interact with Notion workspace to search, read, create, and update documentation, reports, and knowledge base content.

## When to Use

- **Sync local docs to Notion** after creating or updating files in `docs/` folder
- **Search existing documentation** before implementing new features
- **Create documentation** for new features, APIs, or processes
- **Update documentation** when features change or improve
- **Read technical designs** and architectural decisions
- **Access team knowledge** like weekly reports, guidelines, or standards
- **Create meeting notes** and project status updates
- **Document incidents** and post-mortems

## Usage

The user will invoke this skill by asking to interact with Notion:
- "Sync docs/ARCHITECTURE.md to Notion"
- "Sync all docs to Notion"
- "Search Notion for rate limiting documentation"
- "Create a Notion page documenting this feature"
- "Update the guide in Notion"
- "Find all pages about Redis integration"

## Sync Local Documentation

This skill supports syncing markdown files from the `docs/` folder to Notion pages.

### Configuration File

The sync configuration is stored in `docs/notion-sync.yaml`:

```yaml
# Parent page for all documentation (optional)
parent_page_id: null  # Set to page ID like "abc123def456..."

# File-to-page mapping
pages:
  docs/ARCHITECTURE.md: null  # Set page ID after first sync
  docs/DEPLOYMENT.md: abc123def456...  # Existing page ID

# Settings
settings:
  create_if_missing: true
  default_parent: null
```

### Sync Workflow

**When user asks to sync a file:**

1. **Read the local file**
2. **Check config for existing page ID** in `docs/notion-sync.yaml`
3. **If page ID exists — Update the page:**
   - Use `mcp__notion__notion-fetch` to get current page
   - Use `mcp__notion__notion-update-page` with command: `replace_content`
   - Pass the markdown content as `new_str`
4. **If page ID is null — Create new page:**
   - Use `mcp__notion__notion-create-pages`
   - Set title from first H1 heading or filename
   - Pass markdown content
   - Update `notion-sync.yaml` with new page ID
5. **Report result** with the Notion page URL

**Sync all configured files:**
1. Read `docs/notion-sync.yaml`
2. For each file in pages: read file, update or create Notion page
3. Update config if new pages were created
4. Report summary of synced files

### Important Notes

- **Markdown compatibility**: Local markdown is mostly compatible with Notion
- **Mermaid diagrams**: Notion renders mermaid code blocks as diagrams
- **Tables**: Standard markdown tables work in Notion
- **Code blocks**: Language tags are preserved for syntax highlighting
- **Links**: Internal doc links should be updated to Notion page links after sync

### After Creating/Updating docs/

**IMPORTANT**: When you create or modify files in the `docs/` folder, ask the user if they want to sync to Notion.

**IMPORTANT**: The Notion MCP tools cannot change sharing settings. After syncing, remind the user:
> "Remember to make this page public in Notion: Share → Share to web"

## Available Operations

### 1. Search Notion Content

**Tool:** `mcp__notion__notion-search`

**Search strategies:**
- Specific documents: "Search Notion for Week 3 engineering report"
- Technical topics: "Find documentation about WebSocket implementation"
- By date/creator: "Find pages about authentication created this month"
- In specific teamspace: "Search Engineering teamspace for Redis patterns"

### 2. Read Page Content

**Tool:** `mcp__notion__notion-fetch`

**When to read:**
- Review technical designs before implementation
- Access team guidelines and standards
- Read weekly reports and status updates
- Get API documentation

**Strategy:** Search first, then fetch the most relevant page, present formatted summary.

### 3. Create New Pages

**Tool:** `mcp__notion__notion-create-pages`

**Creation guidelines:**
- Clear title describing the content
- Proper heading hierarchy (H1, H2, H3)
- Code blocks with syntax highlighting
- Tables for structured data
- Links to related pages

### 4. Update Existing Pages

**Tool:** `mcp__notion__notion-update-page`

**Strategy:**
1. Always read first to see current state
2. Make targeted changes
3. Preserve existing structure and formatting
4. Add comment if making major changes

### 5. Work with Databases

**Tools:**
- `mcp__notion__notion-fetch` — Get database schema
- `mcp__notion__notion-query-data-sources` — Query database content
- `mcp__notion__notion-create-pages` — Add pages to database

### 6. Post Comments

**Tool:** `mcp__notion__notion-create-comment`

**When to comment:** Provide feedback, add updates, respond to questions, note changes.

## Content Quality Guidelines

### Writing Documentation

**Structure:**
- Start with clear overview/purpose
- Use progressive disclosure (simple → detailed)
- Include practical examples
- Add troubleshooting section
- Provide links to related docs

**Formatting:**
- Use headings to organize content
- Code blocks for all code examples
- Tables for comparisons/options
- Bullet points for lists
- Links to related pages

### Page Organization

**Naming conventions:**
- Clear, descriptive titles
- Include context: "WebSocket Reconnection Logic"
- Not: "Reconnection" or "New Feature"

**Linking strategy:**
- Link to related documentation
- Reference tech designs
- Connect to JIRA tickets
- Cross-reference similar features

## Search Strategies

### Effective Searching

**Be specific:**
- Good: "WebSocket reconnection implementation Week 3"
- Bad: "websocket"

**Use filters:**
- By date: "Find documentation created in January 2026"
- By creator: "Find pages created by Engineering team"
- By teamspace: "Search Engineering Docs teamspace"

### When Search Returns Nothing

1. Try broader terms
2. Search related topics
3. Try different wording
4. Ask user for more context
5. Suggest creating new documentation

## Notion-Flavored Markdown Reference

### Supported Features

**Basic formatting:** bold, italic, strikethrough, inline code

**Headings:** `#`, `##`, `###`

**Lists:** bullet, numbered, checkboxes (`- [ ]`, `- [x]`)

**Code blocks:** with language tags for syntax highlighting

**Tables:** standard markdown table syntax

**Links:** `[text](URL)` and `<mention-page url="{{URL}}">Title</mention-page>`

**Advanced:** toggles, dividers (`---`), empty blocks (`<empty-block/>`), columns

## Error Handling

### Cannot Find Content
1. Try broader search terms
2. Search in different teamspace
3. Ask user for more specific details
4. Offer to create new documentation

### Cannot Create/Update
1. Check permissions
2. Verify parent page exists
3. Ensure page URL is valid
4. Check Notion connection with `/mcp`
5. Provide content to user for manual entry

## Privacy & Security

**Do not include:** API keys, tokens, credentials, personal user data, internal IP addresses

**Safe to include:** Code examples (non-sensitive), public API documentation, architecture patterns, best practices, troubleshooting guides, team processes

## Best Practices

- **Always search first** to avoid duplicates
- **Read before updating** to see current state
- Make targeted updates vs replacing everything
- Preserve existing formatting
- Use consistent naming conventions
- Place in appropriate parent/database
- Link related pages together