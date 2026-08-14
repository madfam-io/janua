"""The `policies` table was missing every column the policy API works with.

`app/routers/v1/policies.py` and `app/services/policy_engine.py` read and wrote
`effect`, `priority`, `enabled`, `version`, `target_type`, `target_id`,
`resource_type`, `resource_pattern`, `actions`, `conditions` and `expires_at`,
and filtered on `Policy.tenant_id`. None of the eleven columns existed and
`policies.tenant_id` never has — alembic 000_init created the table with only
(id, name, description, rules, organization_id, created_at, updated_at) and the
SQLAlchemy model matched it exactly. Model and migration agreed; the *callers*
were the drift. Every create/list/get/update/delete raised before reaching the
database, which is why the production table held 0 rows.

The existing engine suite passed throughout, because it drives the engine with
`MagicMock` requests and policies — a MagicMock answers to any attribute name,
so it cannot tell a real column from a missing one. These tests use real model
instances and a real session for exactly that reason.

Style follows `test_policies_route_order.py` (janua#525): assert against
executable source with docstrings stripped, so prose cannot satisfy a scan.
"""

import ast
import inspect
import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models import Base, Organization, OrganizationMember, Policy, User
from app.models.policy import (
    PolicyCreate,
    PolicyEffect,
    PolicyEvaluateRequest,
    PolicyResponse,
    PolicyTargetType,
)
from app.routers.v1 import policies as policies_router
from app.services import policy_engine as policy_engine_module
from app.services.audit_logger import AuditAction

pytestmark = pytest.mark.asyncio

# Tables this module touches. Creating only these keeps the fixture independent
# of unrelated models that fail to map under SQLite.
_TABLES = [
    "users",
    "organizations",
    "organization_members",
    "policies",
    "roles",
    "user_roles",
    "role_policies",
    "policy_evaluations",
]

# Every field PolicyCreate accepts that lands on a policy row, with a value
# distinguishable from the column default so a dropped write is visible.
ROUND_TRIP_FIELDS = {
    "name": "round-trip-policy",
    "description": "every field this API claims to support",
    "rules": {"allow": {"action": "read"}},
    "effect": PolicyEffect.DENY,
    "priority": 42,
    "enabled": False,
    "target_type": PolicyTargetType.ROLE,
    "target_id": "target-abc",
    "resource_type": "documents",
    "resource_pattern": "documents:*",
    "actions": ["read", "write"],
    "conditions": {"mfa_required": True},
    "expires_at": datetime(2030, 1, 1, 12, 30),
}


@pytest.fixture(autouse=True)
def stub_io():
    """Stub the two collaborators that do network I/O.

    Both are instantiated inside the handlers, and both are awaited, so the
    default `MagicMock` return value is not awaitable.
    """
    audit_cls = MagicMock()
    audit_cls.return_value.log = AsyncMock()

    cache_cls = MagicMock()
    cache_cls.return_value.get = AsyncMock(return_value=None)
    for method in ("set", "delete", "delete_pattern"):
        setattr(cache_cls.return_value, method, AsyncMock())

    with (
        patch.object(policies_router, "AuditLogger", audit_cls),
        patch.object(policies_router, "CacheService", cache_cls),
        patch.object(policy_engine_module, "AuditLogger", audit_cls),
        patch.object(policy_engine_module, "CacheService", cache_cls),
    ):
        yield


@pytest_asyncio.fixture
async def db():
    """An isolated in-memory database per test.

    Deliberately not the session-scoped `real_db_session` fixture: these tests
    assert on row visibility, so they must not see another test's rows.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    tables = [Base.metadata.tables[name] for name in _TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=tables)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def _make_org_with_admin(db, name):
    """Create an organization plus an admin who is a member of it."""
    org = Organization(id=uuid.uuid4(), name=name, slug=name)
    user = User(id=uuid.uuid4(), email=f"admin@{name}.test", is_admin=True)
    db.add_all([org, user])
    await db.flush()
    db.add(OrganizationMember(id=uuid.uuid4(), organization_id=org.id, user_id=user.id))
    await db.commit()
    # The routers receive the authenticated principal, not an ORM instance.
    return org, SimpleNamespace(id=user.id, tenant_id=None)


def _executable_source(obj) -> str:
    """Source of `obj` with docstrings stripped, so prose can't satisfy a scan."""
    tree = ast.parse(inspect.getsource(obj))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            if ast.get_docstring(node):
                node.body = node.body[1:]
    return ast.unparse(tree)


