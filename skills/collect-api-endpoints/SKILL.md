---
name: collect-api-endpoints
description: Collect a comprehensive list of QuantPilot API endpoints (HTTP + WebSocket) across all QP repos for pentest scoping. Walks FastAPI / NestJS / Next.js / MCP / Go-oapi-codegen / OpenAPI / AsyncAPI sources with a deterministic Python extractor (no LLM guessing), produces api_endpoints.json for review, then — only on explicit user go-ahead — publishes to the security Notion database. Use when the user asks to collect/list/inventory QP endpoints, refresh the pentest scope list, or sync endpoints to the security Notion DB.
---

# collect-api-endpoints

## Purpose

Produce a reviewable inventory of every HTTP + WebSocket endpoint that QuantPilot exposes, with each endpoint tagged by a single flat **auth** enum: `public`, `jwt`, `okta`, `api-key`, `signature`, or `unspecified`. This mixes scope and mechanism in the way pentesters think about credentials (what to attempt against each endpoint). Output is published to a Notion database so the list stays maintained and diffable.

| Auth value | Meaning | Example triggers |
|------------|---------|-------------------|
| `public`    | no auth gate | `allow_unauthenticated_paths`, no `@UseGuards`, no middleware |
| `jwt`       | user JWT bearer | FastAPI `get_current_user`, NestJS `AuthGuard('jwt')` |
| `okta`      | Okta SSO (admin/staff) | FastAPI `require_admin`, NestJS `OktaAuthGuard` |
| `api-key`   | service/integration API key header | `X-Service-API-Key`, `AgenticApiKeyGuard`, MCP `x-api-key` |
| `signature` | webhook HMAC signature check | `verify_internal_secret`, Stripe/Anthropic webhooks |
| `unspecified` | could not determine | OpenAPI/AsyncAPI rows with no implementer in scope |

- **Extraction is deterministic** — a Python script walks source code, spec YAML, and generated OpenAPI files. It does not ask an LLM to enumerate routes.
- **Two phases, strictly separate.** Phase 1 writes local files for user review. Phase 2 publishes to Notion, and only runs when the user explicitly asks for it.

**Target Notion database:** `https://www.notion.so/3496b755601180739c4ce3c24b0708e4` (DB id `3496b755601180739c4ce3c24b0708e4`).

## Required inputs

This skill reads repos from **Claude Code's current working-directory list** (what `/add-dir` has attached to the session). Do not ask the user for paths or workspace roots — list what's attached and map each directory to a role.

| Role | Expected repo | Contributes | Required? |
|------|---------------|-------------|-----------|
| agentic-backend | `3commas-io/quantpilot-agentic-backend` | FastAPI HTTP + WS routes | recommended |
| frontend | `3commas-io/quantpilot-frontend` | NestJS (`apps/api`) + Next.js (`apps/landing`) | recommended |
| mcps | `3commas-io/quantpilot-mcps` | MCP server HTTP + tools | recommended |
| mdm | `3commas-io/mdm` | Implements eck spec — middleware → auth level | recommended (else eck rows land as Unspecified) |
| sbm | `3commas-io/sbm` | Implements sbm + sbm-ws specs | recommended |
| ecm | `3commas-io/ecm` | Implements ecm spec + inline `/health` | recommended |
| eck | `3commas-io/eck` | Dev client `GET /` + WS `/ws` only | optional |
| common | `3commas-io/common` | OpenAPI + AsyncAPI specs (eck, ecm, sbm, sbm-backtests-ws) | **required** |

**Out of scope (explicit):** legacy `3commas` Rails, `app-3commas-frontend`, `3commas-frontend`, `3commas-ui`, `nextjs-docker`. These are the main 3commas.io product, not QuantPilot. Do not scan them unless the user explicitly expands scope.

## Behavior — run this sequence

### Phase 1 — extract & verify (default; never publishes)

1. **Enumerate working directories attached to the session.** The session system prompt lists a primary working directory plus "Additional working directories"; `/add-dir` updates the list. Gather all of them.

