"""Admin entitlement write-API (POST/DELETE /api/v1/admin/entitlements/{user,org}).

Phase 0 (Nauta ERP entitlement substrate, G1). Today the only writer of
entitlements is the Dhanam webhook; this adds an AUDITED, platform-admin-only
surface to grant/revoke entitlements for a USER (user_entitlements rows) and an
ORG (product_tiers JSONB). These tests pin the security-critical behaviours:

  * an admin can grant/revoke a user entitlement -> upsert/cancel is called
  * an admin can grant/revoke an org entitlement -> product_tiers merged/removed
  * org grant MERGES (does not clobber other products)
  * a non-admin caller -> 403 (gate enforced before any write)
  * unknown user_id / org_id -> 404
  * every grant/revoke writes an AuditLog row (via the tamper-evident chain)
  * an audit-logging failure does NOT block the mutation

Style follows tests/unit/routers/test_admin_create_user.py: call the endpoint
coroutine directly with an AsyncMock session, rather than a live DB/TestClient.
"""

import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

import app.routers.v1.admin as admin_mod
from app.models import EntitlementSource, User
from app.routers.v1.admin import (
    AdminOrgEntitlementGrantRequest,
    AdminOrgEntitlementRevokeRequest,
    AdminUserEntitlementGrantRequest,
    AdminUserEntitlementRevokeRequest,
    grant_org_entitlement,
    grant_user_entitlement,
    revoke_org_entitlement,
    revoke_user_entitlement,
)

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


def _db(scalar_results):
    """AsyncMock session that returns a queue of scalar_one_or_none values.

    `scalar_results` is a list consumed in order by successive db.execute()
    calls (the endpoint does a lookup for the target user/org, and the service
    methods issue their own lookups). Defaults to None once exhausted.
    """
    results = list(scalar_results)
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
    return db


def _fake_audit():
    """Patch AuditLogger so the endpoint's AuditLogger(db).log(...) is captured."""
    log_mock = AsyncMock(return_value="event-id")
    fake_logger = MagicMock()
    fake_logger.log = log_mock
    return fake_logger, log_mock


class TestGrantUserEntitlement:
    async def test_admin_grants_user_entitlement_and_audits(self):
        target = SimpleNamespace(id=uuid.uuid4(), tenant_id=uuid.uuid4())
        # execute() #1: target-user lookup; #2 (inside upsert): existing row (None).
        db = _db([target, None])
        fake_logger, log_mock = _fake_audit()

        with patch.object(admin_mod, "AuditLogger", return_value=fake_logger):
            resp = await grant_user_entitlement(
                AdminUserEntitlementGrantRequest(
                    user_id=str(target.id), product="kalya", tier="pro"
                ),
                current_user=_admin_user(),
                db=db,
            )

        # A user_entitlements row was created via the service upsert.
        from app.models import UserEntitlement

        added = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], UserEntitlement)]
        assert len(added) == 1
        assert added[0].product == "kalya"
        assert added[0].tier == "pro"
        assert added[0].source == EntitlementSource.ADMIN_GRANT

        # Response echoes the row.
        assert resp.product == "kalya"
        assert resp.tier == "pro"
        assert resp.source == EntitlementSource.ADMIN_GRANT.value

        # Audited as a grant.
        log_mock.assert_awaited_once()
        kwargs = log_mock.await_args.kwargs
        assert kwargs["event_type"] == admin_mod.AuditEventType.ENTITLEMENT_GRANT
        assert kwargs["resource_type"] == "user_entitlement"
        assert kwargs["details"]["product"] == "kalya"
        assert kwargs["details"]["scope"] == "user"
        db.commit.assert_awaited()

    async def test_non_admin_forbidden(self):
        db = _db([])
        with pytest.raises(HTTPException) as exc:
            await grant_user_entitlement(
                AdminUserEntitlementGrantRequest(
                    user_id=str(uuid.uuid4()), product="kalya", tier="pro"
                ),
                current_user=_non_admin_user(),
                db=db,
            )
        assert exc.value.status_code == 403
        assert db.execute.await_count == 0  # gate before any write

    async def test_unknown_user_404(self):
        db = _db([None])  # target-user lookup returns None
        with pytest.raises(HTTPException) as exc:
            await grant_user_entitlement(
                AdminUserEntitlementGrantRequest(
                    user_id=str(uuid.uuid4()), product="kalya", tier="pro"
                ),
                current_user=_admin_user(),
                db=db,
            )
        assert exc.value.status_code == 404

    async def test_invalid_user_id_400(self):
        db = _db([])
        with pytest.raises(HTTPException) as exc:
            await grant_user_entitlement(
                AdminUserEntitlementGrantRequest(user_id="not-a-uuid", product="kalya", tier="pro"),
                current_user=_admin_user(),
                db=db,
            )
        assert exc.value.status_code == 400

    async def test_audit_failure_does_not_block(self):
        target = SimpleNamespace(id=uuid.uuid4(), tenant_id=uuid.uuid4())
        db = _db([target, None])
        fake_logger = MagicMock()
        fake_logger.log = AsyncMock(side_effect=RuntimeError("audit sink down"))
        with patch.object(admin_mod, "AuditLogger", return_value=fake_logger):
            resp = await grant_user_entitlement(
                AdminUserEntitlementGrantRequest(
                    user_id=str(target.id), product="kalya", tier="pro"
                ),
                current_user=_admin_user(),
                db=db,
            )
        assert resp.product == "kalya"
        db.commit.assert_awaited()


