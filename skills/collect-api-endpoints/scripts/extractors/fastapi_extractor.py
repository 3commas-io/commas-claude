"""FastAPI extractor for the quantpilot-agentic-backend repository.

Walks src/api/http/**/*.py and src/api/websocket/*.py with `ast`, composes
router prefixes across include_router() chains starting from the FastAPI
application factory, and classifies each route's auth level from its
Depends() dependencies and the `allow_unauthenticated_paths` list in the
auth middleware config.

This extractor is intentionally conservative: when a route's composition
cannot be resolved it records a warning rather than emitting a guessed path.
"""
from __future__ import annotations

import ast
import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path

import sys
SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))
from models import Auth, EndpointRow  # noqa: E402

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}
REPOSITORY = "agentic-backend"


@dataclass
class _RouteDecl:
    method: str  # upper-case verb or "WS"
    local_path: str
    line: int
    deps: list[str] = field(default_factory=list)  # names of Depends() targets
    auth_headers: list[str] = field(default_factory=list)  # Header(...) aliases suggesting auth
    func_name: str = ""


@dataclass
class _RouterDecl:
    """A top-module-level router variable."""
    var_name: str
    prefix: str
    file: Path
    line: int


@dataclass
class _IncludeEdge:
    """`parent_router.include_router(child, prefix=extra)` edge."""
    parent_var: str  # local var in file
    child_expr: str  # dotted expression like `admin.router` or `users_router`
    extra_prefix: str
    file: Path


@dataclass
class _ModuleInfo:
    module: str  # dotted module, e.g. `src.api.http.admin`
    file: Path
    # `router` var name → prefix + decls
    routers: dict[str, tuple[str, list[_RouteDecl]]] = field(default_factory=dict)
    includes: list[_IncludeEdge] = field(default_factory=list)
    imports: dict[str, str] = field(default_factory=dict)
    type_aliases: dict[str, list[str]] = field(default_factory=dict)  # UserDep -> [get_current_user]
    # Local assignments of the form `var = module_alias` or `var = module_alias.router`
    aliases: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def extract(repo_root: Path) -> tuple[list[EndpointRow], list[str]]:
    warnings: list[str] = []
    src = repo_root / "src"
    if not src.exists():
        warnings.append(f"src/ not found under {repo_root}")
        return [], warnings

    app_file = src / "application" / "__init__.py"
    if not app_file.exists():
        warnings.append("src/application/__init__.py not found — cannot resolve mount tree")
        return [], warnings

    # 1) Gather all HTTP route modules.
    http_files = sorted((src / "api" / "http").rglob("*.py"))
    ws_files = sorted((src / "api" / "websocket").glob("*.py"))
    modules: dict[str, _ModuleInfo] = {}
    for f in http_files + ws_files + [app_file]:
        info = _parse_module(f, repo_root)
        if info is not None:
            modules[info.module] = info

    # 2) Resolve the allow_unauthenticated_paths patterns from app factory.
    allow_patterns = _extract_allow_patterns(app_file)

    # 3) Walk the mount tree starting from `app` in the app factory.
    rows: list[EndpointRow] = []
    _MountWalker(modules, allow_patterns, repo_root, warnings, rows).walk(app_file)
    return rows, warnings


# ---------------------------------------------------------------------------
# Per-file parsing
# ---------------------------------------------------------------------------
def _parse_module(file: Path, repo_root: Path) -> _ModuleInfo | None:
    try:
        tree = ast.parse(file.read_text())
    except (OSError, SyntaxError):
        return None
    module = _file_to_module(file, repo_root)
    info = _ModuleInfo(module=module, file=file)

    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            for name in node.names:
                alias = name.asname or name.name
                info.imports[alias] = f"{node.module}.{name.name}"
        elif isinstance(node, ast.Import):
            for name in node.names:
                info.imports[name.asname or name.name] = name.name
        elif isinstance(node, ast.Assign):
            _handle_assign(node, info)
        elif isinstance(node, ast.AnnAssign):
            _handle_ann_assign(node, info)
        elif isinstance(node, ast.Expr):
            # bare expressions — usually include_router calls at module level
            _maybe_include(node.value, info)
        elif isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            _maybe_route_decl(node, info)

    # Decorators + Depends are discovered by _maybe_route_decl as we walk.
    # For routes defined inside function bodies (like create_app), we handle those
    # via the MountWalker below, which parses that function separately.
    return info