def _attributes_accessed_on(module, name: str) -> set:
    """Every `name.<attr>` referenced in `module`'s executable source."""
    tree = ast.parse(_executable_source(module))
    return {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == name
    }


# ---------------------------------------------------------------------------
# The model is the one the router and engine actually use
# ---------------------------------------------------------------------------


def test_router_and_engine_share_one_policy_class():
    """`app.models.policy.Policy` is a re-export, not a second model.

    `app/models/policy.py` does `from . import Policy as PolicyModel`, so the
    router's import and the model defined in `app/models/__init__.py` are the
    same class. Any conclusion drawn from reading one of them applies to both.
    """
    from app.models import Policy as PolicyFromPackage
    from app.models.policy import Policy as PolicyFromModule

    assert PolicyFromModule is PolicyFromPackage
    assert policies_router.Policy is PolicyFromPackage
    assert policy_engine_module.Policy is PolicyFromPackage
    assert PolicyFromPackage.__table__.name == "policies"


def test_policies_are_scoped_by_a_column_that_exists():
    """The `Policy.tenant_id` half of the drift, mirroring #525's Role check."""
    assert hasattr(Policy, "organization_id")
    assert "tenant_id" not in Policy.__table__.columns, (
        "policies has no tenant_id column; organization_id is the tenancy key, "
        "consistent with Role and OrganizationMember."
    )

    for module in (policies_router, policy_engine_module):
        assert "Policy.tenant_id" not in _executable_source(
            module
        ), f"{module.__name__} filters on Policy.tenant_id, which does not exist."


def test_every_policy_attribute_the_code_touches_is_a_real_column():
    """The structural guard: no caller may reference a column that isn't there.

    This is what a mock-driven suite cannot check, and what let eleven missing
    columns survive review.
    """
    columns = set(Policy.__table__.columns.keys())
    referenced = set()
    for module in (policies_router, policy_engine_module):
        referenced |= _attributes_accessed_on(module, "Policy")
        referenced |= _attributes_accessed_on(module, "policy")

    # `rego_code` is read only by PolicyEngine.compile_to_wasm, which nothing
    # calls and which now returns None when the attribute is absent. It is
    # deliberately not a column.
    referenced -= {"rego_code"}

    missing = sorted(referenced - columns)
    assert not missing, f"Referenced on Policy but not columns: {missing}"


def test_audit_actions_the_handlers_emit_exist():
    """Each handler's audit call used a member that was never defined."""
    for member in (
        "POLICY_CREATE",
        "POLICY_UPDATE",
        "POLICY_DELETE",
        "POLICY_EVALUATE",
        "ROLE_CREATE",
        "ROLE_ASSIGN",
        "ROLE_UNASSIGN",
    ):
        assert hasattr(AuditAction, member), f"AuditAction.{member} is missing"


# ---------------------------------------------------------------------------
# Round trip
# ---------------------------------------------------------------------------


async def test_policy_round_trips_every_field_it_claims_to_support(db):
    """Write every supported field, read it back from the database, compare."""
    org, admin = await _make_org_with_admin(db, "roundtrip")

    created = await policies_router.create_policy(
        PolicyCreate(organization_id=str(org.id), **ROUND_TRIP_FIELDS),
        current_user=admin,
        db=db,
    )

    db.expunge_all()
    stored = await db.get(Policy, uuid.UUID(created.id))

    assert stored is not None, "create_policy did not persist a row"
    assert str(stored.organization_id) == str(org.id)
    assert stored.version == 1

    expected = dict(ROUND_TRIP_FIELDS)
    expected["effect"] = PolicyEffect.DENY.value
    expected["target_type"] = PolicyTargetType.ROLE.value

    for field, value in expected.items():
        assert getattr(stored, field) == value, f"{field} did not survive the round trip"


async def test_policy_response_exposes_every_field_it_declares(db):
    """`PolicyResponse.from_orm` used to read attributes that did not exist."""
    org, admin = await _make_org_with_admin(db, "response")

    created = await policies_router.create_policy(
        PolicyCreate(organization_id=str(org.id), **ROUND_TRIP_FIELDS),
        current_user=admin,
        db=db,
    )

    stored = await db.get(Policy, uuid.UUID(created.id))
    response = PolicyResponse.from_orm(stored)

    assert response.effect == PolicyEffect.DENY.value
    assert response.priority == 42
    assert response.enabled is False
    assert response.version == 1
    assert response.target_type == PolicyTargetType.ROLE.value
    assert response.target_id == "target-abc"
    assert response.resource_pattern == "documents:*"
    assert response.actions == ["read", "write"]
    assert response.conditions == {"mfa_required": True}
    assert response.expires_at == ROUND_TRIP_FIELDS["expires_at"]
    assert response.organization_id == str(org.id)
    # tenant_id is kept as an alias of organization_id, as RoleResponse does.
    assert response.tenant_id == str(org.id)


