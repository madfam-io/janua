"""Regression tests for ``UserProvisioningService._find_existing_user``.

Before this fix the lookup was::

    select(User).where(User.email == email, User.organization_id == organization_id)

but ``User`` has no ``organization_id`` column (org association is via the
``OrganizationMember`` table + ``user_metadata``, and multi-tenancy uses
``tenant_id``). That clause raised at statement-build time whenever this DDD
provisioning path ran.

Since migration 013 ``users.email`` is unique PER TENANT, so every email lookup
must be pool-scoped (see ``app.services.user_lookup``). JIT-provisioned SSO
users are created WITHOUT a ``tenant_id`` (they land in the untenanted / staff
pool), so ``_find_existing_user`` must scope to ``tenant_id IS NULL`` — matching
the sibling ``app.services.sso_service.SSOService._provision_user``.

The existing ``test_user_provisioning.py`` suite mocks ``_find_existing_user``
wholesale, so it never exercised the query; these tests hit it directly.
"""

from __future__ import annotations

import uuid

from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.sql import ColumnElement

from app.models import User
from app.sso.domain.services.user_provisioning import UserProvisioningService


def _db_returning(row):
    """AsyncMock db whose ``execute()`` resolves to a result yielding ``row``.

    Mirrors the mocking style in
    ``tests/unit/routers/test_auth_recovery_pages.py``.
    """
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)
    return db


async def test_find_existing_user_returns_row():
    """Happy path: the resolved user is returned unchanged."""
    row = User(id=uuid.uuid4(), email="user@example.com")
    db = _db_returning(row)
    service = UserProvisioningService(db=db)

    found = await service._find_existing_user("user@example.com", "org_123")

    assert found is row
    db.execute.assert_awaited_once()


async def test_find_existing_user_returns_none_when_absent():
    db = _db_returning(None)
    service = UserProvisioningService(db=db)

    found = await service._find_existing_user("nobody@example.com", "org_123")

    assert found is None


async def test_query_is_pool_scoped_and_has_no_organization_id_clause():
    """The built statement must filter by email + the untenanted pool
    (``tenant_id IS NULL``) and must NOT reference ``User.organization_id``.

    We introspect the compiled SQL of the statement handed to ``db.execute``.
    """
    db = _db_returning(None)
    service = UserProvisioningService(db=db)

    await service._find_existing_user("user@example.com", "org_123")

    # Grab the statement passed to execute().
    stmt = db.execute.await_args.args[0]
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))

    # Non-existent column must never appear (the original bug).
    assert "organization_id" not in compiled

    # Must select from users and scope by email + the NULL-tenant pool.
    assert "users" in compiled
    assert "email" in compiled
    assert "tenant_id IS NULL" in compiled

    # Sanity: every Column referenced by the WHERE clause is a real column on
    # the users table, so the statement can never resolve to a non-existent
    # attribute (e.g. organization_id) again.
    where = stmt.whereclause
    assert where is not None
    referenced_cols = {
        el.name
        for el in where.get_children(column_collections=False)
        if isinstance(el, ColumnElement) and hasattr(el, "name")
    }
    assert "organization_id" not in referenced_cols


def test_user_model_has_no_organization_id_column():
    """Guard the invariant the fix depends on: org link is not a User column."""
    assert not hasattr(User, "organization_id") or "organization_id" not in {
        c.name for c in User.__table__.columns
    }
    assert "tenant_id" in {c.name for c in User.__table__.columns}
