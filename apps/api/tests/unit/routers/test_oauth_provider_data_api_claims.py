"""
Unit tests for the data-API (PostgREST/BaaS) token shaping — `_data_api_claims`.

The seam that makes a Janua access token consumable by an enclii managed-Postgres
addon's PostgREST: when (and only when) a client opts into the ``data-api`` scope,
the token gains a SCALAR ``role`` claim (for PostgREST's ``SET LOCAL ROLE``) and a
client-bound ``tenant_id``. Every non-opted-in token must be unchanged.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.routers.v1.oauth_provider import (
    DATA_API_ROLE,
    DATA_API_SCOPE,
    _data_api_claims,
)


def _client(*, organization_id=None):
    return SimpleNamespace(client_id="jnc_test", organization_id=organization_id)


class TestDataApiClaims:
    def test_no_op_without_the_scope(self):
        # A normal ecosystem token (openid profile email) is unchanged.
        assert _data_api_claims("openid profile email", _client(), {}) == {}

    def test_no_op_even_when_client_is_org_bound_but_scope_absent(self):
        # Opt-in is by SCOPE, not by the client having an org — no scope, no claims.
        org = uuid4()
        assert _data_api_claims("openid", _client(organization_id=org), {}) == {}

    def test_adds_scalar_role_when_scope_present(self):
        claims = _data_api_claims(f"openid {DATA_API_SCOPE}", _client(), {})
        assert claims["role"] == DATA_API_ROLE == "authenticated"
        # It is a scalar string, NOT the array `roles` claim PostgREST cannot use.
        assert isinstance(claims["role"], str)

    def test_tenant_id_bound_to_the_client_org_when_present(self):
        org = uuid4()
        claims = _data_api_claims(DATA_API_SCOPE, _client(organization_id=org), {})
        # The client's org wins — a data-API addon is registered FOR a tenant, so
        # it scopes to that tenant regardless of the end-user's memberships.
        assert claims["tenant_id"] == str(org)

    def test_client_org_overrides_ambiguous_org_claims_tenant(self):
        client_org = uuid4()
        other = str(uuid4())
        claims = _data_api_claims(
            DATA_API_SCOPE,
            _client(organization_id=client_org),
            {"tenant_id": other},
        )
        assert claims["tenant_id"] == str(client_org)
        assert claims["tenant_id"] != other

    def test_falls_back_to_org_claims_tenant_when_client_not_org_bound(self):
        resolved = str(uuid4())
        claims = _data_api_claims(
            DATA_API_SCOPE, _client(organization_id=None), {"tenant_id": resolved}
        )
        assert claims["tenant_id"] == resolved

    def test_role_present_but_no_tenant_when_neither_source_has_one(self):
        # Client not org-bound and no resolved tenant → still get the role (so
        # PostgREST authenticates the user), just no tenant_id claim.
        claims = _data_api_claims(DATA_API_SCOPE, _client(organization_id=None), {})
        assert claims == {"role": DATA_API_ROLE}

    def test_scope_matching_is_token_exact_not_substring(self):
        # A scope that merely contains the substring must not trigger it.
        assert _data_api_claims("data-api-readonly", _client(), {}) == {}