def _handle_assign(node: ast.Assign, info: _ModuleInfo) -> None:
    # Look for: router = APIRouter(prefix="...", tags=[...])
    if (
        isinstance(node.value, ast.Call)
        and _callee_name(node.value.func).endswith("APIRouter")
    ):
        prefix = _kwarg_str(node.value, "prefix") or ""
        for target in node.targets:
            if isinstance(target, ast.Name):
                info.routers[target.id] = (prefix, [])
        return
    # Look for: AdminDep = Annotated[..., Depends(require_admin)]
    deps = _collect_depends_from_annotation(node.value)
    if deps:
        for target in node.targets:
            if isinstance(target, ast.Name):
                info.type_aliases[target.id] = deps
        return
    # Look for: X = AnotherModule.router (simple re-export alias)
    if isinstance(node.value, ast.Attribute):
        for target in node.targets:
            if isinstance(target, ast.Name):
                info.aliases[target.id] = _attr_expr(node.value)
    # Look for: X = SomeIdentifier (alias)
    elif isinstance(node.value, ast.Name):
        for target in node.targets:
            if isinstance(target, ast.Name):
                info.aliases[target.id] = node.value.id


def _handle_ann_assign(node: ast.AnnAssign, info: _ModuleInfo) -> None:
    # UserDep = Annotated[AuthIdentity, Depends(get_current_user)]
    # We only care about top-level assignments where value is a subscript of Annotated.
    if not isinstance(node.target, ast.Name) or node.value is None:
        return
    deps = _collect_depends_from_annotation(node.annotation) + _collect_depends_from_annotation(node.value)
    if deps:
        info.type_aliases[node.target.id] = deps


def _maybe_include(call: ast.AST, info: _ModuleInfo) -> None:
    if not isinstance(call, ast.Call):
        return
    if not isinstance(call.func, ast.Attribute):
        return
    if call.func.attr != "include_router":
        return
    if not isinstance(call.func.value, ast.Name):
        return
    parent_var = call.func.value.id
    if not call.args:
        return
    child_expr = _attr_expr(call.args[0])
    extra_prefix = _kwarg_str(call, "prefix") or ""
    info.includes.append(
        _IncludeEdge(
            parent_var=parent_var,
            child_expr=child_expr,
            extra_prefix=extra_prefix,
            file=info.file,
        )
    )


def _maybe_route_decl(node: ast.AsyncFunctionDef | ast.FunctionDef, info: _ModuleInfo) -> None:
    for dec in node.decorator_list:
        if not isinstance(dec, ast.Call):
            continue
        if not isinstance(dec.func, ast.Attribute):
            continue
        method = dec.func.attr.lower()
        if method not in HTTP_METHODS and method != "websocket":
            continue
        if not isinstance(dec.func.value, ast.Name):
            continue
        router_var = dec.func.value.id
        if router_var not in info.routers:
            continue
        if not dec.args:
            continue
        first = dec.args[0]
        if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
            continue
        decl = _RouteDecl(
            method="WS" if method == "websocket" else method.upper(),
            local_path=first.value,
            line=dec.lineno,
            func_name=node.name,
        )
        decl.deps = _collect_function_depends(node, info)
        decl.auth_headers = _collect_auth_headers(node)
        info.routers[router_var][1].append(decl)


