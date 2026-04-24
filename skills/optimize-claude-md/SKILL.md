# Optimize CLAUDE.md Skill

Audit and enforce size budgets for all CLAUDE.md and `.claude/docs/` files.

## Purpose

Prevent documentation bloat by measuring line counts, checking budgets, detecting duplication, and verifying cross-references. Run this skill periodically or after significant doc changes.

## When to Use

- After editing CLAUDE.md or any `.claude/docs/` file
- Before committing documentation changes
- When prompted: "Check CLAUDE.md health" or "Audit docs"

## Audit Process

### 1. Measure Line Counts

Count lines for each file using `wc -l`:

```bash
wc -l CLAUDE.md
wc -l .claude/docs/*.md
wc -l apps/*/CLAUDE.md
wc -l .claude/skills/*/SKILL.md
```

### 2. Check Against Budgets

| File | Budget (lines) | Action if over |
|------|---------------|----------------|
| `CLAUDE.md` (root) | 500 | Extract content to `.claude/docs/` |
| `.claude/docs/*.md` (each) | 300 | Split into focused docs |
| `apps/*/CLAUDE.md` (each) | 250 | Extract to app-specific docs |
| `.claude/skills/*/SKILL.md` (each) | 200 | Trim examples, link to docs |

### 3. Detect Duplication

Check for content that appears in multiple files:

1. **Root vs docs:** Root CLAUDE.md should reference docs, not duplicate them
2. **Docs vs docs:** Each doc should have a single responsibility
3. **Skills vs docs:** Skills should reference docs, not copy conventions

**Common duplication patterns to check:**
- Type naming rules (should be only in CONVENTIONS.md)
- Module structure template (should be only in ARCHITECTURE.md)
- Tech stack versions (should be only in TECH_STACK.md)
- Key file descriptions (should be only in KEY_FILES.md)

### 4. Verify Cross-References

Every `.claude/docs/` file should be referenced in at least one of:
- Root `CLAUDE.md` documentation table
- A skill's `SKILL.md`
- Another docs file

Check that all docs listed in root CLAUDE.md documentation table actually exist.

### 5. Output Health Report

```markdown
## Documentation Health Report

### Line Counts
| File | Lines | Budget | Status |
|------|-------|--------|--------|
| CLAUDE.md | 360 | 500 | OK |
| CONVENTIONS.md | 195 | 300 | OK |
| ... | ... | ... | ... |

### Duplication Check
- [OK/WARN] No duplicate content detected between root and docs
- [OK/WARN] No duplicate content between docs files

### Cross-Reference Check
- [OK/WARN] All docs referenced in root CLAUDE.md
- [OK/WARN] All referenced docs exist on disk

### Recommendations
- (list any issues found)
```

## Budget Enforcement Rules

1. **Root CLAUDE.md must stay under 500 lines** — it loads every session
2. **Reference, don't repeat** — root should point to docs, not duplicate
3. **One responsibility per doc** — if a doc covers two topics, split it
4. **Skills link to docs** — skills should `Read` docs at runtime, not embed content