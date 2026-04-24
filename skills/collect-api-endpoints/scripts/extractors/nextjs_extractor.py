"""Next.js App Router extractor for `quantpilot-frontend/apps/landing`.

Walks `apps/landing/app/**/route.ts` (and `.tsx`, `.js`, `.mjs` variants).
Each such file exports one or more of `GET`, `POST`, `PUT`, `PATCH`, `DELETE`,
`HEAD`, `OPTIONS` — one export per HTTP verb. The URL path is derived from
the directory tree: `app/api/health/route.ts` → `/api/health`. Route groups
(`(marketing)` etc.) are stripped because they don't affect the URL.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))
from models import Auth, EndpointRow  # noqa: E402

REPOSITORY = "frontend-landing"
HTTP_VERBS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")

_EXPORT_RE = re.compile(
    r"export\s+(?:async\s+)?function\s+(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\b"
    r"|export\s+(?:const|let|var)\s+(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s*="
    r"|export\s+\{\s*([^}]+)\s*\}",
)


def extract(repo_root: Path) -> tuple[list[EndpointRow], list[str]]:
    warnings: list[str] = []
    landing = repo_root / "apps" / "landing"
    if not landing.exists():
        return [], warnings
    app_dir = landing / "app"
    if not app_dir.exists():
        return [], warnings

    rows: list[EndpointRow] = []
    for route_file in sorted(app_dir.rglob("route.*")):
        if route_file.suffix not in (".ts", ".tsx", ".js", ".mjs"):
            continue
        url_path = _path_from_route_file(route_file, app_dir)
        try:
            text = route_file.read_text()
        except OSError:
            continue
        verbs = _extracted_verbs(text)
        if not verbs:
            continue
        rel_file = route_file.relative_to(repo_root)
        auth, _guard, _notes = _classify(url_path, text)
        for verb in sorted(verbs):
            rows.append(
                EndpointRow(
                    repository=REPOSITORY,
                    method=verb,
                    path=url_path,
                    auth=auth,
                    source_kind="Next.js",
                )
            )
    return rows, warnings


def _path_from_route_file(route_file: Path, app_dir: Path) -> str:
    rel = route_file.relative_to(app_dir).parent.parts  # skip route.ts itself
    segments: list[str] = []
    for seg in rel:
        # Route groups like `(marketing)` don't affect the URL.
        if seg.startswith("(") and seg.endswith(")"):
            continue
        # Parallel routes `@foo` don't affect the URL path either.
        if seg.startswith("@"):
            continue
        # Dynamic segments: `[id]` → `{id}`, `[...rest]` → `{...rest}`.
        m = re.fullmatch(r"\[\.{3}(\w+)\]", seg)
        if m:
            segments.append("{..." + m.group(1) + "}")
            continue
        m = re.fullmatch(r"\[\[\.{3}(\w+)\]\]", seg)
        if m:
            segments.append("{..." + m.group(1) + "}")
            continue
        m = re.fullmatch(r"\[(\w+)\]", seg)
        if m:
            segments.append("{" + m.group(1) + "}")
            continue
        segments.append(seg)
    return "/" + "/".join(segments) if segments else "/"


def _extracted_verbs(text: str) -> set[str]:
    verbs: set[str] = set()
    for m in _EXPORT_RE.finditer(text):
        if m.group(1):
            verbs.add(m.group(1))
        elif m.group(2):
            verbs.add(m.group(2))
        elif m.group(3):
            for tok in m.group(3).split(","):
                tok = tok.split(" as ")[-1].strip()
                if tok in HTTP_VERBS:
                    verbs.add(tok)
    return verbs


def _classify(url_path: str, text: str) -> tuple[str, str, str]:
    # Very simple heuristics: the landing site is almost all public marketing / health.
    # If a route imports auth helpers or checks headers, surface that.
    lower = text.lower()
    if "hmac" in lower:
        return Auth.SIGNATURE, "HMAC check in handler", ""
    if "x-service-api-key" in lower or "service_api_key" in lower or "landingapikey" in lower:
        return Auth.API_KEY, "api-key header check in handler", ""
    if "requireauth" in lower or "getserversession" in lower or "verify_jwt" in lower:
        return Auth.JWT, "ad-hoc auth check in handler", ""
    return Auth.PUBLIC, "", ""
