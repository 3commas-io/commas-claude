"""OpenAPI 3.x spec extractor for `common/openapi/*.yaml`.

Enumerates `paths:` keys + operations. Auth level defaults to
``Unspecified`` because these specs declare no ``securitySchemes`` — the
cross-linking logic in ``collect_endpoints.py`` upgrades the classification
using the Go oapi-codegen implementer scan when available.

Each YAML file maps to a logical ``repository`` name derived from the
filename (e.g. ``eck-api.yaml`` → ``eck``, ``ecm-v1.yaml`` → ``ecm``,
``sbm-strategies-v1.yaml`` → ``sbm``) so rows group the way pentesters
think about the services.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))
from models import Auth, EndpointRow  # noqa: E402
from extractors import _yaml_scan  # noqa: E402

HTTP_VERBS = {"get", "post", "put", "patch", "delete", "head", "options"}


def extract(common_root: Path) -> tuple[list[EndpointRow], list[str]]:
    openapi_dir = common_root / "openapi"
    if not openapi_dir.exists():
        return [], [f"openapi/ not found under {common_root}"]

    rows: list[EndpointRow] = []
    warnings: list[str] = []
    for yaml_file in sorted(openapi_dir.glob("*.yaml")) + sorted(openapi_dir.glob("*.yml")):
        try:
            keys = _yaml_scan.read(yaml_file)
        except OSError as exc:
            warnings.append(f"cannot read {yaml_file.name}: {exc!r}")
            continue
        # Only treat real OpenAPI docs (skip oapi-codegen config files).
        top = {k.key for k in keys if k.indent == 0}
        if "openapi" not in top or "paths" not in top:
            continue
        repo_name = _repo_name_from_yaml(yaml_file)
        paths_idx = _yaml_scan.find_top_level(keys, "paths")
        if paths_idx is None:
            continue
        # Security schemes present? (if yes, we may later attempt to classify auth.)
        has_security_schemes = any(
            k.key == "securitySchemes" and k.indent > 0 for k in keys
        )
        global_security = any(k.key == "security" and k.indent == 0 for k in keys)

        # Paths children are `/tickers/...:` entries.
        for path_i in _yaml_scan.children_of(keys, paths_idx):
            path_key = keys[path_i].key
            if not path_key.startswith("/"):
                continue
            path = path_key
            for op_i in _yaml_scan.children_of(keys, path_i):
                verb = keys[op_i].key.lower()
                if verb not in HTTP_VERBS:
                    continue
                auth, _guard = _classify_spec(has_security_schemes, global_security)
                rows.append(
                    EndpointRow(
                        repository=repo_name,
                        method=verb.upper(),
                        path=path,
                        auth=auth,
                        source_kind="OpenAPI spec",
                    )
                )
    return rows, warnings


def _repo_name_from_yaml(file: Path) -> str:
    # Drop extension + trailing version + topic suffixes so rows use the
    # canonical service name: `sbm-strategies-v1.yaml` → `sbm`, `ecm-v1.yaml`
    # → `ecm`, `eck-api.yaml` → `eck`.
    stem = file.stem
    stem = re.sub(r"-v\d+$", "", stem)
    stem = re.sub(r"-api$", "", stem)
    # Strip any trailing topic segment (e.g. `-strategies`, `-market-data`):
    # keep only the leading service code (3 lowercase letters — eck/ecm/sbm).
    m = re.match(r"^([a-z]{3})(?:[-_].*)?$", stem)
    if m:
        return m.group(1)
    return stem


def _classify_spec(has_security_schemes: bool, global_security: bool) -> tuple[str, str]:
    if global_security:
        return Auth.UNSPECIFIED, "spec: global security defined (see securitySchemes)"
    if has_security_schemes:
        return Auth.UNSPECIFIED, "spec: securitySchemes defined but not applied globally"
    return Auth.UNSPECIFIED, "spec: no securitySchemes declared"
