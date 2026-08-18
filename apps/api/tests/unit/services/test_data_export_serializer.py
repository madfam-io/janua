"""Tests for the canonical data-export serializer.

These tests seed a real in-memory SQLite database with identity records that
carry *sentinel* secret values (never real credentials), run the export, and
assert two things:

1. The export contains the expected non-secret user data (Article 15/20).
2. The export contains NONE of the sentinel secret material — no password
   hash, no MFA seed, no session/OAuth token, no passkey public key, no
   client secret.

The sentinels below are obviously-fake constants; per repo doctrine no real
identity data, tokens, or secrets are used anywhere in the suite.
"""

import uuid
from datetime import datetime, timedelta

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
    UserConsent,
)
from app.services.data_export_serializer import (
    assert_no_secrets,
    build_export_archive,
    collect_organization_users,
    collect_user_export_data,
    contains_secret_values,
    find_secret_fields,
    serialize_export,
)

# NOTE: async tests are auto-detected via ``asyncio_mode = auto`` (pytest.ini),
# so no module-level ``pytest.mark.asyncio`` is applied — that would spuriously
# mark the pure-sync unit tests below as async.

# --- Sentinel secret values (fake; must never appear in any export) ---------
FAKE_PASSWORD_HASH = "SENTINEL-pwdhash-$2b$12$AAAAAAAAAAAAAAAAAAAAAA"
FAKE_MFA_SECRET = "SENTINEL-mfaseed-JBSWY3DPEHPK3PXP"
FAKE_BACKUP_CODES = ["SENTINEL-backup-11111111", "SENTINEL-backup-22222222"]
FAKE_SESSION_TOKEN = "SENTINEL-sesstoken-eyJhbGciOiJIUzI1Ni) .payload.sig"
FAKE_REFRESH_TOKEN = "SENTINEL-refreshtoken-abcdef0123456789"
FAKE_ACCESS_JTI = "SENTINEL-jti-0000-1111"
FAKE_OAUTH_ACCESS = "SENTINEL-oauthaccess-ya29.PROVIDER-TOKEN"
FAKE_OAUTH_REFRESH = "SENTINEL-oauthrefresh-1//PROVIDER-REFRESH"
FAKE_PASSKEY_PUBKEY = "SENTINEL-pubkey-pQECAyYgASFYIAAAA"

ALL_SENTINEL_SECRETS = [
    FAKE_PASSWORD_HASH,
    FAKE_MFA_SECRET,
    *FAKE_BACKUP_CODES,
    FAKE_SESSION_TOKEN,
    FAKE_REFRESH_TOKEN,
    FAKE_ACCESS_JTI,
    FAKE_OAUTH_ACCESS,
    FAKE_OAUTH_REFRESH,
    FAKE_PASSKEY_PUBKEY,
]

# --- Non-secret data we DO expect to see ------------------------------------
USER_EMAIL = "portability.subject@example.test"
USER_FIRST = "Ada"
USER_LAST = "Lovelace"
ORG_NAME = "Analytical Engines Co"


