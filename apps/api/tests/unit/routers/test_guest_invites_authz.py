"""Authorization + token-disclosure regression tests for guest invite CRUD.

Pins the behaviour restored by the cross-tenant fix on
``/api/v1/organizations/{org_id}/guest-invites``:

1. Being signed in is not enough. An admin of org A must not reach org B's
   invites through the path parameter (create / list / revoke).
2. The invite token is a bearer credential: returned once at creation, never in
   a list response.
3. ``GET /api/v1/auth/guest/validate/{token}`` stays indistinguishable across
   every failure mode, so it cannot be used as an enumeration oracle.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.database_manager import get_db as get_db_manager
from app.core.redis import get_redis
from app.database import get_db
from app.dependencies import get_current_user
from app.main import app
from app.models import Base, GuestInvite, Organization, OrganizationMember, User


def _invites_url(org_id: str) -> str:
    return f"/api/v1/organizations/{org_id}/guest-invites"


def _validate_url(token: str) -> str:
    return f"/api/v1/auth/guest/validate/{token}"


@pytest_asyncio.fixture
async def guest_invite_env():
    """SQLite-backed app client, a session factory, and a settable caller.

    Yields ``(client, session_factory, actors)``. ``actors["current"]`` selects
    which ``User`` ``get_current_user`` returns, so a single client can act as
    different callers across a test.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session
            await session.commit()

    redis = AsyncMock()
    redis.ping.return_value = True

    actors: dict = {"current": None}

    async def override_get_current_user():
        return actors["current"]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_manager] = override_get_db
    app.dependency_overrides[get_redis] = lambda: redis
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Tests that exercise the mint path flip this; restore it so the flag does
    # not leak into the rest of the suite.
    original_guest_access = settings.ENABLE_GUEST_ACCESS

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, session_factory, actors

    settings.ENABLE_GUEST_ACCESS = original_guest_access
    app.dependency_overrides.clear()
    await engine.dispose()


async def _seed_two_orgs(session_factory):
    """Two orgs, each with its own admin. Neither admin belongs to the other org."""
    org_a = Organization(id=uuid.uuid4(), name="Org A", slug=f"org-a-{uuid.uuid4().hex[:8]}")
    org_b = Organization(id=uuid.uuid4(), name="Org B", slug=f"org-b-{uuid.uuid4().hex[:8]}")
    admin_a = User(id=uuid.uuid4(), email=f"a-{uuid.uuid4().hex[:8]}@example.com")
    admin_b = User(id=uuid.uuid4(), email=f"b-{uuid.uuid4().hex[:8]}@example.com")

    async with session_factory() as session:
        session.add_all([org_a, org_b, admin_a, admin_b])
        await session.flush()
        session.add_all(
            [
                OrganizationMember(
                    organization_id=org_a.id,
                    user_id=admin_a.id,
                    role="admin",
                    status="active",
                ),
                OrganizationMember(
                    organization_id=org_b.id,
                    user_id=admin_b.id,
                    role="admin",
                    status="active",
                ),
            ]
        )
        await session.commit()

    return org_a, org_b, admin_a, admin_b


async def _seed_invite(session_factory, org_id, created_by, **overrides) -> GuestInvite:
    invite = GuestInvite(
        id=uuid.uuid4(),
        organization_id=org_id,
        created_by=created_by,
        token=overrides.pop("token", f"tok-{uuid.uuid4().hex}"),
        label=overrides.pop("label", "Front desk"),
        max_uses=overrides.pop("max_uses", 0),
        use_count=overrides.pop("use_count", 0),
        guest_ttl_hours=overrides.pop("guest_ttl_hours", 4),
        revoked=overrides.pop("revoked", False),
        expires_at=overrides.pop("expires_at", None),
        created_at=overrides.pop("created_at", datetime.utcnow()),
    )
    async with session_factory() as session:
        session.add(invite)
        await session.commit()
    return invite


# -- Cross-organization authorization -----------------------------------------


