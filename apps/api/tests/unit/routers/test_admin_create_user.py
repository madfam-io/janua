"""Admin create-user endpoint (POST /api/v1/admin/users).

Janua previously had no admin path to provision a user directly — creation was
only via self-signup or invite acceptance. This adds Supabase-style
admin.createUser parity. These tests pin the security-critical behaviours:

  * happy path with a password  -> user created, usable, no token leaked
  * password omitted            -> set_password_token minted (PasswordReset),
                                    user has no usable password_hash
  * the response NEVER carries the password or its hash
  * non-admin caller            -> 403 (gate enforced)
  * duplicate email             -> 409
  * no-privilege-escalation     -> org role is disjoint from platform is_admin,
                                    and an unknown org role is rejected (422)
  * the creation is audit-logged via the tamper-evident AuditLog chain

Style follows tests/unit/routers/test_signup_locale.py: call the endpoint
coroutine directly with an AsyncMock session and intercept db.add(), rather than
standing up a live DB/TestClient.
"""

import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

import app.routers.v1.admin as admin_mod
from app.routers.v1.admin import AdminUserCreateRequest, create_user_admin
from app.models import OrganizationMember, PasswordReset, User

pytestmark = pytest.mark.asyncio


def _admin_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="admin@madfam.io",
        password_hash="hashed",
        is_admin=True,
    )


def _non_admin_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="mallory@example.com",
        password_hash="hashed",
        is_admin=False,
    )


def _db(existing_user=None, existing_org=None):
    """AsyncMock session.

    db.execute is called for: optional org lookup, the duplicate-email check, and
    (inside create_audit_log) the previous-hash lookup. We return a result whose
    scalar_one_or_none yields, in order: [org (if org lookup happens), existing
    user for the dup check, None for the audit previous-hash]. To keep ordering
    robust regardless of how many selects run, we route by the queried entity is
    impractical here; instead we hand back a small queue and default to None.
    """
    results = []
    # The endpoint issues at most: org-select, user-dup-select, audit-prev-select.
    # We only need the org-select and dup-select to return meaningful values.
    if existing_org is not None:
        results.append(existing_org)
    results.append(existing_user)  # duplicate check -> None means "no dup"

    call = {"i": 0}

    def _make_result():
        idx = call["i"]
        call["i"] += 1
        value = results[idx] if idx < len(results) else None
        r = MagicMock()
        r.scalar_one_or_none = MagicMock(return_value=value)
        return r

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=lambda *a, **k: _make_result())
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    async def refresh(obj, *args, **kwargs):
        for column, default in (
            ("id", uuid.uuid4()),
            ("created_at", datetime.utcnow()),
            ("updated_at", datetime.utcnow()),
        ):
            if getattr(obj, column, None) is None:
                setattr(obj, column, default)

    db.refresh = AsyncMock(side_effect=refresh)
    return db


def _added(db, cls):
    return [c.args[0] for c in db.add.call_args_list if c.args and isinstance(c.args[0], cls)]


async def _create(request: AdminUserCreateRequest, caller: User, db):
    return await create_user_admin(request=request, current_user=caller, db=db)


class TestHappyPathWithPassword:
    async def test_creates_active_user_and_never_returns_secret(self):
        db = _db()
        resp = await _create(
            AdminUserCreateRequest(
                email="new@example.com",
                name="New Person",
                password="Str0ng!Passw0rd",
                email_verified=True,
            ),
            _admin_user(),
            db,
        )

        # Exactly one User created, with a hashed (not plaintext) password.
        users = _added(db, User)
        assert len(users) == 1
        created = users[0]
        assert created.email == "new@example.com"
        assert created.password_hash is not None
        assert created.password_hash != "Str0ng!Passw0rd"
        assert created.email_verified is True

        # Response carries no password/hash and no set-password token.
        assert resp.email == "new@example.com"
        assert resp.is_admin is False
        assert resp.set_password_token is None
        dumped = resp.model_dump()
        assert "password" not in dumped
        assert "password_hash" not in dumped
        assert "Str0ng!Passw0rd" not in str(dumped)
        assert created.password_hash not in str(dumped)

    async def test_weak_password_rejected(self):
        db = _db()
        with pytest.raises(HTTPException) as exc:
            await _create(
                AdminUserCreateRequest(email="new@example.com", password="weak"),
                _admin_user(),
                db,
            )
        assert exc.value.status_code == 400
        assert _added(db, User) == []  # nothing created on rejection


