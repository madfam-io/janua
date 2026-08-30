"""Unit tests for the tenant-aware user lookup helper — `get_user_by_email`.

Since migration 013 email is unique PER TENANT, so a lookup must declare its
pool. These tests assert the statement is scoped correctly for each pool and that
`scalar_one_or_none` is what runs (safe again, because a pool-scoped lookup is
single-row).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.services.user_lookup import get_user_by_email


def _db_capture():
    """AsyncMock db that records the statement passed to execute() and returns a
    result whose scalar_one_or_none yields a sentinel user."""
    sentinel = SimpleNamespace(id=uuid4())
    result = MagicMock()
    result.scalar_one_or_none.return_value = sentinel
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)
    return db, result, sentinel


def _compiled(stmt) -> str:
    # Render the WHERE clause with literal binds so we can assert on the SQL text
    # without a live dialect-specific engine.
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


class TestGetUserByEmail:
    async def test_returns_the_single_row(self):
        db, result, sentinel = _db_capture()
        got = await get_user_by_email(db, "a@example.com", tenant_id=None)
        assert got is sentinel
        # It resolves via scalar_one_or_none (single-row safe), not first().
        result.scalar_one_or_none.assert_called_once()

    async def test_untenanted_pool_scopes_tenant_id_is_null(self):
        db, *_ = _db_capture()
        await get_user_by_email(db, "a@example.com", tenant_id=None)
        sql = _compiled(db.execute.call_args.args[0])
        assert "tenant_id IS NULL" in sql
        assert "a@example.com" in sql

    async def test_tenanted_pool_scopes_to_that_tenant(self):
        db, *_ = _db_capture()
        org = uuid4()
        await get_user_by_email(db, "a@example.com", tenant_id=org)
        sql = _compiled(db.execute.call_args.args[0])
        assert str(org) in sql
        # Must NOT collapse to the untenanted pool.
        assert "tenant_id IS NULL" not in sql

    @staticmethod
    def _where(stmt) -> str:
        # Just the WHERE clause text (status appears in the SELECT column list
        # regardless, so assert on the predicate, not the whole statement).
        # SQLAlchemy renders "WHERE" after a newline, so match the bare keyword.
        sql = _compiled(stmt)
        idx = sql.upper().find("WHERE")
        return sql[idx:] if idx != -1 else ""

    async def test_active_only_adds_status_predicate(self):
        db, *_ = _db_capture()
        await get_user_by_email(db, "a@example.com", tenant_id=None, active_only=True)
        where = self._where(db.execute.call_args.args[0]).lower()
        # ACTIVE is the enum value; its DB representation appears in the predicate.
        assert "status" in where

    async def test_active_only_default_is_false(self):
        db, *_ = _db_capture()
        await get_user_by_email(db, "a@example.com", tenant_id=None)
        where = self._where(db.execute.call_args.args[0]).lower()
        # No status predicate in the WHERE clause when active_only is not set.
        assert "status" not in where