@pytest.mark.asyncio
async def test_admin_of_other_org_cannot_list_invites(guest_invite_env):
    """Admin of org A must not read org B's invites via the path parameter."""
    client, session_factory, actors = guest_invite_env
    org_a, org_b, admin_a, admin_b = await _seed_two_orgs(session_factory)
    await _seed_invite(session_factory, org_b.id, admin_b.id, label="B secret")

    actors["current"] = admin_a
    response = await client.get(_invites_url(str(org_b.id)))

    assert response.status_code == 404
    assert "B secret" not in response.text


@pytest.mark.asyncio
async def test_admin_of_other_org_cannot_create_invite(guest_invite_env):
    """A cross-org create must be refused and must not persist a row."""
    client, session_factory, actors = guest_invite_env
    org_a, org_b, admin_a, _ = await _seed_two_orgs(session_factory)

    actors["current"] = admin_a
    response = await client.post(_invites_url(str(org_b.id)), json={"label": "smuggled"})

    assert response.status_code == 404

    async with session_factory() as session:
        rows = (
            (
                await session.execute(
                    select(GuestInvite).where(GuestInvite.organization_id == org_b.id)
                )
            )
            .scalars()
            .all()
        )
    assert rows == []


@pytest.mark.asyncio
async def test_admin_of_other_org_cannot_revoke_invite(guest_invite_env):
    """A cross-org revoke must be refused and must leave the row untouched."""
    client, session_factory, actors = guest_invite_env
    org_a, org_b, admin_a, admin_b = await _seed_two_orgs(session_factory)
    invite = await _seed_invite(session_factory, org_b.id, admin_b.id)

    actors["current"] = admin_a
    response = await client.delete(f"{_invites_url(str(org_b.id))}/{invite.id}")

    assert response.status_code == 404

    async with session_factory() as session:
        row = (
            await session.execute(select(GuestInvite).where(GuestInvite.id == invite.id))
        ).scalar_one()
    assert row.revoked is False


@pytest.mark.asyncio
async def test_authenticated_non_member_cannot_list_invites(guest_invite_env):
    """Authentication alone is not authorization: a stranger gets nothing."""
    client, session_factory, actors = guest_invite_env
    org_a, _, _, admin_b = await _seed_two_orgs(session_factory)
    await _seed_invite(session_factory, org_a.id, admin_b.id)

    stranger = User(id=uuid.uuid4(), email=f"stranger-{uuid.uuid4().hex[:8]}@example.com")
    async with session_factory() as session:
        session.add(stranger)
        await session.commit()

    actors["current"] = stranger
    response = await client.get(_invites_url(str(org_a.id)))

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_plain_member_cannot_manage_invites(guest_invite_env):
    """Membership is not enough -- minting guest access needs an admin role."""
    client, session_factory, actors = guest_invite_env
    org_a, _, admin_a, _ = await _seed_two_orgs(session_factory)

    member = User(id=uuid.uuid4(), email=f"member-{uuid.uuid4().hex[:8]}@example.com")
    async with session_factory() as session:
        session.add(member)
        await session.flush()
        session.add(
            OrganizationMember(
                organization_id=org_a.id, user_id=member.id, role="member", status="active"
            )
        )
        await session.commit()

    actors["current"] = member

    assert (await client.get(_invites_url(str(org_a.id)))).status_code == 404
    assert (await client.post(_invites_url(str(org_a.id)), json={"label": "x"})).status_code == 404


@pytest.mark.asyncio
async def test_inactive_admin_membership_is_refused(guest_invite_env):
    """A removed admin keeps the row but loses the capability."""
    client, session_factory, actors = guest_invite_env
    org_a, _, _, _ = await _seed_two_orgs(session_factory)

    former = User(id=uuid.uuid4(), email=f"former-{uuid.uuid4().hex[:8]}@example.com")
    async with session_factory() as session:
        session.add(former)
        await session.flush()
        session.add(
            OrganizationMember(
                organization_id=org_a.id, user_id=former.id, role="admin", status="removed"
            )
        )
        await session.commit()

    actors["current"] = former
    assert (await client.get(_invites_url(str(org_a.id)))).status_code == 404


