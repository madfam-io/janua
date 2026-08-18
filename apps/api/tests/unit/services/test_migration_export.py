"""Tests for the admin bulk/tenant export via MigrationService.export_users.

Seeds a real in-memory SQLite DB with users carrying sentinel secrets and
asserts the serialized bulk export honors ``export_type`` / ``format`` and
never leaks credential material.
"""

import json
import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import (
    AuditLog,
    Base,
    Organization,
    OrganizationMember,
    Session,
    User,
)
from app.services.data_export_serializer import contains_secret_values, find_secret_fields
from app.services.migration_service import MigrationService

FAKE_PASSWORD_HASH = "SENTINEL-pwdhash-$2b$12$ZZZZZZZZZZZZZZZZZZZZ"
FAKE_MFA_SECRET = "SENTINEL-mfaseed-KRSXG5CTMVRXEZLU"
FAKE_SESSION_TOKEN = "SENTINEL-sesstoken-header.payload.signature"
ALL_SECRETS = [FAKE_PASSWORD_HASH, FAKE_MFA_SECRET, FAKE_SESSION_TOKEN]


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    wanted = {"users", "sessions", "organizations", "organization_members", "audit_logs"}
    async with engine.begin() as conn:
        tables = [t for t in Base.metadata.sorted_tables if t.name in wanted]
        await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=tables))
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def two_users(db_session):
    org = Organization(id=uuid.uuid4(), name="Bulk Org", slug="bulk-org")
    db_session.add(org)
    await db_session.flush()

    users = []
    for i in range(2):
        user = User(
            id=uuid.uuid4(),
            email=f"bulk{i}@example.test",
            first_name=f"User{i}",
            password_hash=FAKE_PASSWORD_HASH,
            mfa_enabled=True,
            mfa_secret=FAKE_MFA_SECRET,
            created_at=datetime.utcnow(),
        )
        users.append(user)
        db_session.add(user)
        await db_session.flush()
        db_session.add(
            OrganizationMember(
                id=uuid.uuid4(),
                organization_id=org.id,
                user_id=user.id,
                role="member",
                status="active",
            )
        )
        db_session.add(
            Session(
                id=uuid.uuid4(),
                # Per-user unique token (sessions.token is UNIQUE) — still a
                # sentinel value that must never reach the export.
                token=f"{FAKE_SESSION_TOKEN}-{i}",
                user_id=user.id,
                expires_at=datetime.utcnow() + timedelta(days=1),
            )
        )
        db_session.add(
            AuditLog(
                id=uuid.uuid4(),
                user_id=user.id,
                action="user.created",
                created_at=datetime.utcnow(),
            )
        )
    await db_session.commit()
    return org, users


class TestBulkExportUsers:
    async def test_json_user_data_contains_users_no_secrets(self, db_session, two_users):
        service = MigrationService()
        payload = await service.export_users(
            None, format="json", export_type="user_data", session=db_session
        )
        parsed = json.loads(payload)
        emails = {u["email"] for u in parsed["users"]}
        assert emails == {"bulk0@example.test", "bulk1@example.test"}
        # No secret material anywhere.
        assert find_secret_fields(parsed) == []
        assert contains_secret_values(parsed, ALL_SECRETS) is None
        raw = payload.decode("utf-8")
        assert FAKE_PASSWORD_HASH not in raw
        assert FAKE_MFA_SECRET not in raw
        assert FAKE_SESSION_TOKEN not in raw

    async def test_scoped_to_organization(self, db_session, two_users):
        org, _ = two_users
        service = MigrationService()
        payload = await service.export_users(
            str(org.id), format="json", export_type="user_data", session=db_session
        )
        parsed = json.loads(payload)
        assert parsed["export_metadata"]["organization_id"] == str(org.id)
        assert len(parsed["users"]) == 2

    async def test_organization_data_groups_orgs(self, db_session, two_users):
        org, _ = two_users
        service = MigrationService()
        payload = await service.export_users(
            str(org.id),
            format="json",
            export_type="organization_data",
            session=db_session,
        )
        parsed = json.loads(payload)
        assert any(o["name"] == "Bulk Org" for o in parsed["organizations"])
        assert len(parsed["users"]) == 2
        assert find_secret_fields(parsed) == []

    async def test_audit_logs_export(self, db_session, two_users):
        service = MigrationService()
        payload = await service.export_users(
            None, format="json", export_type="audit_logs", session=db_session
        )
        parsed = json.loads(payload)
        assert "audit_logs" in parsed
        assert len(parsed["audit_logs"]) == 2
        assert "users" not in parsed
        assert find_secret_fields(parsed) == []

    async def test_csv_format_no_secrets(self, db_session, two_users):
        service = MigrationService()
        payload = await service.export_users(
            None, format="csv", export_type="user_data", session=db_session
        )
        text = payload.decode("utf-8")
        assert "bulk0@example.test" in text
        assert "email" in text  # header row
        assert FAKE_PASSWORD_HASH not in text
        assert FAKE_MFA_SECRET not in text

    async def test_xml_format_well_formed_no_secrets(self, db_session, two_users):
        import xml.dom.minidom as minidom

        service = MigrationService()
        payload = await service.export_users(
            None, format="xml", export_type="user_data", session=db_session
        )
        minidom.parseString(payload)  # raises if malformed
        text = payload.decode("utf-8")
        assert FAKE_MFA_SECRET not in text

    async def test_export_is_bytes(self, db_session, two_users):
        service = MigrationService()
        payload = await service.export_users(None, export_type="user_data", session=db_session)
        assert isinstance(payload, bytes)


class TestExportUsersReplacesStub:
    async def test_no_longer_returns_empty_placeholder(self, db_session, two_users):
        """The old stub returned b'{"users": []}' regardless of DB contents."""
        service = MigrationService()
        payload = await service.export_users(None, export_type="user_data", session=db_session)
        assert payload != b'{"users": []}'
        parsed = json.loads(payload)
        assert len(parsed["users"]) == 2
