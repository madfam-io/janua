"""Schemas for the internal OAuth-client scope-grant API.

The grant record for a SERVICE client is its ``OAuthClient.allowed_scopes``.
A person's application roles hang off a membership row
(``organization_member_app_roles``, migration 016); a machine principal has no
membership, so the operator-controlled column that already decides what the
client may ask for is where its authority lives. These types are the shape of
an edit to that column that does not require SQL against production.

Design rules, deliberately the same ones ``schemas/app_role.py`` holds:

* ``scope`` is an OPAQUE STRING. Janua stores it, matches it, and (for the
  namespaced ``"<app>:<role>"`` shape) emits it verbatim into the ``roles``
  claim. There is no enum of known apps and no vocabulary of role names — a new
  HCM role must not require a janua deploy. What janua validates is SHAPE.
* Shape validation exists because a malformed scope becomes a live
  authorization string. No blank values, no whitespace (the column is read back
  as a space-separated request, so an embedded space would split one grant into
  two), and a length bound.
* The client is named by its PUBLIC ``client_id`` in the path, never by the
  secret. Nothing in this surface reads, returns, or logs secret material.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, field_validator

#: Bound on a single scope string. Generous — this is a shape check, not a
#: vocabulary — but finite, so a caller cannot write an unbounded string into a
#: column every token mint reads.
MAX_SCOPE_LENGTH = 128


def _validate_scope(value: str) -> str:
    """Shape-check one scope. Never a meaning check."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("scope must not be empty")
    if len(cleaned) > MAX_SCOPE_LENGTH:
        raise ValueError(f"scope exceeds {MAX_SCOPE_LENGTH} characters")
    if any(c.isspace() for c in cleaned):
        # `allowed_scopes` is compared against a SPACE-SEPARATED request
        # (`_parse_requested_scopes`), so a scope containing a space could never
        # be requested and would sit in the column as dead authority.
        raise ValueError("scope must not contain whitespace")
    return cleaned


class OAuthClientScopeRequest(BaseModel):
    """Grant or revoke ONE scope on ONE client."""

    scope: str = Field(min_length=1, max_length=MAX_SCOPE_LENGTH)

    @field_validator("scope")
    @classmethod
    def _check_scope(cls, value: str) -> str:
        return _validate_scope(value)


class OAuthClientScopeResponse(BaseModel):
    """Result of a scope grant or revoke.

    ``changed`` distinguishes "this call did it" from "it was already so", the
    same idempotency signal ``internal_app_roles.py`` and ``internal_users.py``
    report. ``allowed_scopes`` echoes the FULL resulting list so an operator can
    verify the outcome without a second read.

    ``emits_app_role`` answers the question the caller actually has: *will this
    scope reach the token's ``roles`` claim?* It is true only when the scope has
    the namespaced application-role shape AND the client is organization-bound —
    the exact predicate the token path applies (see
    ``routers/v1/oauth_provider._service_client_app_roles``), computed here so
    an operator who grants ``hcm_hr`` by mistake, or grants ``hcm:hr`` to a
    client with no organization, is told rather than left wondering why HCM
    still answers 403.
    """

    client_id: str
    organization_id: str | None = None
    scope: str
    allowed_scopes: List[str]
    emits_app_role: bool
    changed: bool


class OAuthClientScopeListResponse(BaseModel):
    """Everything one client may ask for, plus what becomes an app role.

    ``app_role_scopes`` is the resolved subset that will reach the token's
    ``roles`` claim — computed with the same predicate the token path applies,
    so an operator reading this sees the token's contents rather than a variant.
    Empty when the client has no ``organization_id``, which is itself the
    diagnosis in the most common "HCM still says 403" case.

    Carries no secret material.
    """

    client_id: str
    organization_id: str | None = None
    allowed_scopes: List[str]
    app_role_scopes: List[str]
