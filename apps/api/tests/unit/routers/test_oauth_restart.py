"""When pre-login state is gone, restart at the client — never fabricate.

Janua used to rebuild a synthetic /oauth/authorize URL from the client's
registration whenever the Redis pre-login blob had expired or been consumed.
That URL necessarily carried no `state`, no `nonce` and no PKCE challenge:
the authorization server cannot know them, only the client that started the
flow can. Any OIDC client that validates `state` (all of them) rejects the
resulting callback — Auth.js reports `response parameter "state" missing`.

Observed in prod 2026-08-13: a second sign-in click always landed on this
path, so the retry failed differently from the first attempt and the operator
was stuck in a loop that looked like "the login button needs two clicks".
"""

from types import SimpleNamespace

import pytest

from app.routers.v1.auth import _recover_authorize_url_from_client


class _Result:
    def __init__(self, obj):
        self._obj = obj

    def scalar_one_or_none(self):
        return self._obj


class _DB:
    def __init__(self, obj):
        self._obj = obj

    async def execute(self, _stmt):
        return _Result(self._obj)


def _client(**overrides):
    base = {
        "client_id": "jnc_test",
        "is_active": True,
        "redirect_uris": ["https://cto.madfam.io/api/auth/callback/janua"],
        "allowed_scopes": ["openid", "profile"],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_restarts_at_the_client_origin():
    url = await _recover_authorize_url_from_client("jnc_test", _DB(_client()))
    assert url == "https://cto.madfam.io/"


@pytest.mark.asyncio
async def test_never_fabricates_an_authorize_request():
    """The regression itself: a server-built authorize request cannot carry
    the client's state or verifier, so it must not be built at all."""
    url = await _recover_authorize_url_from_client("jnc_test", _DB(_client()))
    assert "/oauth/authorize" not in url
    assert "state" not in url
    assert "code_challenge" not in url
    assert "response_type" not in url


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "client",
    [None, _client(is_active=False), _client(redirect_uris=[]), _client(redirect_uris=["notaurl"])],
)
async def test_declines_when_no_usable_origin(client):
    assert await _recover_authorize_url_from_client("jnc_test", _DB(client)) is None


@pytest.mark.asyncio
async def test_json_encoded_redirect_uris_are_understood():
    """Some rows store redirect_uris as a JSON string rather than a list."""
    client = _client(redirect_uris='["https://crea.madfam.io/api/auth/callback/janua"]')
    assert await _recover_authorize_url_from_client("jnc_test", _DB(client)) == (
        "https://crea.madfam.io/"
    )
