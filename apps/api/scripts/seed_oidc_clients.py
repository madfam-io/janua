"""
Seed FIRST-PARTY PUBLIC OIDC clients for the "Sign in with Janua" button.

These are the browser-facing OIDC clients consumed by the rewired
"Sign in with Janua" button (@janua/ui + @janua/nextjs-sdk, PR #447). Each
ecosystem app sets a single PUBLIC env var — ``NEXT_PUBLIC_JANUA_CLIENT_ID`` —
to the stable, human-readable ``client_id`` seeded here, and the button drives
Janua's OIDC provider flow (``GET /api/v1/oauth/authorize`` + PKCE). No per-app
code change is required.

How these differ from ``seed_core_clients.py``:

- **Stable, human-readable ``client_id``** (e.g. ``dhanam-web``), pre-assigned
  here and referenced by each app's ``NEXT_PUBLIC_JANUA_CLIENT_ID``. The
  ``client_id`` is a PUBLIC identifier (OIDC) — safe to commit and print. It is
  NOT a secret.
- **Public client (no usable secret) with PKCE required.** ``is_confidential``
  is ``False``; the OIDC provider (``oauth_provider.py``) then *requires* a
  ``code_challenge`` (PKCE, S256) on ``/authorize`` and skips client_secret
  verification at the token endpoint for these clients. A throwaway secret hash
  is stored only to satisfy the NOT NULL column — it is never emitted and never
  used.
- **``redirect_uris`` match the button's default callback** — ``/auth/callback``
  on each app's real production host (the SDK default is
  ``${origin}/auth/callback``), plus a localhost dev callback.
- **Idempotent upsert keyed on ``client_id``** — safe to re-run.

This script is operator-driven and side-effectful (writes to the OAuth client
registry). Per AGENTS.md it requires an explicit operator request and the
appropriate guard env. It is intentionally NOT run automatically.

Usage:
    cd apps/api
    DATABASE_URL=postgresql://<user>:<pass>@<host>:5432/janua \
        python scripts/seed_oidc_clients.py

Go-live sequence (SSO_CRITICAL_PATH.md § "Sign in with Janua" OIDC rewire):
    1. Run this seed against prod.
    2. Set NEXT_PUBLIC_JANUA_CLIENT_ID for each app (via Enclii) to the
       matching client_id printed below.
    3. Merge PR #447.
"""

from __future__ import annotations

import asyncio
import logging
import os
import secrets
import sys
import uuid
from datetime import datetime
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from seed_core_clients import (  # noqa: E402
    _get_admin_user_id,
    _hash_secret,
    _json_dumps,
    _resolve_database_url,
)
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# First-party PUBLIC OIDC client definitions
# ---------------------------------------------------------------------------
#
# ``client_id`` values are PUBLIC identifiers (OIDC) — each app wires the
# matching value into ``NEXT_PUBLIC_JANUA_CLIENT_ID``. Hosts are derived from
# known ecosystem production domains; any uncertain host carries a ``TODO``
# marker so the operator verifies the callback before go-live.

_OIDC_SCOPES = ["openid", "profile", "email"]
_OIDC_GRANT_TYPES = ["authorization_code", "refresh_token"]

OIDC_CLIENTS: list[dict[str, Any]] = [
    {
        "client_id": "dhanam-web",
        "name": "dhanam-web",
        "description": "Dhanam financial management web app — Sign in with Janua (OIDC/PKCE)",
        "audience": "dhanam-api",
        "redirect_uris": [
            "https://app.dhan.am/auth/callback",
            "http://localhost:3000/auth/callback",
        ],
    },
    {
        "client_id": "enclii-switchyard",
        "name": "enclii-switchyard",
        "description": "Enclii Switchyard platform UI — Sign in with Janua (OIDC/PKCE)",
        "audience": "enclii-api",
        "redirect_uris": [
            "https://app.enclii.dev/auth/callback",
            "http://localhost:3000/auth/callback",
        ],
    },
    {
        "client_id": "enclii-dispatch",
        "name": "enclii-dispatch",
        "description": "Enclii Dispatch admin console — Sign in with Janua (OIDC/PKCE)",
        "audience": "enclii-api",
        "redirect_uris": [
            "https://admin.enclii.dev/auth/callback",
            "http://localhost:3001/auth/callback",
        ],
    },
    {
        "client_id": "yantra4d-web",
        "name": "yantra4d-web",
        # Host resolved 2026-07-08: `app.yantra4d.com` responds 200 (live),
        # while the two alternate candidates from stale docs
        # (`4d-app.madfam.io`, `studio.yantra4d.com`) do not resolve. Matches
        # the enclii domain registry.
        "description": "Yantra4D studio web app — Sign in with Janua (OIDC/PKCE)",
        "audience": "yantra4d-api",
        "redirect_uris": [
            "https://app.yantra4d.com/auth/callback",
            "http://localhost:5173/auth/callback",
        ],
    },
    {
        "client_id": "tezca-web",
        "name": "tezca-web",
        "description": "Tezca Mexican-law platform web app — Sign in with Janua (OIDC/PKCE)",
        "audience": "tezca-api",
        "redirect_uris": [
            "https://tezca.mx/auth/callback",
            "http://localhost:3000/auth/callback",
        ],
    },
    {
        "client_id": "fortuna-web",
        "name": "fortuna-web",
        "description": "Fortuna opportunity-intelligence web app — Sign in with Janua (OIDC/PKCE)",
        # Must match the audience fortuna-api enforces on the Janua JWT, so the
        # OIDC-minted access token carries aud=fortuna (session-API tokens carry
        # the global janua.dev audience and are rejected by fortuna-api).
        "audience": "fortuna",
        "redirect_uris": [
            "https://fortuna.tube/auth/callback",
            "http://localhost:3000/auth/callback",
        ],
    },
    {
        "client_id": "dashboard",
        "name": "dashboard",
        "description": "Janua user dashboard — Sign in with Janua (OIDC/PKCE)",
        "audience": "janua.dev",
        "redirect_uris": [
            "https://app.janua.dev/auth/callback",
            "http://localhost:4101/auth/callback",
        ],
    },
]


