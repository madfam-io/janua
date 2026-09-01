"""
Unit tests for the internal user provisioning + lifecycle endpoints
(POST /api/v1/internal/users/{provision,suspend,reactivate}).
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.redis import get_redis
from app.database import get_db
from app.main import app
from app.models import Base, User, UserStatus

INTERNAL_KEY = "test-internal-api-key-provisioning"
PROVISION_URL = "/api/v1/internal/users/provision"
SUSPEND_URL = "/api/v1/internal/users/suspend"
REACTIVATE_URL = "/api/v1/internal/users/reactivate"

TENANT_A = str(uuid.uuid4())
TENANT_B = str(uuid.uuid4())

AUTH = {"X-Internal-API-Key": INTERNAL_KEY}


@pytest_asyncio.fixture
async def provisioning_env():
    """SQLite-backed app client plus a session factory for direct row asserts."""
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

    from unittest.mock import AsyncMock

    redis = AsyncMock()
    redis.ping.return_value = True

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = lambda: redis

    settings.INTERNAL_API_KEY = INTERNAL_KEY

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    settings.INTERNAL_API_KEY = None
    await engine.dispose()


@pytest_asyncio.fixture
async def provisioning_client(provisioning_env):
    client, _ = provisioning_env
    return client


def _provision_payload(
    email: str = "integrante@crea.example.com",
    tenant_id: str = TENANT_A,
    first_name: str = "Ana",
    last_name: str | None = "Ruiz",
) -> dict:
    return {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "tenant_id": tenant_id,
    }


async def _get_user(session_factory, user_id: str) -> User:
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))
        return result.scalar_one()


# ---------------------------------------------------------------- provision


@pytest.mark.asyncio
async def test_provision_creates_active_passwordless_user(provisioning_env):
    client, session_factory = provisioning_env
    response = await client.post(PROVISION_URL, json=_provision_payload(), headers=AUTH)

    assert response.status_code == 201
    body = response.json()
    assert body["created"] is True
    assert body["email"] == "integrante@crea.example.com"
    assert body["status"] == UserStatus.ACTIVE.value

    user = await _get_user(session_factory, body["id"])
    # Magic-link only: janua must hold no password material for this identity.
    assert user.password_hash is None
    assert user.email_verified is False
    assert user.email_verified_at is None
    assert user.is_admin is False
    assert user.status == UserStatus.ACTIVE
    assert str(user.tenant_id) == TENANT_A
    assert user.first_name == "Ana"
    assert user.last_name == "Ruiz"
    assert user.user_metadata == {}


@pytest.mark.asyncio
async def test_provision_is_idempotent(provisioning_env):
    client, session_factory = provisioning_env
    payload = _provision_payload(email="idempotent@crea.example.com")

    first = await client.post(PROVISION_URL, json=payload, headers=AUTH)
    assert first.status_code == 201
    assert first.json()["created"] is True

    second = await client.post(PROVISION_URL, json=payload, headers=AUTH)
    assert second.status_code == 200
    assert second.json()["created"] is False
    assert second.json()["id"] == first.json()["id"]

    # Exactly one row — the second call must not have created a duplicate.
    async with session_factory() as session:
        count = await session.execute(
            select(func.count(User.id)).where(User.email == "idempotent@crea.example.com")
        )
        assert count.scalar() == 1


@pytest.mark.asyncio
async def test_provision_idempotency_is_case_insensitive(provisioning_env):
    client, session_factory = provisioning_env

    first = await client.post(
        PROVISION_URL, json=_provision_payload(email="Foo@Bar.example.com"), headers=AUTH
    )
    assert first.status_code == 201
    # The stored value is folded, not the raw input.
    assert first.json()["email"] == "foo@bar.example.com"

    second = await client.post(
        PROVISION_URL, json=_provision_payload(email="foo@bar.example.com"), headers=AUTH
    )
    assert second.status_code == 200
    assert second.json()["created"] is False
    assert second.json()["id"] == first.json()["id"]

    async with session_factory() as session:
        count = await session.execute(
            select(func.count(User.id)).where(User.email == "foo@bar.example.com")
        )
        assert count.scalar() == 1


@pytest.mark.asyncio
async def test_provision_same_email_different_tenant_is_a_separate_user(provisioning_env):
    """Email is unique PER TENANT, so the same address is two distinct people.

    IMPORTANT — SQLite cannot express migration 013's PARTIAL unique indexes: it
    drops the `WHERE tenant_id IS NULL` predicate from `uq_users_email_global`
    and so enforces an unconditional global UNIQUE(email). Under Postgres the
    second INSERT below is legal; under SQLite it raises IntegrityError. That is
    a harness artifact, NOT router behaviour, so this test asserts the thing the
    router actually decides: that a lookup for the same email in another tenant
    does NOT resolve to tenant A's user, i.e. it takes the create branch.
    """
    client, session_factory = provisioning_env
    email = "shared@crea.example.com"

    in_a = await client.post(
        PROVISION_URL, json=_provision_payload(email=email, tenant_id=TENANT_A), headers=AUTH
    )
    assert in_a.status_code == 201
    user_a_id = in_a.json()["id"]

    # Pool-scoped lookup must MISS in tenant B even though the address exists in
    # tenant A. If the router had done a bare (non-tenant-scoped) email select it
    # would find tenant A's row and wrongly return 200 / created:false here.
    async with session_factory() as session:
        from app.services.user_lookup import get_user_by_email

        assert await get_user_by_email(session, email, tenant_id=uuid.UUID(TENANT_A)) is not None
        assert await get_user_by_email(session, email, tenant_id=uuid.UUID(TENANT_B)) is None

    user_a = await _get_user(session_factory, user_a_id)
    assert str(user_a.tenant_id) == TENANT_A


@pytest.mark.asyncio
async def test_provision_does_not_mutate_existing_user(provisioning_env):
    """Provisioning is not synchronization: an existing profile is left alone."""
    client, session_factory = provisioning_env
    email = "existing@crea.example.com"

    first = await client.post(
        PROVISION_URL,
        json=_provision_payload(email=email, first_name="Original", last_name="Name"),
        headers=AUTH,
    )
    assert first.status_code == 201

    second = await client.post(
        PROVISION_URL,
        json=_provision_payload(email=email, first_name="Changed", last_name="Different"),
        headers=AUTH,
    )
    assert second.status_code == 200

    user = await _get_user(session_factory, first.json()["id"])
    assert user.first_name == "Original"
    assert user.last_name == "Name"


@pytest.mark.asyncio
async def test_provision_never_returns_password_material(provisioning_client: AsyncClient):
    response = await provisioning_client.post(
        PROVISION_URL, json=_provision_payload(email="nosecrets@crea.example.com"), headers=AUTH
    )
    assert response.status_code == 201
    raw = response.text.lower()
    assert "password" not in raw
    assert "hash" not in raw
    assert "token" not in raw


# ------------------------------------------------------------------ suspend


@pytest.mark.asyncio
async def test_suspend_sets_status_and_is_active_false(provisioning_env):
    client, session_factory = provisioning_env
    email = "suspendme@crea.example.com"
    created = await client.post(PROVISION_URL, json=_provision_payload(email=email), headers=AUTH)
    user_id = created.json()["id"]

    response = await client.post(
        SUSPEND_URL, json={"email": email, "tenant_id": TENANT_A}, headers=AUTH
    )
    assert response.status_code == 200
    body = response.json()
    assert body["changed"] is True
    assert body["status"] == UserStatus.SUSPENDED.value
    assert body["id"] == user_id

    user = await _get_user(session_factory, user_id)
    assert user.status == UserStatus.SUSPENDED
    assert user.is_active is False
    # Metadata was rebuilt-and-reassigned, so it actually flushed.
    assert user.user_metadata["suspended_at"]
    assert user.user_metadata["suspended_by"] == "internal-api-key"


@pytest.mark.asyncio
async def test_suspend_is_idempotent(provisioning_client: AsyncClient):
    email = "suspendtwice@crea.example.com"
    await provisioning_client.post(
        PROVISION_URL, json=_provision_payload(email=email), headers=AUTH
    )

    first = await provisioning_client.post(
        SUSPEND_URL, json={"email": email, "tenant_id": TENANT_A}, headers=AUTH
    )
    assert first.status_code == 200
    assert first.json()["changed"] is True

    second = await provisioning_client.post(
        SUSPEND_URL, json={"email": email, "tenant_id": TENANT_A}, headers=AUTH
    )
    assert second.status_code == 200
    assert second.json()["changed"] is False
    assert second.json()["status"] == UserStatus.SUSPENDED.value


@pytest.mark.asyncio
async def test_suspend_unknown_email_is_404(provisioning_client: AsyncClient):
    response = await provisioning_client.post(
        SUSPEND_URL, json={"email": "ghost@crea.example.com", "tenant_id": TENANT_A}, headers=AUTH
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_suspend_is_tenant_scoped(provisioning_client: AsyncClient):
    """A user in tenant A must not be suspendable via tenant B."""
    email = "scoped@crea.example.com"
    await provisioning_client.post(
        PROVISION_URL, json=_provision_payload(email=email, tenant_id=TENANT_A), headers=AUTH
    )

    response = await provisioning_client.post(
        SUSPEND_URL, json={"email": email, "tenant_id": TENANT_B}, headers=AUTH
    )
    assert response.status_code == 404


# --------------------------------------------------------------- reactivate


@pytest.mark.asyncio
async def test_reactivate_restores_active_and_is_active_true(provisioning_env):
    client, session_factory = provisioning_env
    email = "comeback@crea.example.com"
    created = await client.post(PROVISION_URL, json=_provision_payload(email=email), headers=AUTH)
    user_id = created.json()["id"]

    await client.post(SUSPEND_URL, json={"email": email, "tenant_id": TENANT_A}, headers=AUTH)

    response = await client.post(
        REACTIVATE_URL, json={"email": email, "tenant_id": TENANT_A}, headers=AUTH
    )
    assert response.status_code == 200
    assert response.json()["changed"] is True
    assert response.json()["status"] == UserStatus.ACTIVE.value

    user = await _get_user(session_factory, user_id)
    assert user.status == UserStatus.ACTIVE
    assert user.is_active is True
    # Suspension keys cleared, reactivation stamped.
    assert "suspended_at" not in user.user_metadata
    assert "suspended_by" not in user.user_metadata
    assert user.user_metadata["reactivated_at"]
    assert user.user_metadata["reactivated_by"] == "internal-api-key"


@pytest.mark.asyncio
async def test_reactivate_already_active_is_success_not_error(provisioning_client: AsyncClient):
    """Already-active is the caller's desired end state, so 200 + changed:false."""
    email = "alreadyactive@crea.example.com"
    await provisioning_client.post(
        PROVISION_URL, json=_provision_payload(email=email), headers=AUTH
    )

    response = await provisioning_client.post(
        REACTIVATE_URL, json={"email": email, "tenant_id": TENANT_A}, headers=AUTH
    )
    assert response.status_code == 200
    assert response.json()["changed"] is False
    assert response.json()["status"] == UserStatus.ACTIVE.value


