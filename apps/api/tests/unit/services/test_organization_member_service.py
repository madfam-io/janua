"""Regression tests for `OrganizationMemberService` construction of real models.

Why these exist
---------------
`add_member` passed `invited_by=` and `metadata=` to the `OrganizationMember`
constructor, and NEITHER is a column of that model (`models/__init__.py:180-192`
declares only id, organization_id, user_id, role, status, joined_at, created_at,
updated_at). A SQLAlchemy 2.0 declarative constructor raises
`TypeError: 'invited_by' is an invalid keyword argument for OrganizationMember`
on an unknown keyword, so the call could never have succeeded at runtime.

It survived because the only existing coverage (`tests/integration/
test_mvp_features.py::test_add_member_success`) mocks the whole session: with a
`MagicMock` db nothing ever touches the real mapper, so the defect was invisible
to a green suite. These tests therefore deliberately construct the REAL mapped
class rather than a mock — that is the whole point.

`metadata` additionally can never become a column under that name: `metadata` is
a reserved attribute on a declarative `Base`.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from app.models import OrganizationMember


def test_organization_member_rejects_invited_by_kwarg():
    """Pins the defect: this is what the old `add_member` body did."""
    with pytest.raises(TypeError, match="invited_by"):
        OrganizationMember(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            role="member",
            status="active",
            joined_at=datetime.utcnow(),
            invited_by=uuid4(),
        )


def test_organization_member_metadata_kwarg_is_silently_lost_not_stored():
    """The second head of the same defect, and the nastier one.

    `metadata` does NOT raise: it is a RESERVED declarative attribute (the
    `MetaData` registry on `Base`), so SQLAlchemy's constructor accepts the
    keyword and Python simply shadows the class attribute with a plain dict on
    the instance. Nothing is persisted — the column does not exist — and the
    instance's `metadata` no longer answers as the SQLAlchemy registry.

    So `add_member` was failing in two different ways at once: loud on
    `invited_by`, silent on `metadata`. Only the loud one is visible in a
    traceback, which is why the fix drops BOTH rather than just the one the
    exception named.
    """
    member = OrganizationMember(
        id=uuid4(),
        organization_id=uuid4(),
        user_id=uuid4(),
        role="member",
        status="active",
        joined_at=datetime.utcnow(),
        metadata={"invitation_id": str(uuid4())},
    )

    # Shadowed by a plain dict rather than rejected — silent, and never written.
    assert isinstance(member.metadata, dict)
    # The class attribute it shadowed is SQLAlchemy's registry, not a column.
    assert hasattr(OrganizationMember.metadata, "tables")
    assert "metadata" not in {c.key for c in OrganizationMember.__table__.columns}


def test_organization_member_constructs_with_only_its_real_columns():
    """The corrected shape — what `add_member` builds now."""
    org_id, user_id = uuid4(), uuid4()
    member = OrganizationMember(
        id=uuid4(),
        organization_id=org_id,
        user_id=user_id,
        role="member",
        status="active",
        joined_at=datetime.utcnow(),
    )

    assert member.organization_id == org_id
    assert member.user_id == user_id
    assert member.role == "member"
    assert member.status == "active"


@pytest.mark.asyncio
async def test_add_member_constructs_a_real_organization_member(mocker=None):
    """`add_member` must not raise TypeError when it builds the real model.

    The db is stubbed only enough to reach the constructor — the assertion is
    about the row the service builds, which is where the defect lived. The
    caller's `invited_by` / `metadata` arguments are still ACCEPTED (the router
    at `organization_members.py:143-149` passes both); they are simply not
    forwarded to a model that has nowhere to put them.
    """
    from unittest.mock import AsyncMock, MagicMock

    from app.services.organization_member_service import OrganizationMemberService

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None  # not a member yet

    added: list = []
    db.add.side_effect = added.append

    redis = AsyncMock()
    service = OrganizationMemberService(db, redis)

    org_id, user_id, invited_by = uuid4(), uuid4(), uuid4()
    member = await service.add_member(
        organization_id=org_id,
        user_id=user_id,
        role="member",
        invited_by=invited_by,
        metadata={"source": "test"},
    )

    assert isinstance(member, OrganizationMember)
    assert added == [member]
    assert member.organization_id == org_id
    assert member.user_id == user_id
    assert member.role == "member"
    assert member.status == "active"
    # Not columns — must not have been smuggled onto the instance either, since
    # a silently-set attribute is never persisted and reads as data that exists.
    assert "invited_by" not in member.__dict__
    assert not isinstance(member.__dict__.get("metadata"), dict)
