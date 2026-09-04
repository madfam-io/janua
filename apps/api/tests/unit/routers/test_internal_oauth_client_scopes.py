"""Unit tests for the internal OAuth-client scope endpoints
(POST /api/v1/internal/oauth-clients/{client_id}/scopes[/revoke], GET .../scopes).

Runs against a REAL SQLite-backed schema rather than mocks, matching
`test_internal_app_roles.py`: `allowed_scopes` is a JSONB column and the bug
this surface most easily grows — mutating the list in place, which SQLAlchemy
does not track and which therefore COMMITS NOTHING while reporting success —
is invisible to a mocked session and obvious against a real one.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.redis import get_redis
from app.database import get_db
from app.main import app
from app.models import Base, OAuthClient, Organization, User, UserStatus

INTERNAL_KEY = "test-internal-api-key-client-scopes"
AUTH = {"X-Internal-API-Key": INTERNAL_KEY}


def _grant_url(client_id: str) -> str:
    return f"/api/v1/internal/oauth-clients/{client_id}/scopes"


def _revoke_url(client_id: str) -> str:
    return f"/api/v1/internal/oauth-clients/{client_id}/scopes/revoke"


@pytest_asyncio.fixture
async def scopes_env():
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


async def _seed_client(
    session_factory,
    *,
    client_id: str = "jnc_nauta",
    allowed_scopes: list[str] | None = None,
    with_org: bool = True,
) -> str:
    """Create an OAuth client (optionally org-bound). Returns its public client_id.

    `created_by` is NOT NULL with an FK to `users`, so an owner row is seeded
    too. No real secret material anywhere: the hash column takes a placeholder
    string, and nothing in this surface ever reads it.
    """
    org_id = uuid.uuid4() if with_org else None
    owner_id = uuid.uuid4()

    async with session_factory() as session:
        if org_id is not None:
            session.add(Organization(id=org_id, name="CREA", slug="crea"))
        session.add(
            User(
                id=owner_id,
                email=f"{client_id}-owner@example.com",
                password_hash=None,
                status=UserStatus.ACTIVE,
                is_admin=False,
                user_metadata={},
            )
        )
        session.add(
            OAuthClient(
                id=uuid.uuid4(),
                organization_id=org_id,
                created_by=owner_id,
                client_id=client_id,
                client_secret_hash="placeholder-not-a-secret",
                client_secret_prefix="jnc_test",
                name=f"{client_id}-edge",
                redirect_uris=[],
                allowed_scopes=allowed_scopes if allowed_scopes is not None else ["openid"],
                grant_types=["client_credentials"],
                is_active=True,
                is_confidential=True,
            )
        )
        await session.commit()

    return client_id


async def _stored_scopes(session_factory, client_id: str) -> list[str]:
    async with session_factory() as session:
        result = await session.execute(
            select(OAuthClient).where(OAuthClient.client_id == client_id)
        )
        return list(result.scalars().first().allowed_scopes or [])


pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------- auth


class TestAuth:
    async def test_missing_key_is_refused(self, scopes_env):
        client, session_factory = scopes_env
        await _seed_client(session_factory)

        response = await client.post(_grant_url("jnc_nauta"), json={"scope": "hcm:hr"})

        assert response.status_code in (401, 422)

    async def test_wrong_key_is_401(self, scopes_env):
        client, session_factory = scopes_env
        await _seed_client(session_factory)

        response = await client.post(
            _grant_url("jnc_nauta"),
            json={"scope": "hcm:hr"},
            headers={"X-Internal-API-Key": "wrong"},
        )

        assert response.status_code == 401


# -------------------------------------------------------------------- grant


class TestGrant:
    async def test_grants_and_persists(self, scopes_env):
        client, session_factory = scopes_env
        await _seed_client(session_factory, allowed_scopes=["openid"])

        response = await client.post(
            _grant_url("jnc_nauta"), json={"scope": "hcm:hr"}, headers=AUTH
        )

        assert response.status_code == 201
        body = response.json()
        assert body["changed"] is True
        assert body["scope"] == "hcm:hr"
        assert sorted(body["allowed_scopes"]) == ["hcm:hr", "openid"]
        # The JSONB write actually landed — the in-place-mutation trap.
        assert sorted(await _stored_scopes(session_factory, "jnc_nauta")) == [
            "hcm:hr",
            "openid",
        ]

    async def test_grant_is_idempotent_and_returns_200(self, scopes_env):
        client, session_factory = scopes_env
        await _seed_client(session_factory, allowed_scopes=["openid", "hcm:hr"])

        response = await client.post(
            _grant_url("jnc_nauta"), json={"scope": "hcm:hr"}, headers=AUTH
        )

        assert response.status_code == 200
        assert response.json()["changed"] is False
        assert sorted(await _stored_scopes(session_factory, "jnc_nauta")) == [
            "hcm:hr",
            "openid",
        ]

    async def test_grant_is_additive(self, scopes_env):
        """The failure mode /oauth/clients/register has: a whole-list write."""
        client, session_factory = scopes_env
        await _seed_client(session_factory, allowed_scopes=["openid", "profile", "kalya:manage"])

        await client.post(_grant_url("jnc_nauta"), json={"scope": "hcm:hr"}, headers=AUTH)

        assert sorted(await _stored_scopes(session_factory, "jnc_nauta")) == [
            "hcm:hr",
            "kalya:manage",
            "openid",
            "profile",
        ]

    async def test_emits_app_role_true_for_org_bound_namespaced_scope(self, scopes_env):
        client, session_factory = scopes_env
        await _seed_client(session_factory, with_org=True)

        response = await client.post(
            _grant_url("jnc_nauta"), json={"scope": "hcm:hr"}, headers=AUTH
        )

        assert response.json()["emits_app_role"] is True

    async def test_emits_app_role_false_without_organization(self, scopes_env):
        """The most common "HCM still says 403" diagnosis, reported at grant time."""
        client, session_factory = scopes_env
        await _seed_client(session_factory, client_id="jnc_orphan", with_org=False)

        response = await client.post(
            _grant_url("jnc_orphan"), json={"scope": "hcm:hr"}, headers=AUTH
        )

        assert response.status_code == 201
        body = response.json()
        assert body["organization_id"] is None
        assert body["emits_app_role"] is False

    async def test_emits_app_role_false_for_underscore_typo(self, scopes_env):
        client, session_factory = scopes_env
        await _seed_client(session_factory)

        response = await client.post(
            _grant_url("jnc_nauta"), json={"scope": "hcm_hr"}, headers=AUTH
        )

        assert response.json()["emits_app_role"] is False

    async def test_unknown_client_is_404(self, scopes_env):
        client, _ = scopes_env

        response = await client.post(_grant_url("jnc_nope"), json={"scope": "hcm:hr"}, headers=AUTH)

        assert response.status_code == 404

    @pytest.mark.parametrize("scope", ["", "   ", "hcm:hr extra"])
    async def test_malformed_scope_is_rejected(self, scopes_env, scope):
        client, session_factory = scopes_env
        await _seed_client(session_factory)

        response = await client.post(_grant_url("jnc_nauta"), json={"scope": scope}, headers=AUTH)

        assert response.status_code == 422


# ------------------------------------------------------------------- revoke


class TestRevoke:
    async def test_revokes_and_persists(self, scopes_env):
        client, session_factory = scopes_env
        await _seed_client(session_factory, allowed_scopes=["openid", "hcm:hr"])

        response = await client.post(
            _revoke_url("jnc_nauta"), json={"scope": "hcm:hr"}, headers=AUTH
        )

        assert response.status_code == 200
        assert response.json()["changed"] is True
        assert await _stored_scopes(session_factory, "jnc_nauta") == ["openid"]

    async def test_revoking_absent_scope_is_success_unchanged(self, scopes_env):
        client, session_factory = scopes_env
        await _seed_client(session_factory, allowed_scopes=["openid"])

        response = await client.post(
            _revoke_url("jnc_nauta"), json={"scope": "hcm:hr"}, headers=AUTH
        )

        assert response.status_code == 200
        assert response.json()["changed"] is False
        assert await _stored_scopes(session_factory, "jnc_nauta") == ["openid"]

    async def test_revoke_leaves_other_scopes_alone(self, scopes_env):
        client, session_factory = scopes_env
        await _seed_client(session_factory, allowed_scopes=["openid", "hcm:hr", "kalya:manage"])

        await client.post(_revoke_url("jnc_nauta"), json={"scope": "hcm:hr"}, headers=AUTH)

        assert sorted(await _stored_scopes(session_factory, "jnc_nauta")) == [
            "kalya:manage",
            "openid",
        ]

    async def test_unknown_client_is_404(self, scopes_env):
        client, _ = scopes_env

        response = await client.post(
            _revoke_url("jnc_nope"), json={"scope": "hcm:hr"}, headers=AUTH
        )

        assert response.status_code == 404


# --------------------------------------------------------------------- list


class TestList:
    async def test_reports_allowed_and_resolved_app_roles(self, scopes_env):
        client, session_factory = scopes_env
        await _seed_client(
            session_factory,
            allowed_scopes=["openid", "hcm:hr", "hcm:admin", "admin", "kalya:manage"],
        )

        response = await client.get(_grant_url("jnc_nauta"), headers=AUTH)

        assert response.status_code == 200
        body = response.json()
        assert sorted(body["allowed_scopes"]) == [
            "admin",
            "hcm:admin",
            "hcm:hr",
            "kalya:manage",
            "openid",
        ]
        # `admin` is an org-membership role and `hcm:admin` keeps its legacy
        # underscore treatment — neither becomes an app role here.
        assert body["app_role_scopes"] == ["hcm:hr", "kalya:manage"]

    async def test_empty_app_roles_without_organization(self, scopes_env):
        client, session_factory = scopes_env
        await _seed_client(
            session_factory,
            client_id="jnc_orphan",
            allowed_scopes=["hcm:hr"],
            with_org=False,
        )

        response = await client.get(_grant_url("jnc_orphan"), headers=AUTH)

        assert response.json()["app_role_scopes"] == []

    async def test_unknown_client_is_404(self, scopes_env):
        client, _ = scopes_env

        response = await client.get(_grant_url("jnc_nope"), headers=AUTH)

        assert response.status_code == 404
