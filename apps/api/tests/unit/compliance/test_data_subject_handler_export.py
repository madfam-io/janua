"""Tests for the DataSubjectRequestHandler export implementation.

The ``app/compliance/__init__.py`` package eagerly imports monitoring modules
that carry *pre-existing* broken imports (e.g. ``app.monitoring.stability``)
unrelated to data export. Following the established convention in
``tests/unit/compliance/test_privacy_module.py``, we load the handler module
*directly* (bypassing the package ``__init__``) with its ``..audit`` dependency
stubbed, then exercise its real serialization methods against an in-memory DB.

The methods under test are the ones this task implements:
``_collect_user_data`` / ``_collect_portable_data`` / ``_generate_data_export``
/ ``_create_erasure_backup`` — previously stubs returning fake paths / empty
dicts. We assert they return real, secret-free data and real artifacts.
"""

import importlib.util
import os
import sys
import types
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import AuditLog, Base, Passkey, Session, User
from app.services.data_export_serializer import contains_secret_values, find_secret_fields

# tests/unit/compliance/<this file> -> apps/api is four parents up.
API_ROOT = Path(__file__).resolve().parents[3]
HANDLER_PATH = API_ROOT / "app" / "compliance" / "privacy" / "data_subject_handler.py"

FAKE_PASSWORD_HASH = "SENTINEL-pwdhash-$2b$12$HANDLERAAAAAAAAAAAA"
FAKE_MFA_SECRET = "SENTINEL-mfaseed-HANDLERXYZ"
FAKE_SESSION_TOKEN = "SENTINEL-sesstoken-handler.header.sig"
FAKE_PASSKEY_PUBKEY = "SENTINEL-pubkey-handler-cose"
ALL_SECRETS = [FAKE_PASSWORD_HASH, FAKE_MFA_SECRET, FAKE_SESSION_TOKEN, FAKE_PASSKEY_PUBKEY]


