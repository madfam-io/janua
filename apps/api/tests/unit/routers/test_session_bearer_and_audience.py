"""The issuer accepts what it minted, and /session answers bearers.

Two halves of the same 2026-08-15 rehearsal finding:

1. `/session` read ONLY the cookie, so every server-to-server bearer call
   401'd instantly — nauta's invitation redemption among them.
2. `verify_token` pinned the platform audience, so the moment magic-link
   sessions started carrying per-client audiences (#545), janua would have
   rejected its own tokens on its own session checks.
"""

import inspect

import pytest

from app.routers.v1 import auth
from app.services.auth_service import AuthService


def test_session_endpoint_reads_bearer_when_no_cookie():
    source = inspect.getsource(auth.check_session)
    assert 'request.cookies.get("access_token")' in source
    assert "authorization" in source.lower()
    assert "bearer " in source.lower()


@pytest.mark.asyncio
async def test_verify_token_accepts_a_per_client_audience():
    token, _jti, _exp = AuthService.create_access_token(
        user_id="00000000-0000-0000-0000-000000000001",
        tenant_id="00000000-0000-0000-0000-000000000002",
        email="a@b.test",
        audience="nauta-portal",
    )
    payload = await AuthService.verify_token(token, token_type="access")
    assert payload is not None
    assert payload["aud"] == "nauta-portal"


@pytest.mark.asyncio
async def test_verify_token_still_accepts_the_platform_audience():
    from app.config import settings

    token, _jti, _exp = AuthService.create_access_token(
        user_id="00000000-0000-0000-0000-000000000001",
        tenant_id="00000000-0000-0000-0000-000000000002",
        email="a@b.test",
    )
    payload = await AuthService.verify_token(token, token_type="access")
    assert payload is not None
    assert payload["aud"] == settings.JWT_AUDIENCE


@pytest.mark.asyncio
async def test_verify_token_still_rejects_garbage():
    assert await AuthService.verify_token("not-a-token", token_type="access") is None
