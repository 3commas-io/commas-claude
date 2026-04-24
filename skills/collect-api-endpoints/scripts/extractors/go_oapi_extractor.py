"""Go extractor for oapi-codegen-based services (mdm / sbm / ecm) and the
eck ergo.services platform.

Responsibilities
----------------
1. For oapi-codegen services, detect which spec the repo implements by
   inspecting imports of ``github.com/3commas-io/common/api/<svc>/v<N>``.
   Emit a synthetic ``__impl__`` row that ``collect_endpoints.py`` uses to
   cross-link the spec rows with the implementer repo.
2. Scan the server's middleware stack to determine the real auth level
   (``Public`` when no auth middleware; ``Integration``/``User``/``Admin``
   when auth middleware is present).
3. Emit rows for inline-defined routes that exist outside the generated
   OpenAPI handler (e.g. ecm's ``GET /health``, sbm's ``GET /sbm/v1/ws``).
4. Handle eck's special case: ``cmd/client/web.go`` exposes ``GET /``
   (static) and a WebSocket ``/ws`` with a permissive ``CheckOrigin`` —
   both are surfaced.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))
from models import Auth, EndpointRow  # noqa: E402


_IMPL_IMPORT_RE = re.compile(
    r'"github\.com/3commas-io/common/api/(eck|ecm|sbm)/v\d+"'
)
_HANDLER_MOUNT_RE = re.compile(
    r"\b(?:HandlerWithOptions|HandlerFromMux|HandlerFromMuxWithBaseURL|RegisterHandlers|RegisterHandlersWithOptions)\s*\("
)
_HANDLER_BASE_URL_RE = re.compile(
    r"HandlerFromMuxWithBaseURL\s*\([^,]+,\s*[^,]+,\s*(['\"])([^'\"]*)\1"
)
_HANDLER_WITH_OPTIONS_BASE_RE = re.compile(
    r"BaseURL\s*:\s*(['\"])([^'\"]*)\1"
)
_CHI_USE_RE = re.compile(
    r"""\b(?:r|router|R)\.Use\s*\(\s*([^)]+)\s*\)"""
)
_INLINE_ROUTE_RE = re.compile(
    r"""\b(?:r|R|router|mux)\.(Get|Post|Put|Patch|Delete|Handle|HandleFunc)\s*\(\s*(['"`])([^'"`]+?)\2"""
)
_MUX_METHOD_PATH_RE = re.compile(
    r"""\bmux\.Handle(?:Func)?\s*\(\s*(['"`])(?:(GET|POST|PUT|PATCH|DELETE)\s+)?([^'"`]+?)\1"""
)
_WS_UPGRADER_RE = re.compile(
    r"\bwebsocket\.Upgrader\s*\{"
)
_CHECK_ORIGIN_PERMISSIVE_RE = re.compile(
    r"CheckOrigin\s*:\s*func\s*\([^)]*\)\s*bool\s*\{[^}]*return\s+true"
)
_WRAP_CALL_RE = re.compile(
    r"""\b([A-Za-z_][\w]*)\s*\(\s*([^)]*?)\s*\)"""
)


_AUTH_KEYWORDS = (
    "auth",
    "jwt",
    "bearer",
    "token",
    "apikey",
    "api_key",
    "api-key",
    "authorization",
    "authz",
    "okta",
    "privy",
    "session",
)


@dataclass
class _GoRepoAnalysis:
    repo_name: str  # logical role (mdm, sbm, ecm, eck)
    implemented_specs: set[str]  # {"eck"} or {"sbm"} etc
    base_url_per_spec: dict[str, str]  # spec -> mount prefix like "/ecm/v1"
    inline_routes: list[tuple[str, str, int, Path]]  # (method, full_path, line, file)
    middleware_auth: str  # one of Auth.*
    middleware_evidence: str


def extract(repo_root: Path) -> tuple[list[EndpointRow], list[str]]:
    warnings: list[str] = []
    # Identify role first by looking at dir layout + imports.
    analysis = _analyze_repo(repo_root, warnings)
    if analysis is None:
        warnings.append(f"Go extractor: could not analyze {repo_root}")
        return [], warnings

    rows: list[EndpointRow] = []
    # 1) One synthetic row per implemented spec, for the __impl__ cross-link.
    for spec in analysis.implemented_specs:
        rows.append(
            EndpointRow(
                repository="__impl__",
                method="",
                path="",
                auth=analysis.middleware_auth,
                source_kind=spec,  # used by collect_endpoints to look up by repository
            )
        )
        # ALSO emit a spec-linked row for sbm -> sbm-backtests-ws (since sbm repo
        # implements both the HTTP and WS specs).
        if spec == "sbm":
            rows.append(
                EndpointRow(
                    repository="__impl__",
                    method="",
                    path="",
                    auth=analysis.middleware_auth,
                    source_kind="sbm-backtests-ws",
                )
            )

    # 2) Emit the inline routes (routes NOT generated from the OpenAPI spec).
    for method, full_path, _line, _file in analysis.inline_routes:
        rows.append(
            EndpointRow(
                repository=analysis.repo_name,
                method=method,
                path=full_path,
                auth=analysis.middleware_auth,
                source_kind="Go net/http",
            )
        )

    return rows, warnings


def _analyze_repo(repo_root: Path, warnings: list[str]) -> _GoRepoAnalysis | None:
    repo_name = _guess_repo_name(repo_root)
    # Scan all cmd/*/main.go (there may be many for eck).
    server_mains = sorted((repo_root / "cmd").rglob("main.go")) if (repo_root / "cmd").exists() else []
    if not server_mains:
        return None

    implemented: set[str] = set()
    base_urls: dict[str, str] = {}
    inline_routes: list[tuple[str, str, int, Path]] = []
    middleware_auth = Auth.PUBLIC
    middleware_evidence_parts: list[str] = []

    for main_file in server_mains:
        try:
            text = main_file.read_text()
        except OSError:
            continue
        specs_in_file = set(_IMPL_IMPORT_RE.findall(text))
        implemented.update(specs_in_file)

        # Mount base URL (e.g. "/ecm/v1", "/sbm/v1").
        for m in _HANDLER_BASE_URL_RE.finditer(text):
            base = m.group(2)
            for spec in specs_in_file or implemented:
                base_urls[spec] = base
        # Options-style `BaseURL: "/..."`.
        for m in _HANDLER_WITH_OPTIONS_BASE_RE.finditer(text):
            base = m.group(2)
            for spec in specs_in_file or implemented:
                base_urls[spec] = base

        # Middleware auth detection (only meaningful on main.go, where the http.Server is wired).
        file_auth, file_evidence = _classify_middleware(text)
        middleware_auth = Auth.stronger(middleware_auth, file_auth)
        if file_evidence:
            # Prefix with the parent directory when there are multiple mains (e.g. eck has
            # cmd/marketdata/main.go, cmd/kora/main.go, …); for a single-main repo we emit
            # the bare evidence line.
            if len(server_mains) > 1:
                middleware_evidence_parts.append(f"{main_file.parent.name}: {file_evidence}")
            else:
                middleware_evidence_parts.append(file_evidence)

        # Inline routes defined in main.go — these bypass the generated OpenAPI handler.
        inline_routes.extend(_scan_inline_routes(text, main_file, implemented))

    # Also scan HTTP adapter files (not just main.go) for *inline routes only*.
    # We do NOT re-run middleware detection on handler files — middleware is wired
    # in main.go; handler files never have Router.Use / Handler: fields, so
    # running the classifier on them just yields a "no auth middleware" false
    # positive per file and turns the guard column into unstructured noise.
    for extra in _extra_http_files(repo_root, repo_name):
        try:
            text = extra.read_text()
        except OSError:
            continue
        inline_routes.extend(_scan_inline_routes(text, extra, implemented))

    # Deduplicate inline routes on (method, path).
    seen = set()
    deduped: list[tuple[str, str, int, Path]] = []
    for r in inline_routes:
        key = (r[0], r[1])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    # Collapse duplicate evidence lines — every main.go with no auth middleware
    # would otherwise emit the same sentence, bloating the guard column.
    unique_parts = list(dict.fromkeys(middleware_evidence_parts))
    evidence = " | ".join(unique_parts) if unique_parts else "no auth middleware detected"

    return _GoRepoAnalysis(
        repo_name=repo_name,
        implemented_specs=implemented,
        base_url_per_spec=base_urls,
        inline_routes=deduped,
        middleware_auth=middleware_auth,
        middleware_evidence=evidence,
    )


def _guess_repo_name(repo_root: Path) -> str:
    # Prefer go.mod module name (last segment) if present; fall back to dir name.
    go_mod = repo_root / "go.mod"
    if go_mod.exists():
        try:
            line = go_mod.read_text().splitlines()[0]
        except OSError:
            line = ""
        m = re.match(r"module\s+([\w\./\-]+)", line)
        if m:
            return m.group(1).rsplit("/", 1)[-1]
    return repo_root.name


def _classify_middleware(text: str) -> tuple[str, str]:
    """Return (auth_level, evidence) based on what middleware is wired up.

    Only inspects middleware that actually affects HTTP requests: (a) chi
    ``r.Use(...)`` calls, and (b) function names ending in ``Middleware``
    that appear inside the handler-wrap chain (not arbitrary references in
    the file). This avoids false positives from names like
    ``PostgresIAMAuth`` that are unrelated to HTTP auth.
    """
    hits: list[str] = []
    # Pattern A: chi router ``.Use(<middleware>)``.
    for m in _CHI_USE_RE.finditer(text):
        arg = m.group(1).strip().rstrip(",")
        if any(kw in arg.lower() for kw in _AUTH_KEYWORDS):
            hits.append(arg)

    # Pattern B: wrap chain inside a `Handler:` field assignment
    # (e.g. `Handler: sentryHandler.Handle(corsMiddleware(recoveryMiddleware(...)))`).
    wrap_expr = _extract_handler_wrap_expression(text)
    if wrap_expr:
        for m in re.finditer(r"\b([A-Za-z_][\w]*[Mm]iddleware)\s*\(", wrap_expr):
            name = m.group(1)
            if any(kw in name.lower() for kw in _AUTH_KEYWORDS):
                hits.append(name)

    if not hits:
        return Auth.PUBLIC, "no auth middleware (sentry/cors/recovery/logging only)"
    joined = ", ".join(dict.fromkeys(hits))
    low = joined.lower()
    if "okta" in low or "admin" in low:
        return Auth.OKTA, f"middleware: {joined}"
    if "apikey" in low or "api_key" in low or "api-key" in low or "serviceapikey" in low:
        return Auth.API_KEY, f"middleware: {joined}"
    return Auth.JWT, f"middleware: {joined}"


def _extract_handler_wrap_expression(text: str) -> str:
    """Return the RHS of the ``Handler:`` field, resolving through one level
    of intermediate variable assignment (``wrappedHandler := ...``).
    """
    m = re.search(r"\bHandler\s*:\s*([A-Za-z_][\w]*|[^,\n]+)", text)
    if not m:
        return ""
    rhs = m.group(1).strip()
    # If it's a bare identifier, look up its assignment.
    if re.fullmatch(r"[A-Za-z_][\w]*", rhs):
        assign = re.search(rf"\b{re.escape(rhs)}\s*:=\s*([^\n]+)", text)
        if assign:
            return assign.group(1)
    return rhs


def _scan_inline_routes(text: str, file: Path, specs: set[str]):
    """Find routes defined outside the generated oapi handler."""
    out: list[tuple[str, str, int, Path]] = []
    # Pattern 1: `mux.Handle(<pattern>, handler)` where pattern is `"GET /path"` or `"/path"`.
    for m in _MUX_METHOD_PATH_RE.finditer(text):
        verb = (m.group(2) or "GET").upper()
        path = m.group(3).strip()
        line = text[: m.start()].count("\n") + 1
        out.append((verb, path, line, file))
    # Pattern 2: `mux.HandleFunc("GET /path", ...)` already covered above by verb group.
    # Pattern 3: chi/router style `r.Get("/path", ...)`, `r.Post(...)`, ...
    for m in _INLINE_ROUTE_RE.finditer(text):
        verb_word = m.group(1)
        path = m.group(3).strip()
        if verb_word in ("Handle", "HandleFunc"):
            verb = "GET"
        else:
            verb = verb_word.upper()
        line = text[: m.start()].count("\n") + 1
        # Normalize leading slash
        if not path.startswith("/"):
            continue  # not a URL path
        out.append((verb, path, line, file))
    # Any path ending in /ws (or /*.ws) is a WebSocket upgrade route; flip its method.
    for i, (method, path, line, f) in enumerate(out):
        if path == "/ws" or path.endswith("/ws"):
            out[i] = ("WS", path, line, f)
    return out


def _extra_http_files(repo_root: Path, repo_name: str) -> list[Path]:
    """Return additional Go files to scan for inline routes beyond cmd/*/main.go."""
    extras: list[Path] = []
    # mdm uses internal/adapters/http/server.go + related handlers (but all routes come from OpenAPI)
    # sbm uses internal/handler/ws/handler.go for WS handling (also registered in main.go)
    # ecm has all routes in main.go already; extras may contain handler files.
    # eck: specifically cmd/client/web.go + embedded web UI.
    candidates = [
        repo_root / "internal" / "adapters" / "http",
        repo_root / "internal" / "handler",
        repo_root / "cmd" / "client",
    ]
    for c in candidates:
        if c.is_dir():
            for f in c.rglob("*.go"):
                if f.name.endswith("_test.go"):
                    continue
                extras.append(f)
    return extras