def _load_handler_module():
    """Load data_subject_handler.py in isolation with ..audit stubbed.

    Registers lightweight stand-ins for ``app.compliance`` /
    ``app.compliance.audit`` / ``app.compliance.privacy`` so the module's
    ``from ..audit import ...`` and relative imports resolve without triggering
    the package ``__init__`` side effects.
    """
    # Stub the audit names the handler imports.
    audit_stub = types.ModuleType("app.compliance.audit")

    class AuditEventType:
        DATA_ACCESS = "data_access"

    class EvidenceType:
        USER_ACTIVITY = "user_activity"

    class AuditLogger:  # noqa: D401 - test stub
        async def log_compliance_event(self, *a, **k):
            return None

        async def collect_evidence(self, *a, **k):
            return None

    audit_stub.AuditEventType = AuditEventType
    audit_stub.EvidenceType = EvidenceType
    audit_stub.AuditLogger = AuditLogger

    # Minimal package objects without running their real __init__.py.
    if "app.compliance" not in sys.modules:
        pkg = types.ModuleType("app.compliance")
        pkg.__path__ = [str(API_ROOT / "app" / "compliance")]
        sys.modules["app.compliance"] = pkg
    sys.modules["app.compliance.audit"] = audit_stub

    privpkg = types.ModuleType("app.compliance.privacy")
    privpkg.__path__ = [str(API_ROOT / "app" / "compliance" / "privacy")]
    sys.modules["app.compliance.privacy"] = privpkg

    spec = importlib.util.spec_from_file_location(
        "app.compliance.privacy.data_subject_handler", str(HANDLER_PATH)
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["app.compliance.privacy.data_subject_handler"] = module
    spec.loader.exec_module(module)
    return module


handler_mod = _load_handler_module()
DataSubjectRequestHandler = handler_mod.DataSubjectRequestHandler
DataExportFormat = handler_mod.DataExportFormat


@pytest_asyncio.fixture
async def engine_and_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    # The serializer queries every identity table (users, memberships, orgs,
    # sessions, passkeys, oauth accounts, oauth grants, audit logs), so create
    # the full metadata set for this in-memory DB.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield engine, factory
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_user_id(engine_and_factory, monkeypatch, tmp_path):
    engine, factory = engine_and_factory

    # Point the handler's get_session at our in-memory factory, and its export
    # directory at a temp dir so artifacts are written somewhere disposable.
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _session_cm():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    monkeypatch.setattr(handler_mod, "get_session", _session_cm)
    monkeypatch.setattr(handler_mod, "_EXPORT_DIR", str(tmp_path / "exports"))

    user = User(
        id=uuid.uuid4(),
        email="handler.subject@example.test",
        first_name="Edsger",
        password_hash=FAKE_PASSWORD_HASH,
        mfa_enabled=True,
        mfa_secret=FAKE_MFA_SECRET,
        created_at=datetime.utcnow(),
    )
    async with factory() as session:
        session.add(user)
        session.add(
            Session(
                id=uuid.uuid4(),
                user_id=user.id,
                token=FAKE_SESSION_TOKEN,
                expires_at=datetime.utcnow() + timedelta(days=1),
            )
        )
        session.add(
            Passkey(
                id=uuid.uuid4(),
                user_id=user.id,
                credential_id="cred-handler-1",
                public_key=FAKE_PASSKEY_PUBKEY,
                name="Handler Passkey",
            )
        )
        session.add(
            AuditLog(
                id=uuid.uuid4(),
                user_id=user.id,
                action="user.login",
                created_at=datetime.utcnow(),
            )
        )
        await session.commit()
    return str(user.id)


def _handler():
    return DataSubjectRequestHandler(audit_logger=handler_mod.AuditLogger())


class TestCollectUserData:
    async def test_collects_real_user_data(self, seeded_user_id):
        data = await _handler()._collect_user_data(seeded_user_id)
        assert data["user"]["email"] == "handler.subject@example.test"
        assert data["security"]["mfa_enabled"] is True
        assert len(data["sessions"]) == 1
        assert len(data["audit_logs"]) == 1

    async def test_collect_user_data_no_secrets(self, seeded_user_id):
        data = await _handler()._collect_user_data(seeded_user_id)
        assert find_secret_fields(data) == []
        assert contains_secret_values(data, ALL_SECRETS) is None

    async def test_collect_portable_data_subset_no_secrets(self, seeded_user_id):
        data = await _handler()._collect_portable_data(seeded_user_id)
        # Article 20 subset omits sessions/audit logs.
        assert "sessions" not in data
        assert "audit_logs" not in data
        assert find_secret_fields(data) == []
        assert contains_secret_values(data, ALL_SECRETS) is None


class TestGenerateExportArtifact:
    async def test_generates_real_json_file(self, seeded_user_id):
        handler = _handler()
        data = await handler._collect_user_data(seeded_user_id)
        path = await handler._generate_data_export("DSR-HANDLER-0001", data, DataExportFormat.JSON)
        # Real file on disk, not a fake "/secure/exports/..." string.
        assert os.path.exists(path)
        assert path.endswith(".json")
        with open(path, encoding="utf-8") as handle:
            content = handle.read()
        assert "handler.subject@example.test" in content
        for secret in ALL_SECRETS:
            assert secret not in content

    async def test_structured_export_writes_zip(self, seeded_user_id):
        handler = _handler()
        data = await handler._collect_portable_data(seeded_user_id)
        path = await handler._generate_data_export(
            "DSR-HANDLER-0002", data, DataExportFormat.JSON, structured_format=True
        )
        assert os.path.exists(path)
        assert path.endswith(".zip")

    async def test_erasure_backup_written_without_secrets(self, seeded_user_id):
        handler = _handler()
        data = await handler._collect_user_data(seeded_user_id)
        ref = await handler._create_erasure_backup("DSR-HANDLER-0003", data)
        assert ref.startswith("BACKUP-DSR-HANDLER-0003")
        backup_path = os.path.join(handler_mod._EXPORT_DIR, f"{ref}.json")
        assert os.path.exists(backup_path)
        with open(backup_path, encoding="utf-8") as handle:
            content = handle.read()
        for secret in ALL_SECRETS:
            assert secret not in content