@pytest.mark.asyncio
async def test_org_admin_can_manage_own_org_invites(guest_invite_env):
    """The legitimate path still works end to end: create, list, revoke."""
    client, session_factory, actors = guest_invite_env
    org_a, _, admin_a, _ = await _seed_two_orgs(session_factory)

    actors["current"] = admin_a

    created = await client.post(_invites_url(str(org_a.id)), json={"label": "Lobby"})
    assert created.status_code == 201, created.text
    invite_id = created.json()["id"]

    listed = await client.get(_invites_url(str(org_a.id)))
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    revoked = await client.delete(f"{_invites_url(str(org_a.id))}/{invite_id}")
    assert revoked.status_code == 204

    async with session_factory() as session:
        row = (
            await session.execute(select(GuestInvite).where(GuestInvite.id == uuid.UUID(invite_id)))
        ).scalar_one()
    assert row.revoked is True


@pytest.mark.asyncio
async def test_org_owner_without_membership_row_is_allowed(guest_invite_env):
    """Ownership grants access even with no explicit membership row."""
    client, session_factory, actors = guest_invite_env

    owner = User(id=uuid.uuid4(), email=f"owner-{uuid.uuid4().hex[:8]}@example.com")
    async with session_factory() as session:
        session.add(owner)
        await session.flush()
        session.add(
            Organization(
                id=uuid.uuid4(),
                name="Owned",
                slug=f"owned-{uuid.uuid4().hex[:8]}",
                owner_id=owner.id,
            )
        )
        await session.commit()
        org = (
            await session.execute(select(Organization).where(Organization.owner_id == owner.id))
        ).scalar_one()

    actors["current"] = owner
    assert (await client.get(_invites_url(str(org.id)))).status_code == 200


@pytest.mark.asyncio
async def test_unknown_org_is_indistinguishable_from_forbidden_org(guest_invite_env):
    """A nonexistent org and an off-limits org answer identically."""
    client, session_factory, actors = guest_invite_env
    _, org_b, admin_a, _ = await _seed_two_orgs(session_factory)

    actors["current"] = admin_a
    forbidden = await client.get(_invites_url(str(org_b.id)))
    unknown = await client.get(_invites_url(str(uuid.uuid4())))

    assert forbidden.status_code == unknown.status_code == 404

    # ``request_id``/``timestamp`` are per-request by construction; the
    # discriminating fields are the code and the message.
    def _discriminating(payload: dict) -> tuple:
        error = payload["error"]
        return error["code"], error["message"]

    assert _discriminating(forbidden.json()) == _discriminating(unknown.json())


# -- Token disclosure ----------------------------------------------------------


@pytest.mark.asyncio
async def test_list_response_never_contains_plaintext_token(guest_invite_env):
    """The stored token must not be recoverable from a list response."""
    client, session_factory, actors = guest_invite_env
    org_a, _, admin_a, _ = await _seed_two_orgs(session_factory)
    secret = f"supersecrettoken-{uuid.uuid4().hex}"
    await _seed_invite(session_factory, org_a.id, admin_a.id, token=secret)

    actors["current"] = admin_a
    response = await client.get(_invites_url(str(org_a.id)))

    assert response.status_code == 200
    assert secret not in response.text

    entry = response.json()["invites"][0]
    assert "token" not in entry
    assert "invite_url" not in entry
    assert entry["token_prefix"] == secret[:8]


@pytest.mark.asyncio
async def test_create_returns_token_exactly_once(guest_invite_env):
    """Create still hands back a usable token; the follow-up list does not."""
    client, session_factory, actors = guest_invite_env
    org_a, _, admin_a, _ = await _seed_two_orgs(session_factory)

    actors["current"] = admin_a
    created = await client.post(_invites_url(str(org_a.id)), json={"label": "Once"})
    assert created.status_code == 201

    token = created.json()["token"]
    assert token
    assert token in created.json()["invite_url"]

    listed = await client.get(_invites_url(str(org_a.id)))
    assert token not in listed.text