async def test_update_policy_increments_version_and_persists(db):
    org, admin = await _make_org_with_admin(db, "update")

    created = await policies_router.create_policy(
        PolicyCreate(organization_id=str(org.id), name="v1"),
        current_user=admin,
        db=db,
    )

    from app.models.policy import PolicyUpdate

    updated = await policies_router.update_policy(
        created.id,
        PolicyUpdate(name="v2", effect=PolicyEffect.DENY, priority=7),
        current_user=admin,
        db=db,
    )

    assert updated.version == 2
    assert updated.name == "v2"
    # The enum must be unwrapped to its string value, not stored as PolicyEffect.
    assert updated.effect == "deny"

    db.expunge_all()
    stored = await db.get(Policy, uuid.UUID(created.id))
    assert stored.effect == "deny"
    assert stored.priority == 7


async def test_delete_policy_actually_removes_the_row(db):
    """`AsyncSession.delete` is a coroutine; the un-awaited call left the row."""
    org, admin = await _make_org_with_admin(db, "delete")

    created = await policies_router.create_policy(
        PolicyCreate(organization_id=str(org.id), name="doomed"),
        current_user=admin,
        db=db,
    )

    await policies_router.delete_policy(created.id, current_user=admin, db=db)

    db.expunge_all()
    assert await db.get(Policy, uuid.UUID(created.id)) is None


# ---------------------------------------------------------------------------
# Organization scoping
# ---------------------------------------------------------------------------


async def test_org_a_policy_is_invisible_to_org_b(db):
    """Cross-tenant isolation: list, get, update and delete must all miss."""
    from fastapi import HTTPException

    org_a, admin_a = await _make_org_with_admin(db, "orga")
    org_b, admin_b = await _make_org_with_admin(db, "orgb")

    secret = await policies_router.create_policy(
        PolicyCreate(organization_id=str(org_a.id), name="org-a-secret"),
        current_user=admin_a,
        db=db,
    )

    # skip/limit are passed explicitly: calling the handler directly bypasses
    # FastAPI's dependency resolution, so their defaults are `Query` objects.
    a_listed = await policies_router.list_policies(skip=0, limit=100, current_user=admin_a, db=db)
    b_listed = await policies_router.list_policies(skip=0, limit=100, current_user=admin_b, db=db)

    assert [p.id for p in a_listed] == [secret.id]
    assert b_listed == [], "org B can list org A's policies"

    with pytest.raises(HTTPException) as exc:
        await policies_router.get_policy(secret.id, current_user=admin_b, db=db)
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException):
        await policies_router.delete_policy(secret.id, current_user=admin_b, db=db)

    db.expunge_all()
    assert await db.get(Policy, uuid.UUID(secret.id)) is not None


async def test_create_policy_rejects_a_foreign_organization(db):
    """An admin must not be able to plant a policy in someone else's org."""
    from fastapi import HTTPException

    org_a, admin_a = await _make_org_with_admin(db, "planter")
    org_b, _ = await _make_org_with_admin(db, "victim")

    with pytest.raises(HTTPException) as exc:
        await policies_router.create_policy(
            PolicyCreate(organization_id=str(org_b.id), name="planted"),
            current_user=admin_a,
            db=db,
        )

    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def _engine(db):
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    return policy_engine_module.PolicyEngine(db=db, cache=cache)


async def test_evaluate_does_not_raise_with_no_policies(db):
    """The engine issued `self.db.query(...)` against an AsyncSession, which has
    no `.query`, and read `request.subject`, which the schema did not define."""
    org, _ = await _make_org_with_admin(db, "evalempty")
    engine = _engine(db)

    response = await engine.evaluate(
        request=PolicyEvaluateRequest(resource_type="documents", action="read"),
        organization_id=str(org.id),
    )

    assert response.allowed is False
    assert response.matched_policies == []
    assert response.reason


