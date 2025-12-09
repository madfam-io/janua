"""
OAuth2 Provider Endpoints for Janua

This module implements the OAuth 2.0 Authorization Server endpoints that allow
external applications (like Enclii) to authenticate users via Janua.

Implements:
- Authorization Endpoint (GET/POST /oauth/authorize)
- Token Endpoint (POST /oauth/token)
- UserInfo Endpoint (GET /oauth/userinfo)

Based on RFC 6749 (OAuth 2.0) and OpenID Connect Core 1.0
"""

import hashlib
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode, urlparse

import structlog
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.core.jwt_manager import jwt_manager
from app.core.redis import get_redis, ResilientRedisClient
from app.dependencies import get_current_user, get_current_user_optional
from app.models import OAuthClient, User

logger = structlog.get_logger()
router = APIRouter(prefix="/oauth", tags=["OAuth Provider"])


# ============================================================================
# Cookie-based Authentication Helper
# ============================================================================


async def get_user_from_cookie_or_header(
    request: Request,
    db: AsyncSession,
) -> Optional[User]:
    """
    Get authenticated user from either:
    1. Bearer token in Authorization header (API clients)
    2. janua_access_token cookie (browser-based OAuth flow)

    This enables the OAuth authorize endpoint to work with browser sessions
    after the user logs in via the login form.
    """
    # First, try to get user from Authorization header via dependency
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt_manager.verify_token(token, token_type='access')
            if payload and payload.get('sub'):
                result = await db.execute(
                    select(User).where(User.id == payload.get('sub'))
                )
                user = result.scalar_one_or_none()
                if user:
                    return user
        except Exception:
            pass

    # Second, try to get user from cookie
    access_token = request.cookies.get("janua_access_token")
    if access_token:
        try:
            payload = jwt_manager.verify_token(access_token, token_type='access')
            if payload and payload.get('sub'):
                result = await db.execute(
                    select(User).where(User.id == payload.get('sub'))
                )
                user = result.scalar_one_or_none()
                if user:
                    return user
        except Exception:
            pass

    return None


# ============================================================================
# Pydantic Schemas
# ============================================================================


class AuthorizationRequest(BaseModel):
    """OAuth 2.0 Authorization Request parameters."""

    response_type: str = Field(..., description="Must be 'code' for authorization code flow")
    client_id: str = Field(..., description="The OAuth client ID")
    redirect_uri: str = Field(..., description="Redirect URI for the callback")
    scope: str = Field("openid", description="Space-separated list of scopes")
    state: Optional[str] = Field(None, description="CSRF protection state parameter")
    nonce: Optional[str] = Field(None, description="Nonce for replay protection")
    code_challenge: Optional[str] = Field(None, description="PKCE code challenge")
    code_challenge_method: Optional[str] = Field(None, description="PKCE challenge method (S256)")


class TokenRequest(BaseModel):
    """OAuth 2.0 Token Request parameters."""

    grant_type: str = Field(..., description="Grant type (authorization_code, refresh_token)")
    code: Optional[str] = Field(None, description="Authorization code")
    redirect_uri: Optional[str] = Field(None, description="Redirect URI used in authorization")
    client_id: Optional[str] = Field(None, description="Client ID")
    client_secret: Optional[str] = Field(None, description="Client secret")
    refresh_token: Optional[str] = Field(None, description="Refresh token for token refresh")
    code_verifier: Optional[str] = Field(None, description="PKCE code verifier")