# ---------------------------------------------------------------------------
# Mount walker — starts from `app` and composes paths.
# ---------------------------------------------------------------------------
class _MountWalker:
    def __init__(
        self,
        modules: dict[str, _ModuleInfo],
        allow_patterns: list[str],
        repo_root: Path,
        warnings: list[str],
        rows: list[EndpointRow],
    ) -> None:
        self.modules = modules
        self.allow_patterns = allow_patterns
        self.repo_root = repo_root
        self.warnings = warnings
        self.rows = rows

    def walk(self, app_file: Path) -> None:
        try:
            tree = ast.parse(app_file.read_text())
        except (OSError, SyntaxError) as exc:
            self.warnings.append(f"cannot parse {app_file}: {exc!r}")
            return
        app_module = self.modules[_file_to_module(app_file, self.repo_root)]

        # Inline-defined routers in create_app(): track local var name -> (prefix, child expressions)
        local_routers: dict[str, tuple[str, list[tuple[str, str]]]] = {}
        inline_imports: dict[str, str] = dict(app_module.imports)

        factory_found = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and node.name == "create_app":
                self._walk_factory(node, local_routers, inline_imports, app_module)
                factory_found = True
                break
        if not factory_found:
            self.warnings.append("create_app() not found in application/__init__.py")
            return
        # Also process `register_*_routes(app)` style helpers: any function anywhere
        # that accepts `app` and calls `app.include_router(...)`.
        self._apply_register_helpers()

    def _apply_register_helpers(self) -> None:
        for module, info in self.modules.items():
            try:
                tree = ast.parse(info.file.read_text())
            except (OSError, SyntaxError):
                continue
            for fn in ast.walk(tree):
                if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                params = [a.arg for a in fn.args.args]
                if not params or params[0] != "app":
                    continue
                for child in ast.walk(fn):
                    if (
                        isinstance(child, ast.Expr)
                        and isinstance(child.value, ast.Call)
                        and isinstance(child.value.func, ast.Attribute)
                        and child.value.func.attr == "include_router"
                        and isinstance(child.value.func.value, ast.Name)
                        and child.value.func.value.id == "app"
                        and child.value.args
                    ):
                        child_expr = _attr_expr(child.value.args[0])
                        extra_prefix = _kwarg_str(child.value, "prefix") or ""
                        base = child_expr.split(".", 1)[0]
                        # If child_expr names a module-level router of THIS module,
                        # walk that module directly rather than going through imports.
                        if base in info.routers:
                            self._walk_module_router(
                                target_module=module,
                                accumulated_prefix=extra_prefix,
                                visited=set(),
                            )
                        else:
                            self._emit_mount(
                                accumulated_prefix="",
                                child_expr=child_expr,
                                extra_prefix=extra_prefix,
                                local_routers={},
                                inline_imports=info.imports,
                                app_module=info,
                            )

    def _walk_factory(
        self,
        factory: ast.FunctionDef | ast.AsyncFunctionDef,
        local_routers: dict[str, tuple[str, list[tuple[str, str]]]],
        inline_imports: dict[str, str],
        app_module: _ModuleInfo,
    ) -> None:
        # Pick up `from ... import ...` inside function body (lazy imports).
        for node in factory.body:
            if isinstance(node, ast.ImportFrom) and node.module:
                for name in node.names:
                    inline_imports[name.asname or name.name] = f"{node.module}.{name.name}"

        # Pass 1: local APIRouter variables with their prefixes.
        for node in ast.walk(factory):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                if _callee_name(node.value.func).endswith("APIRouter"):
                    prefix = _kwarg_str(node.value, "prefix") or ""
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name):
                            local_routers[tgt.id] = (prefix, [])

        # Pass 2: local include_router calls (parent_var.include_router(child, prefix=extra)).
        for node in ast.walk(factory):
            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == "include_router"
                and isinstance(node.value.func.value, ast.Name)
            ):
                parent_var = node.value.func.value.id
                if not node.value.args:
                    continue
                child_expr = _attr_expr(node.value.args[0])
                extra_prefix = _kwarg_str(node.value, "prefix") or ""
                if parent_var == "app":
                    # Mount at root (empty prefix).
                    self._emit_mount("", child_expr, extra_prefix, local_routers, inline_imports, app_module)
                elif parent_var in local_routers:
                    local_routers[parent_var][1].append((child_expr, extra_prefix))

        # For each local router mounted on `app`, walk its children with the base prefix.
        # Already handled inline above (when parent_var == "app").

    def _emit_mount(
        self,
        accumulated_prefix: str,
        child_expr: str,
        extra_prefix: str,
        local_routers: dict[str, tuple[str, list[tuple[str, str]]]],
        inline_imports: dict[str, str],
        app_module: _ModuleInfo,
    ) -> None:
        # Resolve child_expr to either (a) a local router var or (b) a module's `router` attribute.
        base = child_expr.split(".", 1)[0]
        if base in local_routers:
            local_prefix, children = local_routers[base]
            full_prefix = accumulated_prefix + extra_prefix + local_prefix
            for child_child_expr, child_extra in children:
                self._emit_mount(full_prefix, child_child_expr, child_extra, local_routers, inline_imports, app_module)
            return

        # Resolve via imports.
        resolved = _resolve_import(child_expr, inline_imports)
        if resolved is None:
            self.warnings.append(f"cannot resolve include_router target: {child_expr}")
            return
        target_module = resolved
        self._walk_module_router(
            target_module=target_module,
            accumulated_prefix=accumulated_prefix + extra_prefix,
            visited=set(),
        )

    def _walk_module_router(
        self,
        target_module: str,
        accumulated_prefix: str,
        visited: set[str],
    ) -> None:
        if target_module in visited:
            return
        visited.add(target_module)

        # Try direct module match, or trim trailing `.router`.
        module = target_module
        if module not in self.modules and module.endswith(".router"):
            module = module[: -len(".router")]

        if module not in self.modules:
            # Maybe the symbol is an alias re-export (`from .routes import router`): try parent+routes.
            candidate = f"{module}.routes" if not module.endswith(".routes") else module
            if candidate in self.modules:
                module = candidate
            else:
                # Or maybe it was imported `from pkg import submodule` — module is exactly the package and we need its __init__.
                # Fall through with a warning.
                self.warnings.append(f"module not found for include_router target: {target_module}")
                return

        info = self.modules[module]
        if not info.routers:
            # Could be a re-export from __init__.py without its own router — search child `routes.py` module.
            routes_candidate = f"{module}.routes"
            if routes_candidate in self.modules and self.modules[routes_candidate].routers:
                info = self.modules[routes_candidate]
        if not info.routers:
            # Sometimes __init__.py just imports: `from .routes import router` with no APIRouter() of its own.
            for child in list(self.modules):
                if child.startswith(module + ".") and self.modules[child].routers:
                    info = self.modules[child]
                    break
        if not info.routers:
            self.warnings.append(f"no APIRouter found in {module}")
            return

        # Usually there's one router named "router"; handle multiple just in case.
        for var_name, (local_prefix, decls) in info.routers.items():
            full_prefix = accumulated_prefix + local_prefix
            # Emit decorated routes on this router.
            for decl in decls:
                full_path = _normalize_path(full_prefix + decl.local_path)
                auth, guard = self._classify_auth(full_path, decl, info)
                rel_file = info.file.relative_to(self.repo_root)
                source_kind = "FastAPI WS" if decl.method == "WS" else "FastAPI"
                self.rows.append(
                    EndpointRow(
                        repository=REPOSITORY,
                        method=decl.method,
                        path=full_path,
                        auth=auth,
                        source_kind=source_kind,
                    )
                )
            # Recurse into includes declared on THIS router.
            for inc in info.includes:
                if inc.parent_var != var_name:
                    continue
                child_module = _resolve_import(inc.child_expr, info.imports)
                if child_module is None:
                    self.warnings.append(
                        f"cannot resolve include_router target {inc.child_expr!r} in {module}"
                    )
                    continue
                self._walk_module_router(
                    target_module=child_module,
                    accumulated_prefix=full_prefix + inc.extra_prefix,
                    visited=visited,
                )

    def _classify_auth(self, full_path: str, decl: _RouteDecl, info: _ModuleInfo) -> tuple[str, str]:
        # Expand type aliases captured in the module (AdminDep → require_admin).
        expanded: list[str] = []
        for dep in decl.deps:
            if dep in info.type_aliases:
                expanded.extend(info.type_aliases[dep])
            else:
                expanded.append(dep)
        expanded_lower = {d.lower() for d in expanded}
        # 1) Okta-style admin gate beats everything else.
        if "require_admin" in expanded_lower:
            return Auth.OKTA, "require_admin"
        # 2) HMAC / signature verifiers (preferred over generic service getters).
        signature_names = [d for d in expanded if _looks_like_signature_verifier(d)]
        if signature_names:
            return Auth.SIGNATURE, signature_names[0]
        # 3) Handler-level header-based API-key check (webhooks, internal routes).
        if decl.auth_headers:
            return Auth.API_KEY, f"Header({decl.auth_headers[0]})"
        # 4) User identity dependency.
        if "get_current_user" in expanded_lower:
            return Auth.JWT, "get_current_user"
        # 5) Fall back to the middleware's allow-unauthenticated list.
        if _path_matches_any(full_path, self.allow_patterns):
            return Auth.PUBLIC, "allow_unauthenticated_paths"
        # 6) Default: MultiProviderAuthMiddleware requires auth by default → JWT.
        if expanded:
            return Auth.JWT, ", ".join(expanded[:3])
        return Auth.JWT, ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _file_to_module(file: Path, repo_root: Path) -> str:
    rel = file.relative_to(repo_root)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][:-3]  # strip .py
    return ".".join(parts)


