---
name: write-tech-design
description: Write comprehensive technical design documents for features, architecture changes, and system designs. Follows industry-standard RFC/design doc patterns aligned with 3Commas Notion tech design conventions. Can be extended with project-specific context.
---

# Write Technical Design Document

Generate comprehensive technical design documents following industry-standard RFC/design doc patterns, aligned with 3Commas Notion documentation conventions.

**CRITICAL INSTRUCTION**: Before generating any design document, you MUST:
1. Check if a template file exists at `docs/tech-design-TEMPLATE.md` in the project
2. Follow the EXACT structure from the template (or use default structure below)
3. Use Mermaid diagrams for architecture and sequence visualization
4. Save the completed document to `docs/tech-design-{feature-name}.md`

## When to Use

- **New features** — Major feature additions
- **Architecture changes** — System redesigns or refactors
- **Technical decisions** — Library choices, patterns, approaches
- **Complex implementations** — Multi-component integrations
- **API changes** — Backend/Frontend contract changes
- **Performance optimizations** — System-wide improvements

## How to Use

Describe what you want to design:

```
Write a tech design for implementing real-time notifications using WebSockets
```

```
Create a design doc for migrating the authentication system to OAuth2
```

## Document Structure

Every design document MUST start with a **metadata header** and then include sections adapted to the feature. Use the base sections below as a guide — add, remove, or renumber sections as the feature demands. Not every feature needs every section.

### Metadata Header (required)

Always start the document with:

```markdown
**Status:** Draft
**Author:** <author name>
**Date:** <YYYY-MM-DD>
**Jira:** <TICKET-ID>
```

### Base Sections

#### 1. Introduction
- **1.1 Purpose** — Document purpose and problem being solved
- **1.2 Scope** — What's in and out of scope
- **1.3 Definitions and Acronyms** — Technical terms used in the document (use a table)

#### 2. System Architecture
- **2.1 High-Level Architecture** — Overall system architecture and main components
  - Include Mermaid `graph` diagrams for architecture visualization
  - Include Mermaid `sequenceDiagram` for interaction flows
- **2.2 Components** — Table with columns: Layer, Component, Purpose
- **2.3 Technical Stack** — Languages, frameworks, databases, infrastructure (if introducing new tech)

#### 3. Detailed Design
- **3.1 Component Design** — Each component with purpose, internal structure, dependencies, APIs
  - Use collapsible `<details>` blocks for lengthy component descriptions
- **3.2 Database Design** — Schema (Prisma models, SQL), relationships, migrations
- **3.3 API Design** — Table with columns: Method, Path, Description
- **3.4 Authorization** — How endpoints are protected, token flows, guards

#### 4. Key Design Decisions
Number each decision and explain the reasoning:
```markdown
### 1. Decision title
Explanation of what was decided and why. Include alternatives considered.
```

#### 5. Environment Variables
Table with columns: Variable, App, Purpose

#### 6. File Structure
Show the directory tree of new/modified files:
```
apps/api/src/feature/
├── dto/
│   └── feature.dto.ts
├── feature.controller.ts
├── feature.module.ts
└── feature.service.ts
```

#### 7. Security Considerations
- Authentication and Authorization
- Data Protection
- Security Controls

#### 8. Performance Considerations
- Caching Strategy
- Scalability
- Load Handling

#### 9. Deployment and Operations
- **9.1 Deployment Strategy** — Environments, rollout plan
- **9.2 Monitoring and Logging** — Metrics, alerts, logging approach

#### 10. Flow References
Document key user flows as step-by-step scenarios:
```markdown
### Flow 1: Happy path
User does X → Frontend calls Y → API returns Z → Result
```

#### 11. Risks and Mitigations
Table with columns: Risk, Impact, Mitigation Strategy

#### 12. Open Questions
Checklist format:
```markdown
- [ ] Question 1
- [ ] Question 2
```

#### 13. Document History
Table with columns: Version, Date, Author, Changes

### Section Guidelines

- **Adapt sections to the feature** — A simple API endpoint doesn't need Performance or Deployment sections. A complex integration might need extra sections (e.g., "External Dependencies", "Migration Plan").
- **Tables over prose** — Use tables for structured data (components, endpoints, env vars, risks). Tables are easier to scan and maintain.
- **Mermaid diagrams** — Use `graph TD/TB/LR` for architecture, `sequenceDiagram` for interaction flows. Every doc should have at least one diagram.
- **Code blocks** — Use for schemas, file structures, config examples, API responses. Always specify the language.
- **Keep it practical** — Focus on what engineers need to implement the feature. Skip boilerplate sections that don't add value for the specific feature.

## File Naming Convention

Format: `tech-design-{kebab-case-feature-name}.md`

Examples:
- `docs/tech-design-share-chat.md`
- `docs/tech-design-auth0-authorization.md`
- `docs/tech-design-real-time-notifications.md`

## Design Doc Status Workflow

- **Draft** — Initial version, open for feedback
- **In Review** — Being reviewed by team
- **Approved** — Approved for implementation
- **Implemented** — Feature is live
- **Superseded** — Replaced by newer design

## Best Practices

1. **Start with why** — Clear problem definition before jumping to solution
2. **Concrete goals** — Measurable success criteria
3. **Visual aids** — Mermaid diagrams and code examples in every doc
4. **Trade-off analysis** — Honest evaluation of approaches in Key Design Decisions
5. **Risk mitigation** — Identify and address concerns upfront
6. **Flow references** — Document happy path and edge case flows
7. **Environment awareness** — Always list env vars and deployment requirements

## Tips for Best Results

1. **Be specific** — Provide context about what you're designing
2. **Mention constraints** — Budget, timeline, technical limitations
3. **List requirements** — Functional and non-functional requirements
4. **Reference code** — Point to existing files/patterns to follow
5. **Clarify scope** — Define what's in and out of scope