class TokenResponse(BaseModel):
    """OAuth 2.0 Token Response."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    scope: str


class UserInfoResponse(BaseModel):
    """OpenID Connect UserInfo Response."""

    sub: str = Field(..., description="Subject identifier (user ID)")
    email: Optional[str] = None
    email_verified: Optional[bool] = None
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    updated_at: Optional[int] = None


# ============================================================================
# Redis-based authorization code storage
# ============================================================================

AUTH_CODE_PREFIX = "oauth:code:"
AUTH_CODE_TTL = 600  # 10 minutes


async def _store_auth_code(code: str, data: dict, redis: ResilientRedisClient):
    """Store authorization code in Redis with TTL."""
    key = f"{AUTH_CODE_PREFIX}{code}"
    logger.info("Storing auth code in Redis", key=key, client_id=data.get("client_id"))
    success = await redis.set(key, json.dumps(data), ex=AUTH_CODE_TTL)
    if not success:
        logger.error("Failed to store auth code in Redis", key=key)
    else:
        logger.info("Auth code stored successfully", key=key)


async def _get_auth_code(code: str, redis: ResilientRedisClient) -> dict | None:
    """Retrieve authorization code from Redis."""
    key = f"{AUTH_CODE_PREFIX}{code}"
    logger.info("Retrieving auth code from Redis", key=key)
    data = await redis.get(key)
    if data:
        logger.info("Auth code found in Redis", key=key)
        return json.loads(data)
    logger.warning("Auth code NOT found in Redis", key=key)
    return None


async def _delete_auth_code(code: str, redis: ResilientRedisClient):
    """Delete authorization code from Redis (single use)."""
    key = f"{AUTH_CODE_PREFIX}{code}"
    await redis.delete(key)


# ============================================================================
# Helper Functions
# ============================================================================


async def _get_oauth_client(client_id: str, db: AsyncSession) -> OAuthClient | None:
    """Retrieve OAuth client by client_id."""
    result = await db.execute(select(OAuthClient).where(OAuthClient.client_id == client_id))
    return result.scalar_one_or_none()


def _validate_redirect_uri(redirect_uri: str, allowed_uris: list[str]) -> bool:
    """Validate that redirect_uri is in the allowed list."""
    parsed = urlparse(redirect_uri)
    # Normalize the URI (remove trailing slash)
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"

    for allowed in allowed_uris:
        allowed_parsed = urlparse(allowed)
        allowed_normalized = (
            f"{allowed_parsed.scheme}://{allowed_parsed.netloc}{allowed_parsed.path.rstrip('/')}"
        )
        if normalized == allowed_normalized:
            return True

    return False


def _verify_pkce(code_verifier: str, code_challenge: str, method: str = "S256") -> bool:
    """Verify PKCE code verifier against stored challenge."""
    if method == "S256":
        # S256: BASE64URL(SHA256(code_verifier))
        import base64

        verifier_hash = hashlib.sha256(code_verifier.encode("ascii")).digest()
        computed_challenge = base64.urlsafe_b64encode(verifier_hash).rstrip(b"=").decode("ascii")
        return secrets.compare_digest(computed_challenge, code_challenge)
    elif method == "plain":
        return secrets.compare_digest(code_verifier, code_challenge)
    return False


def _generate_id_token(
    user: User,
    client_id: str,
    nonce: Optional[str] = None,
    access_token: Optional[str] = None,
) -> str:
    """Generate an OpenID Connect ID Token."""
    now = datetime.now(timezone.utc)
    issuer = settings.BASE_URL or "https://auth.madfam.io"

    claims = {
        "iss": issuer,
        "sub": str(user.id),
        "aud": client_id,
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iat": int(now.timestamp()),
        "auth_time": int(now.timestamp()),
        "email": user.email,
        "email_verified": user.email_verified if hasattr(user, "email_verified") else True,
        "name": user.name if hasattr(user, "name") else None,
    }

    if nonce:
        claims["nonce"] = nonce

    # Add at_hash (access token hash) if access_token provided
    if access_token:
        # at_hash is left 128 bits of SHA256 of access token, base64url encoded
        import base64

        token_hash = hashlib.sha256(access_token.encode("ascii")).digest()
        claims["at_hash"] = base64.urlsafe_b64encode(token_hash[:16]).rstrip(b"=").decode("ascii")

    return jwt_manager.encode_token(claims)


# ============================================================================
# OAuth2 Authorization Endpoint
# ============================================================================


@router.get("/authorize")
async def authorize_get(
    request: Request,
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str = Query("openid"),
    state: Optional[str] = Query(None),
    nonce: Optional[str] = Query(None),
    code_challenge: Optional[str] = Query(None),
    code_challenge_method: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    redis: ResilientRedisClient = Depends(get_redis),
):
    """
    OAuth 2.0 Authorization Endpoint (GET).

    If user is not authenticated, redirect to login page.
    If user is authenticated, show consent screen or auto-approve.

    Authentication is checked from both:
    - Authorization header (Bearer token)
    - janua_access_token cookie (set by login form)
    """
    # Get user from header or cookie (supports browser-based OAuth flow)
    current_user = await get_user_from_cookie_or_header(request, db)

    # Validate response_type
    if response_type != "code":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="unsupported_response_type: Only 'code' is supported",
        )

    # Validate client
    client = await _get_oauth_client(client_id, db)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_client: Unknown client_id",
        )

    if not client.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_client: Client is disabled",
        )

    # Validate redirect_uri
    if not _validate_redirect_uri(redirect_uri, client.redirect_uris):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_redirect_uri: URI not registered for this client",
        )

    # Validate PKCE if provided
    if code_challenge and code_challenge_method not in (None, "S256", "plain"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_request: Unsupported code_challenge_method",
        )

    # If user not authenticated, redirect to login
    if not current_user:
        # Store auth request in session/query params and redirect to login
        login_params = urlencode(
            {
                "next": str(request.url),
                "client_id": client_id,
                "client_name": client.name,
            }
        )
        login_url = f"/api/v1/auth/login?{login_params}"
        return RedirectResponse(url=login_url, status_code=302)

    # User is authenticated - for now, auto-approve (in production, show consent screen)
    # Generate authorization code and store in Redis
    auth_code = secrets.token_urlsafe(32)
    code_data = {
        "client_id": client_id,
        "user_id": str(current_user.id),
        "redirect_uri": redirect_uri,
        "scope": scope,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method or "S256",
        "expires_at": time.time() + AUTH_CODE_TTL,
    }
    await _store_auth_code(auth_code, code_data, redis)

    # Update client last_used_at
    client.last_used_at = datetime.utcnow()
    await db.commit()

    # Redirect back to client with authorization code
    callback_params = {"code": auth_code}
    if state:
        callback_params["state"] = state

    callback_url = f"{redirect_uri}?{urlencode(callback_params)}"
    return RedirectResponse(url=callback_url, status_code=302)


@router.post("/authorize")
async def authorize_post(
    request: Request,
    response_type: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    scope: str = Form("openid"),
    state: Optional[str] = Form(None),
    nonce: Optional[str] = Form(None),
    code_challenge: Optional[str] = Form(None),
    code_challenge_method: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    redis: ResilientRedisClient = Depends(get_redis),
    current_user: User = Depends(get_current_user),
):
    """
    OAuth 2.0 Authorization Endpoint (POST).

    Used for form-based authorization (consent submission).
    """
    # Same validation as GET
    if response_type != "code":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="unsupported_response_type",
        )

    client = await _get_oauth_client(client_id, db)
    if not client or not client.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_client")

    if not _validate_redirect_uri(redirect_uri, client.redirect_uris):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_redirect_uri")

    # Generate authorization code and store in Redis
    auth_code = secrets.token_urlsafe(32)
    code_data = {
        "client_id": client_id,
        "user_id": str(current_user.id),
        "redirect_uri": redirect_uri,
        "scope": scope,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method or "S256",
        "expires_at": time.time() + AUTH_CODE_TTL,
    }
    await _store_auth_code(auth_code, code_data, redis)

    # Update client last_used_at
    client.last_used_at = datetime.utcnow()
    await db.commit()

    # Redirect with code
    callback_params = {"code": auth_code}
    if state:
        callback_params["state"] = state

    callback_url = f"{redirect_uri}?{urlencode(callback_params)}"
    return RedirectResponse(url=callback_url, status_code=302)


# ============================================================================
# OAuth2 Token Endpoint
# ============================================================================


@router.post("/token", response_model=TokenResponse)
async def token(
    request: Request,
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    client_secret: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    redis: ResilientRedisClient = Depends(get_redis),
):
    """
    OAuth 2.0 Token Endpoint.

    Exchanges authorization code for tokens or refreshes tokens.

    Supports:
    - authorization_code: Exchange auth code for access/refresh/id tokens
    - refresh_token: Get new access token using refresh token
    """
    # Handle client authentication (Basic auth or form params)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Basic "):
        import base64

        try:
            decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
            client_id, client_secret = decoded.split(":", 1)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid_client: Invalid Basic auth",
            )

    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_request: client_id required",
        )

    # Validate client
    client = await _get_oauth_client(client_id, db)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_client: Unknown client",
        )

    if not client.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_client: Client disabled",
        )

    # Verify client secret for confidential clients
    if client.is_confidential:
        if not client_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid_client: client_secret required",
            )
        if not client.verify_secret(client_secret):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid_client: Invalid client_secret",
            )

    # Handle grant types
    if grant_type == "authorization_code":
        return await _handle_authorization_code_grant(
            code=code,
            redirect_uri=redirect_uri,
            client=client,
            code_verifier=code_verifier,
            db=db,
            redis=redis,
        )
    elif grant_type == "refresh_token":
        return await _handle_refresh_token_grant(
            refresh_token=refresh_token,
            client=client,
            db=db,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported_grant_type: {grant_type}",
        )


async def _handle_authorization_code_grant(
    code: Optional[str],
    redirect_uri: Optional[str],
    client: OAuthClient,
    code_verifier: Optional[str],
    db: AsyncSession,
    redis: ResilientRedisClient,
) -> TokenResponse:
    """Handle authorization_code grant type."""
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_request: code required",
        )

    # Validate authorization code from Redis
    code_data = await _get_auth_code(code, redis)
    if not code_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_grant: Code not found or expired",
        )

    # Validate client matches
    if code_data["client_id"] != client.client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_grant: Code was not issued to this client",
        )

    # Validate redirect_uri matches
    if redirect_uri and code_data["redirect_uri"] != redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_grant: redirect_uri mismatch",
        )

    # Verify PKCE if code_challenge was provided during authorization
    if code_data.get("code_challenge"):
        if not code_verifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_request: code_verifier required",
            )
        if not _verify_pkce(
            code_verifier, code_data["code_challenge"], code_data.get("code_challenge_method", "S256")
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_grant: PKCE verification failed",
            )

    # Delete the code (single use)
    await _delete_auth_code(code, redis)

    # Get user
    user_id = code_data["user_id"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_grant: User not found",
        )

    # Generate tokens
    scope = code_data["scope"]
    access_token, _, _ = jwt_manager.create_access_token(
        user_id=str(user.id),
        email=user.email,
        additional_claims={
            "client_id": client.client_id,
            "scope": scope,
        },
    )

    refresh_token, _, _, _ = jwt_manager.create_refresh_token(
        user_id=str(user.id),
    )

    # Generate ID token if openid scope requested
    id_token = None
    if "openid" in scope:
        id_token = _generate_id_token(
            user=user,
            client_id=client.client_id,
            nonce=code_data.get("nonce"),
            access_token=access_token,
        )

    # Update client last_used_at
    client.last_used_at = datetime.utcnow()
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=3600,  # 1 hour
        refresh_token=refresh_token,
        id_token=id_token,
        scope=scope,
    )


async def _handle_refresh_token_grant(
    refresh_token: Optional[str],
    client: OAuthClient,
    db: AsyncSession,
) -> TokenResponse:
    """Handle refresh_token grant type."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_request: refresh_token required",
        )

    # Verify refresh token
    try:
        payload = jwt_manager.verify_token(refresh_token, token_type="refresh")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_grant: Invalid refresh token",
        )

    # Validate client matches
    if payload.get("client_id") != client.client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_grant: Token was not issued to this client",
        )

    # Get user
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_grant: User not found",
        )

    # Generate new access token
    scope = payload.get("scope", "openid")
    access_token, _, _ = jwt_manager.create_access_token(
        user_id=str(user.id),
        email=user.email,
        additional_claims={
            "client_id": client.client_id,
            "scope": scope,
        },
    )

    # Update client last_used_at
    client.last_used_at = datetime.utcnow()
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=3600,
        refresh_token=refresh_token,  # Return same refresh token
        scope=scope,
    )