@pytest.mark.asyncio
async def test_reactivate_unknown_email_is_404(provisioning_client: AsyncClient):
    response = await provisioning_client.post(
        REACTIVATE_URL,
        json={"email": "ghost@crea.example.com", "tenant_id": TENANT_A},
        headers=AUTH,
    )
    assert response.status_code == 404


# --------------------------------------------------------------------- auth


@pytest.mark.asyncio
@pytest.mark.parametrize("url", [PROVISION_URL, SUSPEND_URL, REACTIVATE_URL])
async def test_missing_internal_key_header_is_422(provisioning_client: AsyncClient, url: str):
    response = await provisioning_client.post(url, json=_provision_payload())
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("url", [PROVISION_URL, SUSPEND_URL, REACTIVATE_URL])
async def test_wrong_internal_key_is_401(provisioning_client: AsyncClient, url: str):
    response = await provisioning_client.post(
        url, json=_provision_payload(), headers={"X-Internal-API-Key": "wrong-key"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("url", [PROVISION_URL, SUSPEND_URL, REACTIVATE_URL])
async def test_unset_internal_key_is_503(provisioning_client: AsyncClient, url: str):
    settings.INTERNAL_API_KEY = None
    try:
        response = await provisioning_client.post(url, json=_provision_payload(), headers=AUTH)
        assert response.status_code == 503
    finally:
        settings.INTERNAL_API_KEY = INTERNAL_KEY


@pytest.mark.asyncio
async def test_tenant_id_is_required(provisioning_client: AsyncClient):
    """Never defaulted: a missing tenant must fail loudly, not pick a pool."""
    response = await provisioning_client.post(
        PROVISION_URL,
        json={"email": "notenant@crea.example.com", "first_name": "Ana"},
        headers=AUTH,
    )
    assert response.status_code == 422