class TestRevokeUserEntitlement:
    async def test_admin_revokes_user_entitlement_and_audits(self):
        target = SimpleNamespace(id=uuid.uuid4(), tenant_id=uuid.uuid4())
        existing_row = MagicMock(
            user_id=target.id,
            product="kalya",
            tier="pro",
            source=EntitlementSource.ADMIN_GRANT,
            expires_at=None,
            granted_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        # execute() #1: target-user lookup; #2 (inside cancel): the existing row.
        db = _db([target, existing_row])
        fake_logger, log_mock = _fake_audit()

        with patch.object(admin_mod, "AuditLogger", return_value=fake_logger):
            resp = await revoke_user_entitlement(
                AdminUserEntitlementRevokeRequest(user_id=str(target.id), product="kalya"),
                current_user=_admin_user(),
                db=db,
            )

        # cancel set expires_at (row preserved, not deleted).
        assert existing_row.expires_at is not None
        assert resp.product == "kalya"

        log_mock.assert_awaited_once()
        kwargs = log_mock.await_args.kwargs
        assert kwargs["event_type"] == admin_mod.AuditEventType.ENTITLEMENT_REVOKE
        db.commit.assert_awaited()

    async def test_unknown_user_404(self):
        db = _db([None])
        with pytest.raises(HTTPException) as exc:
            await revoke_user_entitlement(
                AdminUserEntitlementRevokeRequest(user_id=str(uuid.uuid4()), product="kalya"),
                current_user=_admin_user(),
                db=db,
            )
        assert exc.value.status_code == 404

    async def test_missing_entitlement_404(self):
        target = SimpleNamespace(id=uuid.uuid4(), tenant_id=uuid.uuid4())
        # target found, but cancel finds no row -> None
        db = _db([target, None])
        with pytest.raises(HTTPException) as exc:
            await revoke_user_entitlement(
                AdminUserEntitlementRevokeRequest(user_id=str(target.id), product="kalya"),
                current_user=_admin_user(),
                db=db,
            )
        assert exc.value.status_code == 404

    async def test_non_admin_forbidden(self):
        db = _db([])
        with pytest.raises(HTTPException) as exc:
            await revoke_user_entitlement(
                AdminUserEntitlementRevokeRequest(user_id=str(uuid.uuid4()), product="kalya"),
                current_user=_non_admin_user(),
                db=db,
            )
        assert exc.value.status_code == 403


class TestGrantOrgEntitlement:
    async def test_admin_grants_org_entitlement_merges_and_audits(self):
        org = MagicMock(product_tiers={"dhanam": "essentials"})
        # execute() #1 (inside set_org_product_tier): org lookup.
        db = _db([org])
        fake_logger, log_mock = _fake_audit()

        with patch.object(admin_mod, "AuditLogger", return_value=fake_logger):
            resp = await grant_org_entitlement(
                AdminOrgEntitlementGrantRequest(
                    org_id=str(uuid.uuid4()), product="kalya", tier="pro"
                ),
                current_user=_admin_user(),
                db=db,
            )

        # Merge preserved the other product.
        assert resp.product_tiers == {"dhanam": "essentials", "kalya": "pro"}

        log_mock.assert_awaited_once()
        kwargs = log_mock.await_args.kwargs
        assert kwargs["event_type"] == admin_mod.AuditEventType.ENTITLEMENT_GRANT
        assert kwargs["resource_type"] == "org_entitlement"
        assert kwargs["details"]["scope"] == "org"
        db.commit.assert_awaited()

    async def test_unknown_org_404(self):
        db = _db([None])  # org lookup returns None
        with pytest.raises(HTTPException) as exc:
            await grant_org_entitlement(
                AdminOrgEntitlementGrantRequest(
                    org_id=str(uuid.uuid4()), product="kalya", tier="pro"
                ),
                current_user=_admin_user(),
                db=db,
            )
        assert exc.value.status_code == 404

    async def test_non_admin_forbidden(self):
        db = _db([])
        with pytest.raises(HTTPException) as exc:
            await grant_org_entitlement(
                AdminOrgEntitlementGrantRequest(
                    org_id=str(uuid.uuid4()), product="kalya", tier="pro"
                ),
                current_user=_non_admin_user(),
                db=db,
            )
        assert exc.value.status_code == 403
        assert db.execute.await_count == 0


class TestRevokeOrgEntitlement:
    async def test_admin_revokes_org_entitlement_and_audits(self):
        org = MagicMock(product_tiers={"dhanam": "pro", "kalya": "pro"})
        db = _db([org])
        fake_logger, log_mock = _fake_audit()

        with patch.object(admin_mod, "AuditLogger", return_value=fake_logger):
            resp = await revoke_org_entitlement(
                AdminOrgEntitlementRevokeRequest(org_id=str(uuid.uuid4()), product="kalya"),
                current_user=_admin_user(),
                db=db,
            )

        # kalya removed, dhanam preserved.
        assert resp.product_tiers == {"dhanam": "pro"}

        log_mock.assert_awaited_once()
        kwargs = log_mock.await_args.kwargs
        assert kwargs["event_type"] == admin_mod.AuditEventType.ENTITLEMENT_REVOKE
        db.commit.assert_awaited()

    async def test_unknown_org_404(self):
        db = _db([None])
        with pytest.raises(HTTPException) as exc:
            await revoke_org_entitlement(
                AdminOrgEntitlementRevokeRequest(org_id=str(uuid.uuid4()), product="kalya"),
                current_user=_admin_user(),
                db=db,
            )
        assert exc.value.status_code == 404

    async def test_non_admin_forbidden(self):
        db = _db([])
        with pytest.raises(HTTPException) as exc:
            await revoke_org_entitlement(
                AdminOrgEntitlementRevokeRequest(org_id=str(uuid.uuid4()), product="kalya"),
                current_user=_non_admin_user(),
                db=db,
            )
        assert exc.value.status_code == 403


class TestInputValidation:
    """product/tier are free-text but must be non-empty (Pydantic min_length=1)."""

    def test_empty_product_rejected(self):
        with pytest.raises(ValidationError):
            AdminUserEntitlementGrantRequest(user_id=str(uuid.uuid4()), product="", tier="pro")

    def test_empty_tier_rejected(self):
        with pytest.raises(ValidationError):
            AdminUserEntitlementGrantRequest(user_id=str(uuid.uuid4()), product="kalya", tier="")
