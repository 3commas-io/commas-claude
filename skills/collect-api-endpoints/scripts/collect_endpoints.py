#!/usr/bin/env python3
"""collect-api-endpoints — deterministic QP endpoint extractor.

Phase 1 (extract): reads repos passed via --role key=<abs-path>, dispatches to
per-source extractors, writes api_endpoints.json.

Phase 2 (publish): ``--publish <json> --out-dir <dir>`` writes one file per
batch to ``<dir>/batch_NN.json`` and prints the batch filenames (one per
line) to stdout. Each batch file is a pure JSON array of
``{"properties": {...}}`` items — ready to be pasted as the ``pages``
argument of the Notion MCP tool ``notion-create-pages``. Also writes
``<dir>/_plan.json`` with the database id, data source id, totals, and
upsert keys for lookup-before-update workflows.

The script never clones repos and never calls Notion itself — publishing
happens from Claude's MCP toolchain, one batch per ``notion-create-pages``
call.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import importlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from models import Auth, EndpointRow  # noqa: E402

NOTION_DB_ID = "3496b755601180739c4ce3c24b0708e4"
NOTION_DB_URL = f"https://www.notion.so/{NOTION_DB_ID}"
# Data source id for the single collection under NOTION_DB_ID; discoverable via
# `notion-fetch NOTION_DB_URL` and stable for this DB.
NOTION_DATA_SOURCE_ID = "3496b755-6011-806e-b7cd-000b5250c121"
# `notion-create-pages` accepts up to 100 pages per call. We pick a smaller
# chunk so each tool-call payload stays under ~30KB — that's comfortably
# within every MCP transport's tool-argument size budget.
NOTION_CREATE_PAGES_LIMIT = 50

ROLES_REQUIRED = {"common"}
ROLES_RECOMMENDED = {
    "agentic-backend",
    "frontend",
    "mcps",
    "mdm",
    "sbm",
    "ecm",
}
ROLES_OPTIONAL = {"eck"}
ROLES_ALL = ROLES_REQUIRED | ROLES_RECOMMENDED | ROLES_OPTIONAL


# ---------------------------------------------------------------------------
# Arg parsing
# ---------------------------------------------------------------------------
def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--role",
        action="append",
        default=[],
        metavar="KEY=PATH",
        help=(
            "Absolute path to a repo for the given role. "
            f"Valid keys: {', '.join(sorted(ROLES_ALL))}. "
            "Pass this flag once per role; omit any role you want to skip. "
            "'common' is required."
        ),
    )
    p.add_argument("--out-json", default="./api_endpoints.json", help="Where to write the JSON output (Phase 1).")
    p.add_argument(
        "--publish",
        metavar="JSON",
        default=None,
        help="Phase 2: read rows from the given JSON file and print Notion MCP payloads for Claude to submit.",
    )
    p.add_argument(
        "--out-dir",
        default="./api_endpoints_batches",
        help=(
            "Phase 2 only: directory to write batch files into. Each batch is "
            "a JSON array of pages ready for mcp__notion__notion-create-pages. "
            "Also writes _plan.json with totals + upsert keys."
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Phase 2 only: print the plan summary without writing batch files.",
    )
    return p.parse_args(argv)


def parse_roles(role_args: list[str]) -> dict[str, Path]:
    roles: dict[str, Path] = {}
    for raw in role_args:
        if "=" not in raw:
            sys.exit(f"ERROR: --role expects KEY=PATH, got {raw!r}")
        key, _, path = raw.partition("=")
        key = key.strip()
        path_obj = Path(path.strip()).expanduser()
        if key not in ROLES_ALL:
            sys.exit(f"ERROR: unknown role {key!r} (valid: {sorted(ROLES_ALL)})")
        if not path_obj.is_absolute():
            sys.exit(f"ERROR: role '{key}' path must be absolute, got {path_obj}")
        if not path_obj.exists():
            sys.exit(
                f"ERROR: role '{key}' path does not exist: {path_obj}\n"
                f"  Either /add-dir the correct checkout, or clone it first with\n"
                f"    gh repo clone 3commas-io/{_expected_repo(key)} {path_obj}\n"
                f"  then re-invoke the skill."
            )
        if key in roles:
            sys.exit(f"ERROR: role '{key}' specified twice")
        roles[key] = path_obj.resolve()
    missing_required = ROLES_REQUIRED - roles.keys()
    if missing_required:
        sys.exit(f"ERROR: missing required role(s): {sorted(missing_required)}")
    return roles


def _expected_repo(role: str) -> str:
    return {
        "agentic-backend": "quantpilot-agentic-backend",
        "frontend": "quantpilot-frontend",
        "mcps": "quantpilot-mcps",
        "mdm": "mdm",
        "sbm": "sbm",
        "ecm": "ecm",
        "eck": "eck",
        "common": "common",
    }[role]


# ---------------------------------------------------------------------------
# Extractor dispatch
# ---------------------------------------------------------------------------
ExtractorFn = Callable[[Path], tuple[list[EndpointRow], list[str]]]


def _load(module_name: str) -> Any:
    return importlib.import_module(f"extractors.{module_name}")


def _extract_fastapi(p: Path):
    return _load("fastapi_extractor").extract(p)


def _extract_frontend(p: Path):
    api_rows, api_warns = _load("nestjs_extractor").extract(p)
    landing_rows, landing_warns = _load("nextjs_extractor").extract(p)
    return api_rows + landing_rows, api_warns + landing_warns


def _extract_mcps(p: Path):
    return _load("mcp_extractor").extract(p)


def _extract_common(p: Path):
    oa_rows, oa_warns = _load("openapi_extractor").extract(p)
    aa_rows, aa_warns = _load("asyncapi_extractor").extract(p)
    return oa_rows + aa_rows, oa_warns + aa_warns


def _extract_go_impl(p: Path):
    return _load("go_oapi_extractor").extract(p)


EXTRACTORS: dict[str, ExtractorFn] = {
    "agentic-backend": _extract_fastapi,
    "frontend": _extract_frontend,
    "mcps": _extract_mcps,
    "common": _extract_common,
    "mdm": _extract_go_impl,
    "sbm": _extract_go_impl,
    "ecm": _extract_go_impl,
    "eck": _extract_go_impl,
}


# ---------------------------------------------------------------------------
# Phase 1 — extract and write outputs
# ---------------------------------------------------------------------------
def run_extract(roles: dict[str, Path], out_json: Path) -> None:
    rows: list[EndpointRow] = []
    warnings: list[str] = []
    skipped = sorted(ROLES_ALL - roles.keys())

    for role in sorted(roles):
        path = roles[role]
        extractor = EXTRACTORS[role]
        try:
            role_rows, role_warns = extractor(path)
        except Exception as exc:  # surface loudly, don't swallow
            warnings.append(f"[{role}] extractor crashed: {exc!r}")
            continue
        rows.extend(role_rows)
        warnings.extend(f"[{role}] {w}" for w in role_warns)

    # Cross-link implementations: spec rows get Implementation filled in from
    # the Go oapi-codegen extractor's side-channel annotations.
    _apply_implementation_links(rows, roles)

    # Sort for stable diffs.
    rows.sort(key=lambda r: (r.repository, r.path, r.method))

    payload = {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "notion_db": NOTION_DB_URL,
        "skipped_roles": skipped,
        "warnings": warnings,
        "rows": [r.to_dict() for r in rows],
    }
    out_json.write_text(json.dumps(payload, indent=2))
    _print_summary(payload)


def _apply_implementation_links(rows: list[EndpointRow], roles: dict[str, Path]) -> None:
    # Each Go oapi extractor emits a synthetic row with repository == '__impl__'
    # and source_kind encoding the spec name it implements. Consume those rows
    # and promote spec rows' auth from Auth.UNSPECIFIED to the real value
    # the implementer's middleware scan determined.
    impl_auth: dict[str, str] = {}  # spec-repo → resolved auth
    keep: list[EndpointRow] = []
    for row in rows:
        if row.repository == "__impl__":
            impl_auth[row.source_kind] = row.auth
        else:
            keep.append(row)
    rows.clear()
    rows.extend(keep)
    for row in rows:
        resolved = impl_auth.get(row.repository)
        if resolved and row.auth == Auth.UNSPECIFIED:
            row.auth = resolved


def _print_summary(payload: dict[str, Any]) -> None:
    rows = payload["rows"]
    print(f"Wrote {len(rows)} endpoint row(s)")
    by_repo = Counter(r["repository"] for r in rows)
    by_auth = Counter(r["auth"] for r in rows)
    print("\nPer repository:")
    for repo, n in sorted(by_repo.items()):
        print(f"  {repo:24s}  {n}")
    print("\nPer auth:")
    for lvl, n in sorted(by_auth.items()):
        print(f"  {lvl:24s}  {n}")
    if payload["skipped_roles"]:
        print(f"\nSkipped roles: {', '.join(payload['skipped_roles'])}")
    if payload["warnings"]:
        print(f"\nWarnings ({len(payload['warnings'])}):")
        for w in payload["warnings"][:20]:
            print(f"  - {w}")
        if len(payload["warnings"]) > 20:
            print(f"  ... {len(payload['warnings']) - 20} more")


# ---------------------------------------------------------------------------
# Phase 2 — publish payloads
# ---------------------------------------------------------------------------
# Repository → Notion `Service` select value. Covers both code repos and specs.
SERVICE_MAP = {
    "agentic-backend": "Agentic backend",
    "frontend-api": "Frontend monorepo",
    "frontend-landing": "Frontend monorepo",
    "mcps": "MCPs",
    "eck": "eck",
    "ecm": "ecm",
    "sbm": "sbm",
    "sbm-backtests-ws": "sbm-backtests-ws",
}

# Flat `auth` enum → Notion `Authorization level` (the ticket's 4-bucket taxonomy).
# The finer enum still lives on the separate `Auth mechanism` property.
AUTH_LEVEL_MAP = {
    Auth.PUBLIC: "public",
    Auth.JWT: "user-specific",
    Auth.OKTA: "admin-only",
    Auth.API_KEY: "private/integration-specific",
    Auth.SIGNATURE: "private/integration-specific",
    Auth.UNSPECIFIED: None,  # leave blank
}

def run_publish(json_path: Path, out_dir: Path, dry_run: bool) -> None:
    """Write one file per batch so the caller's loop is trivial.

    Layout produced under ``out_dir/``:
      _plan.json          — database id, data source id, totals, upsert keys,
                            a ``pages_with_keys`` list
                            for lookup-before-update workflows.
      batch_00.json       — JSON array of ``{"properties": {...}}`` items.
      batch_01.json         Ready to pass directly to the Notion MCP tool
      ...                   ``notion-create-pages`` as the ``pages`` argument.

    The caller (Claude, from the skill) iterates batch_NN.json files and
    calls ``mcp__notion__notion-create-pages`` once per file. For updates it
    uses ``_plan.json['pages_with_keys'][i]['upsert_key']`` to query
    ``notion-query-data-sources`` and then ``notion-update-page`` with the
    matching ``properties`` block.
    """
    payload = json.loads(json_path.read_text())
    rows = payload["rows"]
    scanned_at = payload.get("generated_at", "")[:10]

    pages_with_keys = [
        _row_to_notion_props(r, scanned_at=scanned_at) for r in rows
    ]
    batches = [
        [{"properties": p["properties"]} for p in pages_with_keys[i : i + NOTION_CREATE_PAGES_LIMIT]]
        for i in range(0, len(pages_with_keys), NOTION_CREATE_PAGES_LIMIT)
    ]

    out_dir.mkdir(parents=True, exist_ok=True)
    batch_files: list[str] = []
    if not dry_run:
        for i, batch in enumerate(batches):
            fp = out_dir / f"batch_{i:02d}.json"
            fp.write_text(json.dumps(batch, indent=2))
            batch_files.append(str(fp))

    plan = {
        "database_id": NOTION_DB_ID,
        "data_source_id": NOTION_DATA_SOURCE_ID,
        "upsert_keys": ["Service", "Method", "Path"],
        "dry_run": dry_run,
        "total_pages": len(pages_with_keys),
        "batch_size": NOTION_CREATE_PAGES_LIMIT,
        "batch_files": batch_files,
        "next_steps": (
            [
                "For each batch_NN.json:",
                f"  call mcp__notion__notion-create-pages with parent={{'type':'data_source_id','data_source_id':'{NOTION_DATA_SOURCE_ID}'}} and pages=<contents of batch_NN.json>.",
                "For updates: look up rows by upsert_key (Service, Method, Path) via notion-query-data-sources, then pass the matching pages_with_keys[i].properties to notion-update-page.",
                "Do NOT mutate the database schema — if a property doesn't exist, stop and tell the user.",
            ]
            if not dry_run
            else ["DRY RUN — no batch files were written."]
        ),
        "pages_with_keys": pages_with_keys,
    }
    plan_path = out_dir / "_plan.json"
    if not dry_run:
        plan_path.write_text(json.dumps(plan, indent=2))

    # Stdout: print each batch file path on its own line, preceded by a summary.
    # Keeps the CLI friendly for shells / humans without a JSON parser.
    print(f"Publish plan → {out_dir}")
    print(f"Total pages: {plan['total_pages']}  Batch size: {plan['batch_size']}  Batches: {len(batches)}")
    if dry_run:
        print("DRY RUN — no files written.")
    else:
        print(f"Plan file:  {plan_path}")
        for f in batch_files:
            print(f"Batch file: {f}")


def _row_to_notion_props(row: dict[str, Any], scanned_at: str) -> dict[str, Any]:
    name = f"{row['method']} {row['path']}"
    service = SERVICE_MAP.get(row["repository"], row["repository"])
    auth_mechanism = row.get("auth") or Auth.UNSPECIFIED
    auth_level = AUTH_LEVEL_MAP.get(auth_mechanism)

    props: dict[str, Any] = {
        "Name": name,
        "Method": row["method"] or None,
        "Path": row["path"] or "",
        "Service": service or None,
        "Auth mechanism": auth_mechanism,
        "Source kind": row["source_kind"] or None,
    }
    if auth_level is not None:
        props["Authorization level"] = auth_level
    if scanned_at:
        props["date:Last scanned:start"] = scanned_at
        props["date:Last scanned:is_datetime"] = 0

    return {
        "upsert_key": {
            "Service": service,
            "Method": row["method"] or None,
            "Path": row["path"] or "",
        },
        "properties": props,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main(argv: list[str]) -> None:
    args = parse_args(argv)
    if args.publish:
        run_publish(
            Path(args.publish).expanduser().resolve(),
            out_dir=Path(args.out_dir).expanduser().resolve(),
            dry_run=args.dry_run,
        )
        return
    roles = parse_roles(args.role)
    run_extract(
        roles=roles,
        out_json=Path(args.out_json).expanduser().resolve(),
    )


if __name__ == "__main__":
    main(sys.argv[1:])
