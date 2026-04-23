"""MCP server extractor for `quantpilot-mcps`.

Each server under `servers/<name>/` exposes the same two HTTP endpoints
via Express (see `packages/core/src/transport/validateEndpoint.ts` +
`setupStreamableHttpTransport`):
  POST /mcp       — MCP over StreamableHTTP (session-based)
  GET  /validate  — API-key validator

We also enumerate each server's registered MCP tools (from its
`tools/toolConfigs.ts`-style file) so pentesters can see the tool-call
surface area. Tool rows use method `MCP` and path = tool name.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))
from models import Auth, EndpointRow  # noqa: E402

REPOSITORY = "mcps"


def extract(repo_root: Path) -> tuple[list[EndpointRow], list[str]]:
    warnings: list[str] = []
    servers_dir = repo_root / "servers"
    if not servers_dir.exists():
        return [], [f"servers/ not found under {repo_root}"]

    rows: list[EndpointRow] = []
    for server in sorted(p for p in servers_dir.iterdir() if p.is_dir()):
        # Two fixed HTTP endpoints per server. Embed server name in the path
        # so rows stay unique across servers (each server runs on its own host).
        rows.append(
            EndpointRow(
                repository=REPOSITORY,
                method="POST",
                path=f"/{server.name}/mcp",
                auth=Auth.API_KEY,
                source_kind="MCP HTTP",
            )
        )
        rows.append(
            EndpointRow(
                repository=REPOSITORY,
                method="GET",
                path=f"/{server.name}/validate",
                auth=Auth.API_KEY,
                source_kind="MCP HTTP",
            )
        )
        for tool_name, _tool_file, _tool_line in _find_tools(server):
            rows.append(
                EndpointRow(
                    repository=REPOSITORY,
                    method="MCP",
                    path=tool_name,
                    auth=Auth.API_KEY,
                    source_kind="MCP tool",
                )
            )
    return rows, warnings


def _find_tools(server_dir: Path):
    """Yield (tool_name, source_file, line) for every registered MCP tool.

    Tool definitions live in files under `src/tools/` (sometimes split per domain,
    e.g. `cryptocurrencyTools.ts` / `globalTools.ts`). We match `name: '<slug>'`
    patterns and rely on the convention that tool slugs contain a hyphen
    (`<server>-<action>`) to filter out generic `name:` occurrences in JSON
    schemas or Zod configs.
    """
    tools_dir = server_dir / "src" / "tools"
    if not tools_dir.exists():
        # Some servers may keep tools at the top of src/ — fall back to full rglob.
        candidates = list(server_dir.rglob("*tool*.ts"))
    else:
        candidates = [
            p for p in tools_dir.rglob("*.ts")
            if p.suffix == ".ts" and not p.name.endswith(".spec.ts") and not p.name.endswith(".test.ts")
        ]

    global_seen: set[str] = set()
    for file in candidates:
        try:
            text = file.read_text()
        except OSError:
            continue
        for m in re.finditer(
            r"""\bname\s*:\s*(['"`])([A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)+)\1""",
            text,
        ):
            name = m.group(2)
            if name in global_seen:
                continue
            global_seen.add(name)
            line = text[: m.start()].count("\n") + 1
            yield name, file, line