@pytest_asyncio.fixture
async def db_session():
    """Provide a real in-memory SQLite async session with export tables."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    wanted = {
        "users",
        "sessions",
        "passkeys",
        "oauth_accounts",
        "user_consents",
        "organizations",
        "organization_members",
        "audit_logs",
    }
    async with engine.begin() as conn:
        tables = [t for t in Base.metadata.sorted_tables if t.name in wanted]
        await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=tables))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_user(db_session):
    """Seed one user with secrets, an org membership, session, passkey, OAuth."""
    user = User(
        id=uuid.uuid4(),
        email=USER_EMAIL,
        email_verified=True,
        password_hash=FAKE_PASSWORD_HASH,
        first_name=USER_FIRST,
        last_name=USER_LAST,
        username="ada",
        phone="+1-555-0100",
        mfa_enabled=True,
        mfa_secret=FAKE_MFA_SECRET,
        mfa_backup_codes=FAKE_BACKUP_CODES,
        user_metadata={"favorite_language": "Ada"},
        created_at=datetime.utcnow(),
    )
    db_session.add(user)

    org = Organization(id=uuid.uuid4(), name=ORG_NAME, slug="analytical-engines")
    db_session.add(org)
    await db_session.flush()

    db_session.add(
        OrganizationMember(
            id=uuid.uuid4(),
            organization_id=org.id,
            user_id=user.id,
            role="owner",
            status="active",
        )
    )
    db_session.add(
        Session(
            id=uuid.uuid4(),
            user_id=user.id,
            token=FAKE_SESSION_TOKEN,
            refresh_token=FAKE_REFRESH_TOKEN,
            access_token_jti=FAKE_ACCESS_JTI,
            ip_address="203.0.113.7",
            user_agent="pytest-agent/1.0",
            device_name="Test Laptop",
            expires_at=datetime.utcnow() + timedelta(days=1),
        )
    )
    db_session.add(
        Passkey(
            id=uuid.uuid4(),
            user_id=user.id,
            credential_id="cred-abc-123",
            public_key=FAKE_PASSKEY_PUBKEY,
            name="Ada's YubiKey",
            authenticator_attachment="cross-platform",
        )
    )
    db_session.add(
        OAuthAccount(
            id=uuid.uuid4(),
            user_id=user.id,
            provider=OAuthProvider.GITHUB,
            provider_user_id="gh-99",
            provider_email="ada@github.test",
            access_token=FAKE_OAUTH_ACCESS,
            refresh_token=FAKE_OAUTH_REFRESH,
        )
    )
    db_session.add(
        UserConsent(
            id=uuid.uuid4(),
            user_id=user.id,
            client_id="enclii-console",
            scopes=["openid", "profile", "email"],
            granted_at=datetime.utcnow(),
        )
    )
    db_session.add(
        AuditLog(
            id=uuid.uuid4(),
            user_id=user.id,
            action="user.login",
            resource_type="session",
            ip_address="203.0.113.7",
            user_agent="pytest-agent/1.0",
            created_at=datetime.utcnow(),
        )
    )
    await db_session.commit()
    return user


# ===========================================================================
# Content: the export gathers the expected user data
# ===========================================================================


class TestExportContent:
    async def test_export_contains_core_profile(self, db_session, seeded_user):
        data = await collect_user_export_data(db_session, str(seeded_user.id))

        assert data["user"]["email"] == USER_EMAIL
        assert data["user"]["first_name"] == USER_FIRST
        assert data["user"]["last_name"] == USER_LAST
        assert data["user"]["mfa_enabled"] is True
        assert data["user"]["id"] == str(seeded_user.id)

    async def test_export_contains_related_sections(self, db_session, seeded_user):
        data = await collect_user_export_data(db_session, str(seeded_user.id))

        # Org membership + nested org profile
        assert len(data["organization_memberships"]) == 1
        membership = data["organization_memberships"][0]
        assert membership["role"] == "owner"
        assert membership["organization"]["name"] == ORG_NAME

        # OAuth grant (client consent)
        assert len(data["oauth_grants"]) == 1
        assert data["oauth_grants"][0]["client_id"] == "enclii-console"
        assert "openid" in data["oauth_grants"][0]["scopes"]

        # Linked social account metadata (no tokens)
        assert len(data["linked_accounts"]) == 1
        assert data["linked_accounts"][0]["provider"] == "github"
        assert data["linked_accounts"][0]["provider_email"] == "ada@github.test"

        # Sessions metadata
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["device_name"] == "Test Laptop"

        # MFA/passkey metadata
        assert data["security"]["mfa_enabled"] is True
        assert data["security"]["mfa_methods"] == ["totp"]
        assert len(data["security"]["passkeys"]) == 1
        assert data["security"]["passkeys"][0]["name"] == "Ada's YubiKey"

        # Audit logs
        assert len(data["audit_logs"]) == 1
        assert data["audit_logs"][0]["action"] == "user.login"

    async def test_export_metadata_present(self, db_session, seeded_user):
        data = await collect_user_export_data(db_session, str(seeded_user.id))
        meta = data["export_metadata"]
        assert meta["subject_user_id"] == str(seeded_user.id)
        assert meta["article"] == "GDPR Article 15"
        assert meta["portable_only"] is False

    async def test_missing_user_raises(self, db_session):
        with pytest.raises(ValueError):
            await collect_user_export_data(db_session, str(uuid.uuid4()))

    async def test_portable_only_subset_excludes_telemetry(self, db_session, seeded_user):
        data = await collect_user_export_data(db_session, str(seeded_user.id), portable_only=True)
        # Article 20 subset: user-provided data only.
        assert "user" in data
        assert "organization_memberships" in data
        assert "oauth_grants" in data
        # Server-generated telemetry omitted.
        assert "sessions" not in data
        assert "audit_logs" not in data
        assert data["export_metadata"]["article"] == "GDPR Article 20"

    async def test_audit_date_range_filter(self, db_session, seeded_user):
        # A future window should exclude the single (now-timestamped) entry.
        future = datetime.utcnow() + timedelta(days=365)
        data = await collect_user_export_data(
            db_session,
            str(seeded_user.id),
            date_range_start=future,
        )
        assert data["audit_logs"] == []


# ===========================================================================
# Security: the export leaks NO secret material (the critical guarantee)
# ===========================================================================


class TestExportSecretExclusion:
    async def test_no_secret_field_names_in_export(self, db_session, seeded_user):
        data = await collect_user_export_data(db_session, str(seeded_user.id))
        offenders = find_secret_fields(data)
        assert offenders == [], f"secret-like field names leaked: {offenders}"

    async def test_no_sentinel_secret_values_survive(self, db_session, seeded_user):
        data = await collect_user_export_data(db_session, str(seeded_user.id))
        leaked = contains_secret_values(data, ALL_SENTINEL_SECRETS)
        assert leaked is None, f"secret value leaked into export: {leaked!r}"

    async def test_no_secrets_after_json_serialization(self, db_session, seeded_user):
        data = await collect_user_export_data(db_session, str(seeded_user.id))
        raw = serialize_export(data, "json").decode("utf-8")
        for secret in ALL_SENTINEL_SECRETS:
            assert secret not in raw, f"secret {secret!r} present in JSON artifact"
        # Spot-check the specific credential classes the task calls out.
        assert "password_hash" not in raw
        assert "mfa_secret" not in raw
        assert FAKE_PASSWORD_HASH not in raw
        assert FAKE_MFA_SECRET not in raw
        assert FAKE_SESSION_TOKEN not in raw
        assert FAKE_OAUTH_ACCESS not in raw
        assert FAKE_PASSKEY_PUBKEY not in raw

    async def test_portable_export_has_no_secrets(self, db_session, seeded_user):
        data = await collect_user_export_data(db_session, str(seeded_user.id), portable_only=True)
        assert find_secret_fields(data) == []
        assert contains_secret_values(data, ALL_SENTINEL_SECRETS) is None

    async def test_assert_no_secrets_passes_for_clean_export(self, db_session, seeded_user):
        data = await collect_user_export_data(db_session, str(seeded_user.id))
        # Should not raise.
        assert_no_secrets(data)

    def test_assert_no_secrets_raises_on_password_hash(self):
        with pytest.raises(ValueError):
            assert_no_secrets({"user": {"password_hash": FAKE_PASSWORD_HASH}})

    def test_assert_no_secrets_raises_on_mfa_secret(self):
        with pytest.raises(ValueError):
            assert_no_secrets({"nested": [{"mfa_secret": FAKE_MFA_SECRET}]})

    def test_assert_no_secrets_raises_on_token(self):
        with pytest.raises(ValueError):
            assert_no_secrets({"session": {"refresh_token": FAKE_REFRESH_TOKEN}})


# ===========================================================================
# Serialization formats
# ===========================================================================


class TestSerializationFormats:
    async def test_json_roundtrip(self, db_session, seeded_user):
        import json

        data = await collect_user_export_data(db_session, str(seeded_user.id))
        parsed = json.loads(serialize_export(data, "json"))
        assert parsed["user"]["email"] == USER_EMAIL

    async def test_csv_contains_user_row_no_secrets(self, db_session, seeded_user):
        data = await collect_user_export_data(db_session, str(seeded_user.id))
        # CSV flattens the single user record.
        csv_bytes = serialize_export({"users": [data["user"]]}, "csv")
        text = csv_bytes.decode("utf-8")
        assert USER_EMAIL in text
        assert "email" in text  # header
        assert FAKE_PASSWORD_HASH not in text
        assert FAKE_MFA_SECRET not in text

    async def test_xml_well_formed_no_secrets(self, db_session, seeded_user):
        import xml.dom.minidom as minidom

        data = await collect_user_export_data(db_session, str(seeded_user.id))
        xml_bytes = serialize_export(data, "xml")
        # Parses without error => well-formed.
        minidom.parseString(xml_bytes)
        text = xml_bytes.decode("utf-8")
        assert USER_EMAIL in text
        assert FAKE_MFA_SECRET not in text
        assert FAKE_SESSION_TOKEN not in text

    def test_unsupported_format_raises(self):
        with pytest.raises(ValueError):
            serialize_export({"users": []}, "yaml")

    async def test_zip_archive_contains_sections_no_secrets(self, db_session, seeded_user):
        import io
        import zipfile

        data = await collect_user_export_data(db_session, str(seeded_user.id))
        payload = build_export_archive(data, manifest_name="export.json")
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names = archive.namelist()
            assert "export.json" in names
            assert "user.json" in names
            assert "audit_logs.json" in names
            # No secret survives in any archive member.
            for name in names:
                content = archive.read(name).decode("utf-8")
                for secret in ALL_SENTINEL_SECRETS:
                    assert secret not in content


# ===========================================================================
# Bulk / tenant export (admin path)
# ===========================================================================


class TestBulkExport:
    async def test_bulk_user_data_all_users(self, db_session, seeded_user):
        data = await collect_organization_users(db_session, None, export_type="user_data")
        assert data["export_metadata"]["record_count"] == 1
        assert data["users"][0]["email"] == USER_EMAIL
        assert find_secret_fields(data) == []
        assert contains_secret_values(data, ALL_SENTINEL_SECRETS) is None

    async def test_bulk_scoped_to_organization(self, db_session, seeded_user):
        # Resolve the org id from the seeded membership.
        from sqlalchemy import select

        org = (await db_session.execute(select(Organization))).scalars().first()
        data = await collect_organization_users(
            db_session, str(org.id), export_type="organization_data"
        )
        assert data["export_metadata"]["organization_id"] == str(org.id)
        assert any(o["name"] == ORG_NAME for o in data["organizations"])
        assert data["users"][0]["email"] == USER_EMAIL
        assert find_secret_fields(data) == []

    async def test_bulk_audit_logs_only(self, db_session, seeded_user):
        data = await collect_organization_users(db_session, None, export_type="audit_logs")
        assert "audit_logs" in data
        assert data["audit_logs"][0]["action"] == "user.login"
        # user_data section not emitted for audit_logs export.
        assert "users" not in data
        assert find_secret_fields(data) == []

    async def test_empty_org_yields_no_users(self, db_session):
        empty_org_id = str(uuid.uuid4())
        data = await collect_organization_users(db_session, empty_org_id, export_type="user_data")
        assert data["users"] == []
        assert data["export_metadata"]["record_count"] == 0
