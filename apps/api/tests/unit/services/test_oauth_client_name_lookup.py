"""
get_client_by_name must survive duplicate names.

Production holds 13 OAuth clients named "Voxa" (created 2026-06-07/08 with
byte-identical redirect_uris and scopes — a retry loop against the
non-idempotent POST /oauth/clients). The lookup used scalar_one_or_none(),
which raises MultipleResultsFound on more than one row, so
/oauth/clients/register raised a 500 on its name-matching fallback for any
duplicated name: the duplicates broke the idempotency path whose whole job is
to prevent duplicates.

It must instead be total and deterministic — oldest row wins — so /register
converges onto the original client.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models import Base, OAuthClient, User, UserStatus
from app.services.oauth_client_service import OAuthClientService


OWNER_ID = uuid.uuid4()


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as s:
        # oauth_clients.created_by is NOT NULL
        s.add(
            User(
                id=OWNER_ID,
                email="owner@janua.test",
                email_verified=True,
                status=UserStatus.ACTIVE,
                is_admin=True,
                is_active=True,
            )
        )
        await s.commit()
        yield s
    await engine.dispose()


def _client(name: str, *, client_id: str, created_at: datetime) -> OAuthClient:
    return OAuthClient(
        id=uuid.uuid4(),
        created_by=OWNER_ID,
        client_id=client_id,
        client_secret_hash="x" * 60,  # NOT NULL; value irrelevant to this lookup
        client_secret_prefix="jns_test",
        name=name,
        redirect_uris=["https://voxa.madfam.io/auth/callback"],
        allowed_scopes=["openid", "profile", "email"],
        grant_types=["authorization_code", "refresh_token"],
        is_active=True,
        is_confidential=True,
        created_at=created_at,
        updated_at=created_at,
    )


@pytest.mark.asyncio
async def test_returns_oldest_when_duplicates_exist(session: AsyncSession):
    """The real shape: many identical clients, one name. Must not raise."""
    base = datetime(2026, 6, 7, 8, 51, 28)
    oldest = _client("Voxa", client_id="jnc_oldest_0000000000", created_at=base)
    session.add(oldest)
    for i in range(1, 13):  # 13 total, matching production
        session.add(
            _client(
                "Voxa",
                client_id=f"jnc_dupe_{i:015d}",
                created_at=base + timedelta(seconds=34 * i),
            )
        )
    await session.commit()

    service = OAuthClientService(session)
    found = await service.get_client_by_name("Voxa")

    assert found is not None
    assert found.client_id == "jnc_oldest_0000000000"


@pytest.mark.asyncio
async def test_single_match_and_no_match_still_behave(session: AsyncSession):
    session.add(
        _client("Solo", client_id="jnc_solo_00000000000", created_at=datetime(2026, 1, 1))
    )
    await session.commit()

    service = OAuthClientService(session)
    assert (await service.get_client_by_name("Solo")).client_id == "jnc_solo_00000000000"
    assert await service.get_client_by_name("does-not-exist") is None