def _callee_name(func: ast.AST) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        base = _callee_name(func.value)
        return f"{base}.{func.attr}" if base else func.attr
    return ""


def _attr_expr(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_attr_expr(node.value)}.{node.attr}"
    return ""


def _kwarg_str(call: ast.Call, name: str) -> str | None:
    for kw in call.keywords:
        if kw.arg == name and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
            return kw.value.value
    return None


def _resolve_import(expr: str, imports: dict[str, str]) -> str | None:
    if not expr:
        return None
    parts = expr.split(".")
    base = parts[0]
    remainder = parts[1:]
    if base not in imports:
        return None
    root = imports[base]
    if not remainder:
        return root
    # `admin` import points to `src.api.http.admin` package; admin.router → src.api.http.admin.router
    # but we want the module not the attribute. Keep building a dotted string; the caller trims.
    return root + "." + ".".join(remainder)


def _collect_function_depends(node: ast.AsyncFunctionDef | ast.FunctionDef, info: _ModuleInfo) -> list[str]:
    deps: list[str] = []
    for arg in list(node.args.args) + list(node.args.kwonlyargs):
        if arg.annotation is None:
            continue
        deps.extend(_collect_depends_from_annotation(arg.annotation))
        # Resolve type aliases used directly (e.g. `_admin: AdminDep`)
        ann = arg.annotation
        if isinstance(ann, ast.Name) and ann.id in info.type_aliases:
            deps.append(ann.id)  # record the alias; classify_auth expands it
    # Also check defaults for `= Depends(...)`
    for default in list(node.args.defaults) + list(node.args.kw_defaults):
        if default is None:
            continue
        deps.extend(_collect_depends_from_annotation(default))
    return deps


