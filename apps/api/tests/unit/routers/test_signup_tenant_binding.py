"""Unit tests for tenant-bound self-signup — `_resolve_signup_tenant`.

The BaaS Phase-1 slice that makes a client's DB-only signup land a *tenant-scoped*
user: when the app passes its org-bound OAuth ``client_id`` to POST /auth/signup,
the new user is bound to that client's organization (tenant_id + an
OrganizationMember). That, in turn, is what lets the user's data-api token (the
``data-api`` scope, janua#581) carry a ``tenant_id`` so PostgREST scopes their
queries under RLS.

`_resolve_signup_tenant` is the resolution seam. It must be a *soft hint*: any
bad/absent/stale client_id degrades to an ordinary untenanted signup, never a
422 — a signup must not fail because the app mis-passed a client_id.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.routers.v1.auth import _resolve_signup_tenant


def _db_returning(row):
    """AsyncMock db whose execute() resolves to a result yielding `row`."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)
    return db


def _client(*, organization_id=None, is_active=True):
    return SimpleNamespace(
        client_id="jnc_app",
        organization_id=organization_id,
        is_active=is_active,
    )


class TestResolveSignupTenant:
    async def test_none_when_no_client_id(self):
        # The overwhelming common case (platform-staff signup): no hint, no tenant,
        # and — importantly — NO db round-trip.
        db = _db_returning(None)
        assert await _resolve_signup_tenant(db, None) is None
        db.execute.assert_not_awaited()

    async def test_none_when_empty_client_id(self):
        db = _db_returning(None)
        assert await _resolve_signup_tenant(db, "") is None
        db.execute.assert_not_awaited()

    async def test_none_when_client_unknown(self):
        # Stale/mistyped client_id → resolves to nothing, signup proceeds untenanted.
        db = _db_returning(None)
        assert await _resolve_signup_tenant(db, "jnc_missing") is None

    async def test_none_when_client_inactive(self):
        org = uuid4()
        db = _db_returning(_client(organization_id=org, is_active=False))
        assert await _resolve_signup_tenant(db, "jnc_app") is None

    async def test_none_when_client_not_org_bound(self):
        # A real, active client that simply has no organization → no tenant to bind.
        db = _db_returning(_client(organization_id=None))
        assert await _resolve_signup_tenant(db, "jnc_app") is None

    async def test_returns_org_id_for_active_org_bound_client(self):
        org = uuid4()
        db = _db_returning(_client(organization_id=org))
        assert await _resolve_signup_tenant(db, "jnc_app") == org