async def test_evaluate_allows_on_a_matching_allow_policy(db):
    org, admin = await _make_org_with_admin(db, "evalallow")

    db.add(
        Policy(
            id=uuid.uuid4(),
            organization_id=org.id,
            name="allow-doc-read",
            effect="allow",
            priority=10,
            enabled=True,
            version=1,
            target_type="organization",
            actions=["read"],
            rules={},
            conditions={},
        )
    )
    await db.commit()

    engine = _engine(db)
    response = await engine.evaluate(
        request=PolicyEvaluateRequest(
            subject_id=str(admin.id), resource_type="documents", action="read"
        ),
        organization_id=str(org.id),
    )

    assert response.allowed is True
    assert len(response.matched_policies) == 1
    assert response.metadata["evaluation_time_ms"] >= 0


async def test_evaluate_deny_beats_allow_regardless_of_order(db):
    """Explicit deny wins; priority orders evaluation, deny short-circuits."""
    org, admin = await _make_org_with_admin(db, "evaldeny")

    common = {
        "organization_id": org.id,
        "enabled": True,
        "version": 1,
        "target_type": "organization",
        "actions": ["read"],
        "rules": {},
        "conditions": {},
    }
    db.add(Policy(id=uuid.uuid4(), name="allow-all", effect="allow", priority=1, **common))
    db.add(Policy(id=uuid.uuid4(), name="deny-docs", effect="deny", priority=99, **common))
    await db.commit()

    engine = _engine(db)
    response = await engine.evaluate(
        request=PolicyEvaluateRequest(
            subject_id=str(admin.id), resource_type="documents", action="read"
        ),
        organization_id=str(org.id),
    )

    assert response.allowed is False
    assert response.denied_by is not None


async def test_evaluate_ignores_disabled_and_expired_policies(db):
    org, admin = await _make_org_with_admin(db, "evalskip")

    common = {
        "organization_id": org.id,
        "effect": "allow",
        "priority": 5,
        "version": 1,
        "target_type": "organization",
        "actions": ["read"],
        "rules": {},
        "conditions": {},
    }
    db.add(Policy(id=uuid.uuid4(), name="disabled", enabled=False, **common))
    db.add(
        Policy(
            id=uuid.uuid4(),
            name="expired",
            enabled=True,
            expires_at=datetime.utcnow() - timedelta(days=1),
            **common,
        )
    )
    await db.commit()

    engine = _engine(db)
    response = await engine.evaluate(
        request=PolicyEvaluateRequest(
            subject_id=str(admin.id), resource_type="documents", action="read"
        ),
        organization_id=str(org.id),
    )

    assert response.allowed is False
    assert response.matched_policies == []


async def test_evaluate_does_not_see_another_organizations_policy(db):
    """Org scoping on the evaluation path, not just on CRUD."""
    org_a, _ = await _make_org_with_admin(db, "evala")
    org_b, admin_b = await _make_org_with_admin(db, "evalb")

    db.add(
        Policy(
            id=uuid.uuid4(),
            organization_id=org_a.id,
            name="org-a-allow",
            effect="allow",
            priority=10,
            enabled=True,
            version=1,
            target_type="organization",
            actions=["read"],
            rules={},
            conditions={},
        )
    )
    await db.commit()

    engine = _engine(db)
    response = await engine.evaluate(
        request=PolicyEvaluateRequest(
            subject_id=str(admin_b.id), resource_type="documents", action="read"
        ),
        organization_id=str(org_b.id),
    )

    assert response.allowed is False, "org B was allowed by org A's policy"
    assert response.matched_policies == []


async def test_evaluate_endpoint_returns_a_response(db):
    """End to end through the router handler, including the context it builds.

    `current_user.organization_id` was read here and `User` has no such column.
    """
    org, admin = await _make_org_with_admin(db, "evalroute")

    response = await policies_router.evaluate_policies(
        PolicyEvaluateRequest(resource_type="documents", action="read"),
        current_user=admin,
        db=db,
    )

    assert response.allowed is False
    assert response.reason


async def test_evaluate_request_derives_flat_subject_and_resource():
    """The adapter between the wire schema and the engine's matching vocabulary."""
    request = PolicyEvaluateRequest(
        subject_id="user-1", resource_type="documents", resource_id="42", action="read"
    )
    assert request.subject == "user-1"
    assert request.resource == "documents:42"

    type_only = PolicyEvaluateRequest(resource_type="documents", action="read")
    assert type_only.subject == ""
    assert type_only.resource == "documents"