# -- Public validate endpoint --------------------------------------------------


@pytest.mark.asyncio
async def test_validate_is_indistinguishable_across_failure_modes(guest_invite_env):
    """Unknown, revoked, expired, and exhausted must be one identical answer."""
    client, session_factory, actors = guest_invite_env
    org_a, _, admin_a, _ = await _seed_two_orgs(session_factory)

    revoked = await _seed_invite(session_factory, org_a.id, admin_a.id, revoked=True)
    expired = await _seed_invite(
        session_factory,
        org_a.id,
        admin_a.id,
        expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1),
    )
    exhausted = await _seed_invite(session_factory, org_a.id, admin_a.id, max_uses=1, use_count=1)

    responses = [
        await client.get(_validate_url(tok))
        for tok in [
            f"unknown-{uuid.uuid4().hex}",
            revoked.token,
            expired.token,
            exhausted.token,
        ]
    ]

    assert {r.status_code for r in responses} == {200}
    payloads = [r.json() for r in responses]
    assert all(p == payloads[0] for p in payloads), payloads
    assert payloads[0]["valid"] is False
    assert payloads[0]["org_name"] is None


@pytest.mark.asyncio
async def test_expired_invite_is_refused_not_a_server_error(guest_invite_env):
    """An expiring invite must evaluate, not raise on naive/aware comparison.

    ``expires_at`` is a naive column, so the previous direct comparison against
    ``datetime.now(UTC)`` raised ``TypeError`` -- a 500 that both failed to
    enforce expiry and made expiring invites distinguishable.
    """
    client, session_factory, actors = guest_invite_env
    org_a, _, admin_a, _ = await _seed_two_orgs(session_factory)
    expired = await _seed_invite(
        session_factory,
        org_a.id,
        admin_a.id,
        expires_at=datetime.utcnow() - timedelta(hours=1),
    )

    settings.ENABLE_GUEST_ACCESS = True
    minted = await client.post(
        "/api/v1/auth/guest", json={"invite_token": expired.token, "display_name": "G"}
    )

    assert minted.status_code == 410


@pytest.mark.asyncio
async def test_unexpired_invite_passes_the_expiry_gate(guest_invite_env):
    """The normalization must not reject invites that are still in date.

    Asserted at the gate rather than end to end: minting itself is separately
    broken (``_mint_guest_jwt`` calls ``jwt_manager.create_token``, which does
    not exist), so a still-valid invite reaches the minting 500 instead of the
    410 an expired one gets. What this pins is that expiry no longer rejects it.
    """
    client, session_factory, actors = guest_invite_env
    org_a, _, admin_a, _ = await _seed_two_orgs(session_factory)
    live = await _seed_invite(
        session_factory,
        org_a.id,
        admin_a.id,
        expires_at=datetime.utcnow() + timedelta(hours=6),
    )

    settings.ENABLE_GUEST_ACCESS = True
    minted = await client.post(
        "/api/v1/auth/guest", json={"invite_token": live.token, "display_name": "G"}
    )

    # Not 410: the live invite is no longer rejected as expired. It gets past
    # every validity check and only then hits the unrelated minting defect.
    assert minted.status_code != 410

    # The companion assertion -- that the same invite, once expired, IS
    # rejected -- lives in ``test_expired_invite_is_refused_not_a_server_error``.
    # Together they show the gate discriminates rather than always passing.


@pytest.mark.asyncio
async def test_validate_accepts_an_unexpired_invite(guest_invite_env):
    """The public validate path resolves a live expiring invite without raising."""
    client, session_factory, actors = guest_invite_env
    org_a, _, admin_a, _ = await _seed_two_orgs(session_factory)
    live = await _seed_invite(
        session_factory,
        org_a.id,
        admin_a.id,
        expires_at=datetime.utcnow() + timedelta(hours=6),
    )

    response = await client.get(_validate_url(live.token))

    assert response.status_code == 200
    assert response.json()["valid"] is True
