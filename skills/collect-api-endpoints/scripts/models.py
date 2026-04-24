"""Shared dataclasses used by all extractors and the entry-point script.

Keeping these in a standalone module avoids a circular import between
``collect_endpoints.py`` and the per-source extractors.
"""
from __future__ import annotations

import dataclasses
from typing import Any


# Canonical classification of how an endpoint gates access.
# Flat enum — each extractor MUST set `auth` to one of these values.
# Pick the *specific* mechanism when known; `unspecified` only when the
# extractor genuinely cannot determine it (e.g. a spec-only row with no
# implementer in scope).
class Auth:
    PUBLIC = "public"           # no auth gate
    JWT = "jwt"                 # user identity via JWT bearer (Privy / AuthGuard('jwt') / get_current_user)
    OKTA = "okta"               # Okta SSO for admin/staff (OktaAuthGuard / require_admin)
    API_KEY = "api-key"         # service/integration API key header (X-Service-API-Key, AgenticApiKeyGuard, MCP x-api-key)
    SIGNATURE = "signature"     # webhook HMAC signature check (Stripe, Anthropic, verify_internal_secret)
    UNSPECIFIED = "unspecified" # cannot determine (e.g. spec-only, implementer missing)

    ALL = frozenset({PUBLIC, JWT, OKTA, API_KEY, SIGNATURE, UNSPECIFIED})

    # Priority for picking the "most specific" classification when an endpoint
    # is gated by multiple mechanisms (e.g. JWT + admin guard → okta).
    # Higher number wins.
    _PRIORITY = {
        UNSPECIFIED: 0,
        PUBLIC: 1,
        JWT: 2,
        OKTA: 3,
        API_KEY: 4,
        SIGNATURE: 5,
    }

    @classmethod
    def stronger(cls, a: str, b: str) -> str:
        """Return whichever of a/b is the more specific classification."""
        return a if cls._PRIORITY.get(a, 0) >= cls._PRIORITY.get(b, 0) else b


@dataclasses.dataclass
class EndpointRow:
    """One row in the Notion endpoint table."""

    repository: str  # Notion Service column (logical service name)
    method: str  # GET / POST / PUT / PATCH / DELETE / WS / MCP
    path: str
    auth: str  # One of Auth.* (flat enum — see class above)
    source_kind: str  # FastAPI / NestJS / Next.js / MCP / OpenAPI spec / AsyncAPI spec / Go net/http

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)
