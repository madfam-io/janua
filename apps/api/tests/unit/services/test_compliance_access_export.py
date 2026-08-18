"""Integration test for the live GDPR access-request export path.

Exercises ``DataSubjectRightsService.process_access_request`` end-to-end
against a real in-memory SQLite database and asserts the enriched export
(profile + memberships + sessions + MFA/passkey + OAuth + audit logs) is
returned and carries no secret material.

This is the code path actually wired to
``GET /api/v1/compliance/data-subject-request/{id}/data``.
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import (
    AuditLog,
    Base,
    OAuthAccount,
    OAuthProvider,
    Organization,
    OrganizationMember,
    Passkey,
    Session,
    User,
)
from app.models.compliance import DataSubjectRequest, DataSubjectRequestType, RequestStatus
from app.services.compliance_service import DataSubjectRightsService
from app.services.data_export_serializer import contains_secret_values, find_secret_fields

FAKE_PASSWORD_HASH = "SENTINEL-pwdhash-$2b$12$COMPLIANCEAAAAAAAAAA"
FAKE_MFA_SECRET = "SENTINEL-mfaseed-COMPLIANCEXYZ"
FAKE_SESSION_TOKEN = "SENTINEL-sesstoken-compliance.header.sig"
FAKE_OAUTH_ACCESS = "SENTINEL-oauthaccess-compliance-provider"
FAKE_PASSKEY_PUBKEY = "SENTINEL-pubkey-compliance-cose"
ALL_SECRETS = [
    FAKE_PASSWORD_HASH,
    FAKE_MFA_SECRET,
    FAKE_SESSION_TOKEN,
    FAKE_OAUTH_ACCESS,
    FAKE_PASSKEY_PUBKEY,
]


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    # Create every table the compliance models declare (they cross-reference
    # users/consent/privacy); this keeps the access-request query valid.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def access_request(db_session):
    user = User(
        id=uuid.uuid4(),
        email="dsr.subject@example.test",
        first_name="Grace",
        last_name="Hopper",
        password_hash=FAKE_PASSWORD_HASH,
        mfa_enabled=True,
        mfa_secret=FAKE_MFA_SECRET,
        created_at=datetime.utcnow(),
    )
    db_session.add(user)

    org = Organization(id=uuid.uuid4(), name="Compilers Inc", slug="compilers")
    db_session.add(org)
    await db_session.flush()

    db_session.add(
        OrganizationMember(
            id=uuid.uuid4(),
            organization_id=org.id,
            user_id=user.id,
            role="admin",
            status="active",
        )
    )
    db_session.add(
        Session(
            id=uuid.uuid4(),
            user_id=user.id,
            token=FAKE_SESSION_TOKEN,
            expires_at=datetime.utcnow() + timedelta(days=1),
        )
    )
    db_session.add(
        Passkey(
            id=uuid.uuid4(),
            user_id=user.id,
            credential_id="cred-grace-1",
            public_key=FAKE_PASSKEY_PUBKEY,
            name="Grace's Passkey",
        )
    )
    db_session.add(
        OAuthAccount(
            id=uuid.uuid4(),
            user_id=user.id,
            provider=OAuthProvider.GOOGLE,
            provider_user_id="g-1",
            provider_email="grace@google.test",
            access_token=FAKE_OAUTH_ACCESS,
        )
    )
    db_session.add(
        AuditLog(
            id=uuid.uuid4(),
            user_id=user.id,
            action="user.password_changed",
            created_at=datetime.utcnow(),
        )
    )

    request = DataSubjectRequest(
        request_id="DSR-TEST-ACCESS-0001",
        user_id=user.id,
        request_type=DataSubjectRequestType.ACCESS,
        status=RequestStatus.RECEIVED,
        received_at=datetime.utcnow(),
        response_due_date=datetime.utcnow() + timedelta(days=30),
    )
    db_session.add(request)
    await db_session.commit()
    return user, request


class TestProcessAccessRequest:
    async def test_returns_enriched_export(self, db_session, access_request):
        user, request = access_request
        service = DataSubjectRightsService(db_session, AsyncMock())

        data = await service.process_access_request(request.request_id, processor_id=user.id)

        # Historical shape preserved.
        assert data["personal_information"]["email"] == "dsr.subject@example.test"
        # New real sections populated (previously empty stubs).
        assert data["profile"]["email"] == "dsr.subject@example.test"
        assert len(data["organization_memberships"]) == 1
        assert data["organization_memberships"][0]["organization"]["name"] == "Compilers Inc"
        assert len(data["sessions"]) == 1
        assert data["security"]["mfa_enabled"] is True
        assert len(data["security"]["passkeys"]) == 1
        assert len(data["linked_accounts"]) == 1
        assert data["linked_accounts"][0]["provider"] == "google"
        assert len(data["audit_logs"]) == 1

    async def test_export_has_no_secret_material(self, db_session, access_request):
        user, request = access_request
        service = DataSubjectRightsService(db_session, AsyncMock())

        data = await service.process_access_request(request.request_id, processor_id=user.id)

        # No secret-like field names, no sentinel values.
        assert find_secret_fields(data) == []
        assert contains_secret_values(data, ALL_SECRETS) is None

    async def test_request_marked_completed(self, db_session, access_request):
        user, request = access_request
        service = DataSubjectRightsService(db_session, AsyncMock())

        await service.process_access_request(request.request_id, processor_id=user.id)
        await db_session.refresh(request)
        assert request.status == RequestStatus.COMPLETED
        assert request.completed_at is not None

    async def test_wrong_request_type_rejected(self, db_session, access_request):
        user, request = access_request
        # Flip to an erasure request; access processor must reject it.
        request.request_type = DataSubjectRequestType.ERASURE
        await db_session.commit()

        service = DataSubjectRightsService(db_session, AsyncMock())
        with pytest.raises(ValueError):
            await service.process_access_request(request.request_id, processor_id=user.id)
