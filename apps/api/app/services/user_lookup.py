"""Tenant-aware user lookup by email.

Since migration 013, ``users.email`` is unique PER TENANT, not globally: the same
address can exist once in each tenant's pool AND once in the untenanted (staff /
platform) pool. That means a bare ``select(User).where(User.email == x)`` can now
match MORE THAN ONE row, so:

- ``.scalar_one_or_none()`` on it can raise ``MultipleResultsFound``, and
- ``.first()`` / ``.scalar()`` on it silently return an ARBITRARY row — which,
  across tenants, is a cross-tenant identity confusion (log in as the wrong
  tenant's user).

Every email lookup must therefore declare WHICH pool it means. These helpers are
the single primitive for that. Passing ``tenant_id=None`` scopes to the
untenanted pool and reproduces EXACTLY the pre-013 behaviour for staff/platform
identities — which is what the great majority of existing call sites want.

There is deliberately no "search every pool" helper: an email is not a global
identifier any more, and code that wants a user must know the tenant context it
is operating in (an OAuth client's org for an end-user flow, ``None`` for the
platform pool, the target org for an admin/SCIM/SSO provisioning op).
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, UserStatus


def _scope_by_pool(stmt, tenant_id: Optional[UUID]):
    """Constrain a User select to a single email-uniqueness pool.

    tenant_id is a real UUID → that tenant's pool; None → the untenanted pool
    (``tenant_id IS NULL``). This mirrors the two partial unique indexes from
    migration 013 exactly, so a lookup can match at most one row.
    """
    if tenant_id is None:
        return stmt.where(User.tenant_id.is_(None))
    return stmt.where(User.tenant_id == tenant_id)


async def get_user_by_email(
    db: AsyncSession,
    email: str,
    *,
    tenant_id: Optional[UUID] = None,
    active_only: bool = False,
) -> Optional[User]:
    """Return the single user with ``email`` in the given pool, or None.

    Because the lookup is pool-scoped it matches at most one row, so
    ``scalar_one_or_none`` is safe again. ``tenant_id=None`` is the untenanted /
    staff pool (pre-013 behaviour). ``active_only=True`` additionally requires
    ``status == ACTIVE`` (some callers filter this inline today).
    """
    stmt = select(User).where(User.email == email)
    stmt = _scope_by_pool(stmt, tenant_id)
    if active_only:
        stmt = stmt.where(User.status == UserStatus.ACTIVE)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


class AmbiguousEmailAcrossPools(Exception):
    """More than one ACTIVE user holds this email and no preference resolved it.

    Raised by :func:`resolve_user_by_email_across_pools` only in the world
    migration 013 creates. Callers must surface this as a 4xx — picking a row
    arbitrarily is the cross-tenant identity confusion the module docstring
    warns about.
    """

    def __init__(self, email: str, count: int):
        self.email = email
        self.count = count
        super().__init__(f"{count} active users share the email {email!r} across pools")


async def resolve_user_by_email_across_pools(
    db: AsyncSession,
    email: str,
    *,
    preferred_tenant_id: Optional[UUID] = None,
    active_only: bool = True,
) -> Optional[User]:
    """BRIDGE helper: find the one user holding ``email`` in ANY pool.

    WHY THIS EXISTS, given the module docstring says there is deliberately no
    "search every pool" helper. Migration 013 was written but NEVER APPLIED in
    production: prod's ``alembic_version`` is 011, the DB is hand-migrated, and
    ``users.email`` still carries the GLOBAL unique index ``ix_users_email``
    from 000_init. So the code assumed per-tenant pools while the schema
    enforced one global namespace, and the two disagreed with a user-visible
    outage: the bare-email entry points (magic link, /signin) look only in the
    untenanted pool, missed every user the internal provisioning API had
    created WITH a ``tenant_id`` (CTM staff via crea-map), and the "not found →
    create" branch then hit ``ix_users_email`` → IntegrityError → 503. Nobody
    got a magic link (2026-09-03, 21 users).

    WHILE THE SCHEMA IS GLOBALLY UNIQUE this lookup is EXACT: at most one row
    can hold the address, so "across pools" and "the user" are the same thing.
    It is therefore not an abandonment of pool discipline but its bridge:

    - ``preferred_tenant_id`` (the pool of the OAuth client owning the request's
      redirect host) is consulted FIRST, so the day 013 does land and two pools
      may legitimately hold the address, this resolves to the right one.
    - If no preference matches and MORE THAN ONE row remains, it raises
      :class:`AmbiguousEmailAcrossPools` rather than returning an arbitrary row.

    Callers that know their tenant context must keep using
    :func:`get_user_by_email`; this is only for the bare-email entry points that
    have no tenant to declare.
    """
    stmt = select(User).where(User.email == email)
    if active_only:
        stmt = stmt.where(User.status == UserStatus.ACTIVE)
    result = await db.execute(stmt)
    users = list(result.scalars().all())

    if not users:
        return None
    if len(users) == 1:
        return users[0]

    if preferred_tenant_id is not None:
        preferred = [u for u in users if u.tenant_id == preferred_tenant_id]
        if len(preferred) == 1:
            return preferred[0]

    raise AmbiguousEmailAcrossPools(email, len(users))
