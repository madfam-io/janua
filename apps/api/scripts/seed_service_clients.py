"""
Seed machine (client_credentials) OAuth clients for cross-service auth.

These are the RFC 0024 §P4 consolidation service identities:

- ``zavlo-cfdi-emitter``      — Zavlo → Karafiel CFDI stamping bridge
- ``routecraft-billing-relay`` — RouteCraft → Dhanam billing delegation

Unlike the interactive clients in ``seed_core_clients.py``, these clients:

- allow ONLY the ``client_credentials`` grant (no browser flows),
- have no redirect URIs,
- are confidential (a ``client_secret`` is required), and
- carry a narrow scope allowlist (least privilege).

The client_secret is printed exactly once on creation — store it in the
approved secret store (Enclii/Vault) for the calling service. Never commit it.

Alternative (zero-touch) provisioning: each consumer service's bootstrap can
instead call ``POST /api/v1/oauth/clients/register`` with ``X-Internal-API-Key``
and the same payload shape. This script exists for operator-driven seeding.

Usage:
    cd apps/api
    python scripts/seed_service_clients.py

See docs/service-tokens.md for the full integration contract.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from seed_core_clients import (  # noqa: E402
    _resolve_database_url,
    _seed_clients,
)
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Service (machine-to-machine) client definitions
# ---------------------------------------------------------------------------

SERVICE_CLIENTS: list[dict[str, Any]] = [
    {
        "name": "zavlo-cfdi-emitter",
        "description": (
            "Zavlo → Karafiel CFDI stamping bridge service client "
            "(internal-devops RFC 0024 §P4.2). Emits zavlo.* payment "
            "envelopes to Karafiel's CFDI billing bridge."
        ),
        "audience": "karafiel-api",
        "redirect_uris": [],
        "allowed_scopes": ["cfdi:issue"],
        "grant_types": ["client_credentials"],
        "is_confidential": True,
    },
    {
        "name": "nauta-legal-drafts",
        "description": (
            "Nauta → Karafiel legal document generation service client "
            "(nauta docs/LEGAL_OPS_INTEGRATION_PLAN_2026-08-12.md, step "
            "D3.5). legal:draft creates and compiles service-agreement "
            "drafts and reads generated-document metadata. "
            "legal:client-profile creates and updates the client's own "
            "legal-entity profile (karafiel PR #148). Nothing else."
        ),
        "audience": "karafiel-api",
        "redirect_uris": [],
        "allowed_scopes": ["legal:draft", "legal:client-profile"],
        "grant_types": ["client_credentials"],
        "is_confidential": True,
    },
    {
        "name": "routecraft-billing-relay",
        "description": (
            "RouteCraft → Dhanam billing delegation service client "
            "(internal-devops RFC 0024 §P4.3). Emits signed billing events "
            "and delegated checkout requests to Dhanam's billing APIs."
        ),
        "audience": "dhanam-api",
        "redirect_uris": [],
        "allowed_scopes": ["billing:events"],
        "grant_types": ["client_credentials"],
        "is_confidential": True,
    },
]


async def main() -> None:
    database_url = _resolve_database_url()
    engine = create_async_engine(database_url, echo=False)

    try:
        await _seed_clients(engine, clients=SERVICE_CLIENTS)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        sys.exit(130)