_AUTH_HEADER_ALIASES = ("api-key", "api_key", "apikey", "authorization", "token", "secret", "signature")


def _looks_like_signature_verifier(name: str) -> bool:
    """Name patterns that suggest HMAC / shared-secret validation logic."""
    low = name.lower()
    if low.startswith("verify_"):
        return True
    return any(
        kw in low
        for kw in ("_secret", "_signature", "_hmac", "_webhook")
    )


def _collect_auth_headers(fn: ast.AsyncFunctionDef | ast.FunctionDef) -> list[str]:
    aliases: list[str] = []
    for arg in list(fn.args.args) + list(fn.args.kwonlyargs):
        defaults_source = fn.args.defaults if arg in fn.args.args else fn.args.kw_defaults
        # Look at default value of this arg if it's a Header(...) call.
        positional_args = fn.args.args
        if arg in positional_args:
            idx_in_args = positional_args.index(arg)
            # defaults align to the last len(defaults) positional args
            offset = len(positional_args) - len(fn.args.defaults)
            default_idx = idx_in_args - offset
            default = fn.args.defaults[default_idx] if 0 <= default_idx < len(fn.args.defaults) else None
        else:
            kw_positionals = list(fn.args.kwonlyargs)
            default_idx = kw_positionals.index(arg) if arg in kw_positionals else -1
            default = fn.args.kw_defaults[default_idx] if 0 <= default_idx < len(fn.args.kw_defaults) else None
        _maybe_add_auth_header(default, aliases)
        _maybe_add_auth_header(arg.annotation, aliases)
    return aliases


def _maybe_add_auth_header(node: ast.AST | None, out: list[str]) -> None:
    if node is None:
        return
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and _callee_name(sub.func).endswith("Header"):
            # Look for alias kwarg (or positional).
            alias = None
            for kw in sub.keywords:
                if kw.arg == "alias" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    alias = kw.value.value
            if alias and any(kw in alias.lower() for kw in _AUTH_HEADER_ALIASES):
                out.append(alias)


def _collect_depends_from_annotation(node: ast.AST) -> list[str]:
    if node is None:
        return []
    deps: list[str] = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            name = _callee_name(sub.func)
            if name.endswith("Depends") and sub.args:
                target = _attr_expr(sub.args[0])
                if target:
                    deps.append(target)
    return deps


def _extract_allow_patterns(app_file: Path) -> list[str]:
    try:
        tree = ast.parse(app_file.read_text())
    except (OSError, SyntaxError):
        return []
    patterns: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _callee_name(node.func).endswith("add_middleware"):
            for kw in node.keywords:
                if kw.arg == "allow_unauthenticated_paths" and isinstance(kw.value, ast.List):
                    for el in kw.value.elts:
                        if isinstance(el, ast.Constant) and isinstance(el.value, str):
                            patterns.append(el.value)
    return patterns


def _path_matches_any(path: str, patterns: list[str]) -> bool:
    for pat in patterns:
        # Patterns like `/agentic/internal/arena/*` use glob-style wildcard.
        if fnmatch.fnmatchcase(path, pat):
            return True
        # Also accept exact match.
        if path == pat:
            return True
    return False


def _normalize_path(path: str) -> str:
    # Collapse duplicate slashes, drop trailing slash (except root).
    collapsed = re.sub(r"/+", "/", path)
    if len(collapsed) > 1 and collapsed.endswith("/"):
        collapsed = collapsed[:-1]
    if not collapsed.startswith("/"):
        collapsed = "/" + collapsed
    return collapsed