2. **Map each directory to a role.** First try the directory basename against the expected-repo names. If a basename doesn't match (e.g. the user cloned into a different name), run a quick fingerprint check with `Read` / `Bash`:
   - `common`: has `openapi/*.yaml` **and** `asyncapi/*.yaml` under the repo root.
   - `agentic-backend`: `src/application/__init__.py` exists.
   - `frontend`: `apps/api/src/` and `apps/landing/app/` both exist.
   - `mcps`: `servers/<name>/` and `packages/core/` both exist.
   - `mdm`: Go repo whose `cmd/server/main.go` imports `github.com/3commas-io/common/api/eck/v1` (alias `eckapi`).
   - `sbm`: Go repo whose `cmd/server/main.go` calls `v1.HandlerFromMuxWithBaseURL(..., "/sbm/v1")`.
   - `ecm`: Go repo whose `cmd/server/main.go` mounts `api.HandlerFromMuxWithBaseURL(..., "/ecm/v1")`.
   - `eck`: Go repo with `apps/marketdata` + `apps/kora` + `cmd/client/web.go`.

3. **Print a coverage table and stop for any missing recommended/required role.** Example:
   ```
   role               status           path
   -----------------  ---------------  --------------------------------------
   common             OK               /Users/you/3com/common
   agentic-backend    OK               /Users/you/3com/quantpilot-agentic-backend
   frontend           OK               /Users/you/3com/quantpilot-frontend
   mcps               OK               /Users/you/3com/quantpilot-mcps
   mdm                OK               /Users/you/3com/mdm
   sbm                MISSING          —
   ecm                OK               /Users/you/3com/ecm
   eck                MISSING (opt.)   —
   ```
   For each missing recommended/required role, tell the user exactly what to do (do not try to clone yourself):
   ```
   Cannot scan: 'sbm' is not attached.
   Either:
     - /add-dir /path/to/your/sbm checkout, OR
     - if you don't have it cloned, run
         gh repo clone 3commas-io/sbm ~/3com/sbm
       then /add-dir ~/3com/sbm
   Re-invoke the skill when done.
   ```
   Missing `common` is a hard stop. Missing `eck` is a warning only — proceed with a note in the report.

4. **Invoke the extractor.** The script lives at `${CLAUDE_PLUGIN_ROOT}/skills/collect-api-endpoints/scripts/collect_endpoints.py`. Pass one `--role key=<absolute-path>` for every role that resolved; omit skipped roles entirely. Write outputs next to the current working directory so the user can inspect them:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/collect-api-endpoints/scripts/collect_endpoints.py" \
     --role common=<abs> \
     --role agentic-backend=<abs> \
     --role frontend=<abs> \
     --role mcps=<abs> \
     --role mdm=<abs> \
     --role sbm=<abs> \
     --role ecm=<abs> \
     [--role eck=<abs>] \
     --out-json ./api_endpoints.json
   ```
   `${CLAUDE_PLUGIN_ROOT}` is set automatically when a plugin skill runs; if it isn't present (dev invocation), fall back to resolving the script via the skill's own directory.

5. **Relay the summary to the user.** The script prints a summary to stdout (totals per repo, per auth, parse warnings, skipped sources). Show that summary and the path to `./api_endpoints.json` so the user can open it in their editor. **Stop here.** Do not invoke any Notion tool in Phase 1.

### Phase 2 — publish to Notion (only on explicit user go-ahead)

Only run when the user asks to publish (e.g. "publish to Notion", "sync the list to Notion").

1. **Dry-run first.** Print what will be created/updated without hitting Notion:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/collect-api-endpoints/scripts/collect_endpoints.py" \
     --publish ./api_endpoints.json \
     --dry-run
   ```
   The script reads the JSON from Phase 1 and prints the intended payloads (one per row). Do not write the payloads to Notion yet.

2. **Publish.** When the user confirms after seeing the dry-run, run without `--dry-run`. Claude is responsible for calling the Notion MCP tools; the script produces the payloads and Claude submits them via `mcp__claude_ai_Notion__*` against database id `3496b755601180739c4ce3c24b0708e4`. Match rows on `(Repository, Method, Path)` and update in place; create new rows otherwise. Never mutate the DB schema silently — if a column is missing, tell the user and stop.

## Safety rules

- Do not clone repos. If a repo is missing, print the `gh repo clone ...` / `/add-dir ...` hint and stop.
- Do not publish to Notion in Phase 1, ever.
- Do not mutate the Notion schema. If columns are missing, surface the list and ask the user.
- Do not touch any repo listed under "Out of scope" unless the user explicitly expands scope.
- The script is the source of truth for extraction. Do not second-guess its output by reading routes yourself — if the user suspects an extractor bug, reproduce it with the script and fix the script.