# ---------------------------------------------------------------------------
# Seeding logic
# ---------------------------------------------------------------------------


def _throwaway_secret_hash() -> str:
    """Return a bcrypt hash of a random, non-recoverable value.

    Public (PKCE) clients never authenticate with a client_secret, but the
    ``client_secret_hash`` column is NOT NULL. We store a random hash that is
    never emitted and never usable rather than a well-known placeholder.
    """
    return _hash_secret(secrets.token_urlsafe(32))


async def _seed_oidc_clients(engine: AsyncEngine) -> None:
    """Idempotently upsert the public OIDC clients, keyed on ``client_id``."""
    admin_id = await _get_admin_user_id(engine)
    now = datetime.utcnow()  # naive UTC — matches DB column type

    created_count = 0
    updated_count = 0

    async with engine.begin() as conn:
        for client_def in OIDC_CLIENTS:
            client_id = client_def["client_id"]
            name = client_def["name"]

            existing = await conn.execute(
                text("SELECT id FROM oauth_clients WHERE client_id = :cid"),
                {"cid": client_id},
            )
            existing_row = existing.fetchone()

            if existing_row is not None:
                await conn.execute(
                    text(
                        """
                        UPDATE oauth_clients
                           SET name = :name,
                               description = :description,
                               redirect_uris = CAST(:redirect_uris AS jsonb),
                               allowed_scopes = CAST(:allowed_scopes AS jsonb),
                               grant_types = CAST(:grant_types AS jsonb),
                               audience = :audience,
                               is_active = true,
                               is_confidential = false,
                               updated_at = :now
                         WHERE id = :id
                        """
                    ),
                    {
                        "id": str(existing_row[0]),
                        "name": name,
                        "description": client_def.get("description"),
                        "redirect_uris": _json_dumps(client_def["redirect_uris"]),
                        "allowed_scopes": _json_dumps(_OIDC_SCOPES),
                        "grant_types": _json_dumps(_OIDC_GRANT_TYPES),
                        "audience": client_def.get("audience"),
                        "now": now,
                    },
                )
                logger.info("SYNC  %-20s (public OIDC client already exists)", client_id)
                updated_count += 1
                continue

            secret_hash = _throwaway_secret_hash()
            await conn.execute(
                text(
                    """
                    INSERT INTO oauth_clients (
                        id,
                        created_by,
                        client_id,
                        client_secret_hash,
                        client_secret_prefix,
                        name,
                        description,
                        redirect_uris,
                        allowed_scopes,
                        grant_types,
                        audience,
                        is_active,
                        is_confidential,
                        created_at,
                        updated_at
                    ) VALUES (
                        :id,
                        :created_by,
                        :client_id,
                        :client_secret_hash,
                        :client_secret_prefix,
                        :name,
                        :description,
                        CAST(:redirect_uris AS jsonb),
                        CAST(:allowed_scopes AS jsonb),
                        CAST(:grant_types AS jsonb),
                        :audience,
                        true,
                        false,
                        :now,
                        :now
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "created_by": str(admin_id),
                    "client_id": client_id,
                    "client_secret_hash": secret_hash,
                    # Public client — no usable secret. Marker instead of a prefix.
                    "client_secret_prefix": "public",
                    "name": name,
                    "description": client_def.get("description"),
                    "redirect_uris": _json_dumps(client_def["redirect_uris"]),
                    "allowed_scopes": _json_dumps(_OIDC_SCOPES),
                    "grant_types": _json_dumps(_OIDC_GRANT_TYPES),
                    "audience": client_def.get("audience"),
                    "now": now,
                },
            )
            logger.info("NEW   %-20s (public OIDC client, PKCE required)", client_id)
            created_count += 1

    _print_mapping()
    logger.info(
        "Done. Created %d, synced %d existing public OIDC client(s).",
        created_count,
        updated_count,
    )


def _print_mapping() -> None:
    """Print the client_id → app → redirect_uri map (all values are public)."""
    print(f"\n{'=' * 72}")
    print("  Public OIDC clients for the \"Sign in with Janua\" button")
    print("  Set each app's NEXT_PUBLIC_JANUA_CLIENT_ID to the client_id below.")
    print("  client_id is a PUBLIC (PKCE-protected) identifier — NOT a secret.")
    print(f"{'=' * 72}")
    for client_def in OIDC_CLIENTS:
        prod_uri = next(
            (u for u in client_def["redirect_uris"] if u.startswith("https://")),
            client_def["redirect_uris"][0],
        )
        print(f"  NEXT_PUBLIC_JANUA_CLIENT_ID={client_def['client_id']:<18} "
              f"-> {prod_uri}")
    print(f"{'=' * 72}\n")


async def main() -> None:
    database_url = _resolve_database_url()
    engine = create_async_engine(database_url, echo=False)

    try:
        await _seed_oidc_clients(engine)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        sys.exit(130)
