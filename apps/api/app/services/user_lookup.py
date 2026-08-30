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
