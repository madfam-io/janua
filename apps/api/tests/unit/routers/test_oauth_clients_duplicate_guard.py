"""
POST /api/v1/oauth/clients must not silently mint a duplicate.

Unlike /oauth/clients/register — idempotent and convergent since 2026-05-22 —
the human-facing create path had no duplicate check at all. On 2026-06-07/08 it
produced 13 clients named "Voxa" with byte-identical redirect_uris and scopes,
the active one 34 seconds after the first, each carrying its own secret. Twelve
were later deactivated rather than deleted.

The dashboard made that easy: when its list request failed it rendered "No
OAuth clients yet — create your first" (fixed separately), so the honest
response to a broken screen was to press Create again.

A name collision is now rejected with 409 naming the existing client_id.
Rejecting rather than silently reconciling is deliberate on this path: the
caller chose a name, and quietly handing back someone else's client would be
its own surprise. Secret rotation never needs a second client —
POST /{client_id}/rotate rotates with a grace period — so this costs no
legitimate flow. `allow_duplicate: true` remains as a deliberate override.
"""

from __future__ import annotations

import json

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.redis import get_redis
from app.database import get_db
from app.dependencies import get_current_user
from app.main import app
from app.models import Base, User, UserStatus

CREATE_URL = "/api/v1/oauth/clients"


@pytest_asyncio.fixture
async def api() -> AsyncClient:
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

    actor = User(
        id=uuid.uuid4(),
        email="operator@janua.test",
        email_verified=True,
        status=UserStatus.ACTIVE,
        is_admin=True,
        is_active=True,
    )
    async with session_factory() as session:
        session.add(actor)
        await session.commit()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = lambda: redis
    app.dependency_overrides[get_current_user] = lambda: actor

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


def _payload(name: str = "Voxa", **extra) -> dict:
    return {
        "name": name,
        "redirect_uris": ["https://voxa.madfam.io/auth/callback"],
        "allowed_scopes": ["openid", "profile", "email"],
        "grant_types": ["authorization_code", "refresh_token"],
        "is_confidential": True,
        **extra,
    }


@pytest.mark.asyncio
async def test_repeated_identical_create_is_rejected(api: AsyncClient):
    """The Voxa shape: press Create twice, get one client and a 409."""
    first = await api.post(CREATE_URL, json=_payload())
    assert first.status_code == 201, first.text
    existing_client_id = first.json()["client_id"]

    second = await api.post(CREATE_URL, json=_payload())
    assert second.status_code == 409, second.text

    body = second.json()
    detail = body.get("detail") or json.dumps(body)
    # The caller must be able to act on the response without another lookup.
    assert existing_client_id in detail
    assert "rotate" in detail

    listed = await api.get(CREATE_URL)
    assert listed.status_code == 200
    assert [c["name"] for c in listed.json()["clients"]].count("Voxa") == 1


@pytest.mark.asyncio
async def test_allow_duplicate_is_an_explicit_escape_hatch(api: AsyncClient):
    first = await api.post(CREATE_URL, json=_payload())
    assert first.status_code == 201

    second = await api.post(CREATE_URL, json=_payload(allow_duplicate=True))
    assert second.status_code == 201, second.text
    assert second.json()["client_id"] != first.json()["client_id"]


@pytest.mark.asyncio
async def test_distinct_names_are_unaffected(api: AsyncClient):
    for name in ("Voxa", "Karafiel", "tulana-web-production"):
        created = await api.post(CREATE_URL, json=_payload(name))
        assert created.status_code == 201, created.text