class TestPasswordOmittedTokenPath:
    async def test_mints_set_password_token_and_leaves_no_usable_password(self):
        db = _db()
        resp = await _create(
            AdminUserCreateRequest(email="invitee@example.com", name="Invitee"),
            _admin_user(),
            db,
        )

        # No usable password on the created user.
        created = _added(db, User)[0]
        assert created.password_hash is None

        # A PasswordReset token row was created, and the SAME token is returned.
        resets = _added(db, PasswordReset)
        assert len(resets) == 1
        assert resp.set_password_token is not None
        assert resp.set_password_token == resets[0].token
        # Token is high-entropy, not a guessable default.
        assert len(resp.set_password_token) >= 32
        assert resp.set_password_token.lower() not in {"changeme", "password", "invitee"}


class TestPrivilegeModel:
    async def test_non_admin_caller_forbidden(self):
        db = _db()
        with pytest.raises(HTTPException) as exc:
            await _create(
                AdminUserCreateRequest(email="new@example.com", password="Str0ng!Passw0rd"),
                _non_admin_user(),
                db,
            )
        assert exc.value.status_code == 403
        # Gate runs before any writes.
        assert db.add.call_args_list == []

    async def test_org_role_is_disjoint_from_platform_admin(self):
        """Granting an org-scoped role must not touch the platform is_admin flag."""
        org = SimpleNamespace(id=uuid.uuid4())
        db = _db(existing_org=org)
        resp = await _create(
            AdminUserCreateRequest(
                email="member@example.com",
                password="Str0ng!Passw0rd",
                is_admin=False,
                organization_id=str(org.id),
                organization_role="admin",  # org admin, NOT platform admin
            ),
            _admin_user(),
            db,
        )

        created = _added(db, User)[0]
        assert created.is_admin is False  # org role did not escalate platform admin
        assert resp.is_admin is False

        members = _added(db, OrganizationMember)
        assert len(members) == 1
        assert members[0].role == "admin"
        assert members[0].organization_id == org.id
        assert resp.organization_role == "admin"

    async def test_unknown_org_role_rejected(self):
        db = _db()
        with pytest.raises(HTTPException) as exc:
            await _create(
                AdminUserCreateRequest(
                    email="new@example.com",
                    password="Str0ng!Passw0rd",
                    organization_role="superadmin",  # not in the allowlist
                ),
                _admin_user(),
                db,
            )
        assert exc.value.status_code == 422
        assert _added(db, User) == []


class TestDuplicateGuard:
    async def test_duplicate_email_conflicts(self):
        existing = User(id=uuid.uuid4(), email="dupe@example.com", password_hash="x")
        db = _db(existing_user=existing)
        with pytest.raises(HTTPException) as exc:
            await _create(
                AdminUserCreateRequest(email="dupe@example.com", password="Str0ng!Passw0rd"),
                _admin_user(),
                db,
            )
        assert exc.value.status_code == 409


class TestAuditLogged:
    async def test_creation_is_audit_logged(self):
        db = _db()
        caller = _admin_user()
        log_mock = AsyncMock(return_value="event-id")
        # Patch AuditLogger so its constructor returns an object whose .log is our
        # AsyncMock — the endpoint does `AuditLogger(db).log(...)`.
        fake_logger = MagicMock()
        fake_logger.log = log_mock
        with patch.object(admin_mod, "AuditLogger", return_value=fake_logger):
            await _create(
                AdminUserCreateRequest(email="new@example.com", password="Str0ng!Passw0rd"),
                caller,
                db,
            )

        log_mock.assert_awaited_once()
        kwargs = log_mock.await_args.kwargs
        assert kwargs["event_type"] == admin_mod.AuditEventType.USER_CREATE
        assert kwargs["resource_type"] == "user"
        assert kwargs["details"]["email"] == "new@example.com"
        assert kwargs["details"]["created_by"] == str(caller.id)
        assert kwargs["details"]["via"] == "admin.create_user"
        # No secret ever reaches the audit trail.
        assert "password" not in kwargs["details"]
        assert "Str0ng!Passw0rd" not in str(kwargs["details"])

    async def test_audit_failure_does_not_block_creation(self):
        """An audit-logging error must not prevent the user from being created."""
        db = _db()
        fake_logger = MagicMock()
        fake_logger.log = AsyncMock(side_effect=RuntimeError("audit sink down"))
        with patch.object(admin_mod, "AuditLogger", return_value=fake_logger):
            resp = await _create(
                AdminUserCreateRequest(email="resilient@example.com", password="Str0ng!Passw0rd"),
                _admin_user(),
                db,
            )
        assert resp.email == "resilient@example.com"
        assert len(_added(db, User)) == 1
        db.commit.assert_awaited()