# ============================================================================
# OpenID Connect UserInfo Endpoint
# ============================================================================


@router.get("/userinfo", response_model=UserInfoResponse)
async def userinfo(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    OpenID Connect UserInfo Endpoint.

    Returns claims about the authenticated user.
    Requires Bearer token in Authorization header.
    """
    # Get access token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token: Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[7:]

    # Verify token
    try:
        payload = jwt_manager.verify_token(token, token_type="access")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token: Token expired or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token: User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Build response based on scope
    scope = payload.get("scope", "")
    response = UserInfoResponse(sub=str(user.id))

    if "email" in scope or "openid" in scope:
        response.email = user.email
        response.email_verified = getattr(user, "email_verified", True)

    if "profile" in scope or "openid" in scope:
        response.name = getattr(user, "name", None)
        # Split name into given/family if possible
        if response.name:
            parts = response.name.split(" ", 1)
            response.given_name = parts[0]
            response.family_name = parts[1] if len(parts) > 1 else None

        response.picture = getattr(user, "avatar_url", None)
        if hasattr(user, "updated_at") and user.updated_at:
            response.updated_at = int(user.updated_at.timestamp())

    return response


# ============================================================================
# Token Introspection Endpoint (RFC 7662)
# ============================================================================


@router.post("/introspect")
async def introspect(
    request: Request,
    token: str = Form(...),
    token_type_hint: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    client_secret: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth 2.0 Token Introspection Endpoint (RFC 7662).

    Allows resource servers to query token validity.
    """
    # Authenticate client (required for introspection)
    if not client_id:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Basic "):
            import base64

            try:
                decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                client_id, client_secret = decoded.split(":", 1)
            except Exception:
                pass

    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Client authentication required",
        )

    client = await _get_oauth_client(client_id, db)
    if not client or not client.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_client",
        )

    if client.is_confidential and not client.verify_secret(client_secret or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_client",
        )

    # Try to verify the token
    try:
        # Try as access token first
        token_type = token_type_hint or "access"
        payload = jwt_manager.verify_token(token, token_type=token_type)

        return {
            "active": True,
            "sub": payload.get("sub"),
            "client_id": payload.get("client_id"),
            "scope": payload.get("scope"),
            "exp": payload.get("exp"),
            "iat": payload.get("iat"),
            "token_type": token_type,
        }
    except Exception:
        # Token is invalid or expired
        return {"active": False}


# ============================================================================
# Token Revocation Endpoint (RFC 7009)
# ============================================================================


@router.post("/revoke")
async def revoke(
    request: Request,
    token: str = Form(...),
    token_type_hint: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    client_secret: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth 2.0 Token Revocation Endpoint (RFC 7009).

    Revokes access or refresh tokens.
    """
    # Authenticate client
    if not client_id:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Basic "):
            import base64

            try:
                decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                client_id, client_secret = decoded.split(":", 1)
            except Exception:
                pass

    if client_id:
        client = await _get_oauth_client(client_id, db)
        if client and client.is_confidential:
            if not client.verify_secret(client_secret or ""):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="invalid_client",
                )

    # In production, add token to blacklist in Redis
    # For now, we just acknowledge the revocation
    # The token will expire naturally based on its exp claim

    # Return 200 OK regardless of whether token was valid
    # This is per RFC 7009 - don't leak token validity information
    return {"message": "Token revoked"}
