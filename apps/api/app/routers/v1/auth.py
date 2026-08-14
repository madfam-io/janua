"""
Authentication router for v1 API
"""

import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional
from urllib.parse import urlencode, urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.orm import Session

import structlog

from app.config import settings
from app.core.redis import ResilientRedisClient, get_redis
from app.core.url_security import validate_redirect_url
from app.database import AsyncSessionLocal, get_db
from app.dependencies import get_current_user
from app.services.account_lockout_service import AccountLockoutService
from app.services.auth_service import AuthService
from app.services.audit_logger import AuditEventType, AuditLogger
from app.services.email import EmailService
from app.services.email_service import (
    send_magic_link_email_task,
    send_password_reset_email_task,
    send_verification_email_task,
)
from app.services.webhooks import WebhookEventType, trigger_user_webhook

from ...models import ActivityLog, EmailVerification, MagicLink, PasswordReset, User, UserStatus
from ...models import Session as UserSession

logger = structlog.get_logger()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

# Include OAuth sub-router
from app.routers.v1 import oauth

router.include_router(oauth.router)


# Request/Response Models
class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    username: Optional[str] = Field(None, min_length=3, max_length=50)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        if v and not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v


class SignInRequest(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: str

    @model_validator(mode="after")
    def validate_credentials(self):
        if not self.username and not self.email:
            raise ValueError("Either email or username must be provided")
        return self


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    # Optional product-surface page that will consume the token, e.g.
    # "https://app.dhan.am/reset-password". Only honored when its value is in
    # settings.PASSWORD_RESET_REDIRECT_ORIGINS — otherwise the default
    # FRONTEND_URL page is used. Lets each product's reset email land on that
    # product's own UI instead of Janua's.
    redirect_base: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class VerifyEmailRequest(BaseModel):
    token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class MagicLinkRequest(BaseModel):
    email: EmailStr
    redirect_url: Optional[str] = None


class VerifyMagicLinkRequest(BaseModel):
    token: str


class UserResponse(BaseModel):
    id: str
    email: str
    email_verified: bool
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    profile_image_url: Optional[str]
    is_admin: bool = False
    created_at: datetime
    updated_at: datetime
    last_sign_in_at: Optional[datetime]


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class SignInResponse(BaseModel):
    user: UserResponse
    tokens: Optional[TokenResponse] = None
    mfa_required: bool = False
    mfa_token: Optional[str] = None


# Helper functions (get_current_user moved to app.dependencies)


async def log_activity(
    db: Session, user_id: str, action: str, details: Dict = None, request: Request = None
):
    """Log user activity"""
    activity = ActivityLog(
        user_id=user_id,
        action=action,
        activity_metadata=details or {},  # Model uses activity_metadata, not details
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.add(activity)
    await db.commit()


# SOC 2 CF-08: Audit event type mapping for auth actions
_AUDIT_EVENT_MAP = {
    "signup": AuditEventType.AUTH_SIGNUP,
    "signin": AuditEventType.AUTH_SIGNIN,
    "signout": AuditEventType.AUTH_SIGNOUT,
    "password_change": AuditEventType.AUTH_PASSWORD_CHANGE,
    "password_reset": AuditEventType.AUTH_PASSWORD_RESET,
    "email_verified": AuditEventType.USER_UPDATE,
}


async def log_audit_event(
    db: Session, user_id: str, action: str, details: Dict = None, request: Request = None
):
    """Log to SOC 2 audit trail (CF-08) alongside activity log."""
    event_type = _AUDIT_EVENT_MAP.get(action)
    if not event_type:
        return
    try:
        audit_logger = AuditLogger(db)
        await audit_logger.log(
            event_type=event_type,
            tenant_id="default",
            identity_id=user_id,
            details=details or {},
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            severity="info",
        )
    except Exception:
        # Audit logging failure should not break auth flow
        pass


# Authentication endpoints
@router.post("/signup", response_model=SignInResponse)
@limiter.limit("3/minute")  # Strict rate limiting for signup
async def sign_up(
    request: Request,
    signup_data: SignUpRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Create a new user account"""
    if not settings.ENABLE_SIGNUPS:
        raise HTTPException(status_code=403, detail="Sign ups are currently disabled")

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == signup_data.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check if username already exists
    if signup_data.username:
        result = await db.execute(select(User).where(User.username == signup_data.username))
        existing_username = result.scalar_one_or_none()
        if existing_username:
            raise HTTPException(status_code=400, detail="Username already taken")

    # Validate password
    valid, message = AuthService.validate_password_strength(signup_data.password)
    if not valid:
        raise HTTPException(status_code=400, detail=message)

    # Create user
    user = User(
        email=signup_data.email,
        password_hash=AuthService.hash_password(signup_data.password),
        first_name=signup_data.first_name,
        last_name=signup_data.last_name,
        username=signup_data.username,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create session
    access_token, refresh_token, session = await AuthService.create_session(
        db, user, ip_address=request.client.host, user_agent=request.headers.get("user-agent")
    )

    # Log activity
    await log_activity(db, str(user.id), "signup", {"method": "email"}, request)
    await log_audit_event(db, str(user.id), "signup", {"method": "email"}, request)

    # Dispatch user.created webhook for CRM integration.
    # ISOLATED session, deliberately: the webhook path inserts an event-log
    # row, and a failure there (prod 2026-08-02: legacy_webhook_events table
    # missing) used to poison THIS request's session — the except below
    # swallowed the first error, but the doomed pending INSERT detonated at
    # the next db.commit(), turning every valid signup into a 503. With a
    # dedicated session, webhook logging cannot touch the signup transaction.
    try:
        async with AsyncSessionLocal() as webhook_db:
            await trigger_user_webhook(
                webhook_db,
                WebhookEventType.USER_CREATED,
                {
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "username": user.username,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                },
                user_id=str(user.id),
            )
            await webhook_db.commit()
    except Exception:
        pass  # Webhook failure must not block signup

    # Send verification email in background
    if settings.EMAIL_ENABLED:
        verification_token = secrets.token_urlsafe(32)
        verification = EmailVerification(
            user_id=user.id,
            token=verification_token,
            email=user.email,
            expires_at=datetime.utcnow() + timedelta(hours=48),
        )
        db.add(verification)
        await db.commit()

        background_tasks.add_task(
            send_verification_email_task,
            user.email,
            verification_token,
            locale=getattr(user, "locale", None),
        )

    return SignInResponse(
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            email_verified=user.email_verified,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            profile_image_url=user.profile_image_url,
            is_admin=getattr(user, "is_admin", False),
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_sign_in_at=user.last_sign_in_at,
        ),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )


@router.post("/signin", response_model=SignInResponse)
@limiter.limit("5/minute")  # Rate limiting for signin attempts
async def sign_in(credentials: SignInRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticate user and get tokens"""
    # Find user - we need to find the user first to check lockout status
    # Note: We look for any user (not just ACTIVE) to check lockout, then verify status
    if credentials.email:
        result = await db.execute(select(User).where(User.email == credentials.email))
        user = result.scalar_one_or_none()
    else:
        result = await db.execute(select(User).where(User.username == credentials.username))
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check if account is locked
    is_locked, seconds_remaining = AccountLockoutService.is_account_locked(user)
    if is_locked:
        minutes_remaining = (seconds_remaining or 0) // 60 + 1
        raise HTTPException(
            status_code=423,  # HTTP 423 Locked
            detail=f"Account temporarily locked due to too many failed login attempts. "
            f"Please try again in {minutes_remaining} minute(s).",
        )

    # Check user status after lockout check
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password
    if not user.password_hash or not AuthService.verify_password(
        credentials.password, user.password_hash
    ):
        # Record failed attempt
        ip_address = request.client.host if request.client else None
        is_now_locked, lock_seconds = await AccountLockoutService.record_failed_attempt(
            db, user, ip_address=ip_address
        )
        if is_now_locked:
            minutes_remaining = (lock_seconds or 0) // 60 + 1
            raise HTTPException(
                status_code=423,
                detail=f"Account locked due to too many failed login attempts. "
                f"Please try again in {minutes_remaining} minute(s).",
            )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Reset failed attempts on successful login
    await AccountLockoutService.reset_failed_attempts(db, user)

    # SECURITY: Check if MFA is required before issuing session tokens
    if getattr(user, 'mfa_enabled', False) and getattr(user, 'mfa_secret', None):
        # Issue a short-lived MFA challenge token (not a session token)
        import jwt as pyjwt

        mfa_challenge_payload = {
            "sub": str(user.id),
            "type": "mfa_challenge",
            "exp": datetime.utcnow() + timedelta(minutes=5),
            "iat": datetime.utcnow(),
            "iss": settings.JWT_ISSUER,
        }
        mfa_token = pyjwt.encode(
            mfa_challenge_payload,
            settings.JWT_SECRET_KEY or "development-secret-key",
            algorithm="HS256",
        )

        await log_activity(db, str(user.id), "signin", {"method": "password", "mfa_required": True}, request)

        return SignInResponse(
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                email_verified=user.email_verified,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                profile_image_url=user.profile_image_url,
                is_admin=getattr(user, "is_admin", False),
                created_at=user.created_at,
                updated_at=user.updated_at,
                last_sign_in_at=user.last_sign_in_at,
            ),
            tokens=None,
            mfa_required=True,
            mfa_token=mfa_token,
        )

    # Create session (no MFA required)
    access_token, refresh_token, session = await AuthService.create_session(
        db, user, ip_address=request.client.host, user_agent=request.headers.get("user-agent")
    )

    # Log activity (best-effort, don't fail login)
    try:
        await log_activity(db, str(user.id), "signin", {"method": "password"}, request)
    except Exception:
        pass
    try:
        await log_audit_event(db, str(user.id), "signin", {"method": "password"}, request)
    except Exception:
        pass

    return SignInResponse(
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            email_verified=user.email_verified,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            profile_image_url=user.profile_image_url,
            is_admin=getattr(user, "is_admin", False),
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_sign_in_at=user.last_sign_in_at,
        ),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )


@router.get("/session")
async def check_session(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Check if the user has an active session via cookies.

    This endpoint is used for silent authentication / SSO across subdomains.
    It reads the access_token from HTTP-only cookies (set with COOKIE_DOMAIN)
    and returns user info if valid.

    Returns:
        - 200 with user info if session is valid
        - 401 if no session or invalid token
    """
    # Try to get access token from cookies
    access_token = request.cookies.get("access_token")

    if not access_token:
        raise HTTPException(status_code=401, detail="No session cookie found")

    # Validate access token
    payload = AuthService.verify_token(access_token, token_type="access")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    # Fetch user from database
    from uuid import UUID as PyUUID

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(
        select(User).where(User.id == PyUUID(user_id), User.status == UserStatus.ACTIVE)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return {
        "authenticated": True,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email_verified": user.email_verified,
            "roles": getattr(user, "roles", []),
            "permissions": getattr(user, "permissions", []),
            "is_admin": getattr(user, "is_admin", False),
        },
        "session": {
            "expires_at": payload.get("exp"),
        },
    }


def _oauth_context_hidden_fields_html(
    *,
    auth_request_id: Optional[str],
    client_id: Optional[str],
    client_name: Optional[str],
    next_url: Optional[str] = None,
) -> str:
    """Hidden form fields that preserve OAuth context across retries."""
    import html

    parts: list[str] = []
    if auth_request_id:
        parts.append(
            f'<input type="hidden" name="auth_request_id" value="{html.escape(auth_request_id)}">'
        )
    elif next_url:
        parts.append(f'<input type="hidden" name="next" value="{html.escape(next_url)}">')
    if client_id:
        parts.append(
            f'<input type="hidden" name="client_id" value="{html.escape(client_id)}">'
        )
    if client_name:
        parts.append(
            f'<input type="hidden" name="client_name" value="{html.escape(client_name)}">'
        )
    return "".join(parts)


async def _recover_authorize_url_from_client(client_id: str, db) -> Optional[str]:
    """Send the user back to the CLIENT so it can start a fresh flow.

    This used to rebuild a synthetic /oauth/authorize URL from the client's
    registration. That URL carried no `state`, no `nonce` and no PKCE
    challenge, because the server cannot know them — only the client that
    started the flow does. Every modern OIDC client validates `state` and a
    PKCE verifier against its own cookies, so the callback produced by such a
    fabricated request could never be accepted: Auth.js rejects it with
    `response parameter "state" missing` (observed in prod 2026-08-13).

    A recovery that cannot succeed is worse than an honest restart. Returning
    the client's own origin lets it mint a new state + verifier pair the way
    it always does.
    """
    from ...models import OAuthClient as _OAuthClient

    stmt = select(_OAuthClient).where(_OAuthClient.client_id == client_id)
    result = await db.execute(stmt)
    oauth_client = result.scalar_one_or_none()
    if not oauth_client or not oauth_client.is_active or not oauth_client.redirect_uris:
        return None

    redirect_uris = oauth_client.redirect_uris
    if isinstance(redirect_uris, str):
        try:
            redirect_uris = json.loads(redirect_uris)
        except json.JSONDecodeError:
            redirect_uris = []
    if not redirect_uris:
        return None

    # The origin of the registered callback is the product itself. Landing
    # there re-enters the product's own sign-in entry point, which starts a
    # complete authorize request (state + PKCE) that its callback can verify.
    parsed = urlparse(redirect_uris[0])
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}/"


# GET /login - Render login form for OAuth flows
@router.get("/login")
async def login_page(
    request: Request,
    next: Optional[str] = None,
    auth_request_id: Optional[str] = None,
    client_id: Optional[str] = None,
    client_name: Optional[str] = None,
    db=Depends(get_db),
    redis: ResilientRedisClient = Depends(get_redis),
):
    """
    Render login page for OAuth authorization flows.

    This endpoint serves an HTML login form that:
    1. Accepts email/password credentials
    2. POSTs to /api/v1/auth/login-form
    3. On success, redirects to the OAuth authorize endpoint

    Query params:
    - auth_request_id: Opaque ID for Redis-stored OAuth params (preferred for OAuth flows)
    - next: URL to redirect to after successful login (fallback for non-OAuth logins)
    - client_id: OAuth client requesting authorization
    - client_name: Human-readable name of the OAuth client
    """
    import html

    from fastapi.responses import HTMLResponse, RedirectResponse

    # Stale bookmarked login URLs carry an expired auth_request_id. Restart the
    # OAuth flow instead of rendering a form that cannot complete.
    if auth_request_id and client_id:
        stored_data = await redis.get(f"oauth:pre_login:{auth_request_id}")
        if not stored_data:
            recovered = await _recover_authorize_url_from_client(client_id, db)
            if recovered:
                logger.info(
                    "login_page.stale_auth_request_restarted",
                    auth_request_id=auth_request_id,
                    client_id=client_id,
                )
                return RedirectResponse(url=recovered, status_code=302)

    # SECURITY: Validate the 'next' URL to prevent open redirect attacks (CWE-601)
    safe_next = validate_redirect_url(next or "/", default_url="/")
    app_name = html.escape(client_name or "Application")

    hidden_fields = _oauth_context_hidden_fields_html(
        auth_request_id=auth_request_id,
        client_id=client_id,
        client_name=client_name,
        next_url=safe_next if not auth_request_id else None,
    )

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign in - Janua</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .login-container {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            width: 100%;
            max-width: 400px;
        }}
        .logo {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .logo h1 {{
            font-size: 28px;
            color: #333;
            margin-bottom: 8px;
        }}
        .logo p {{
            color: #666;
            font-size: 14px;
        }}
        .app-info {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 24px;
            text-align: center;
        }}
        .app-info span {{
            color: #666;
            font-size: 13px;
        }}
        .app-info strong {{
            color: #333;
        }}
        .form-group {{
            margin-bottom: 20px;
        }}
        label {{
            display: block;
            margin-bottom: 6px;
            color: #333;
            font-weight: 500;
            font-size: 14px;
        }}
        input[type="email"], input[type="password"] {{
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e1e5eb;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.2s, box-shadow 0.2s;
        }}
        input:focus {{
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}
        button {{
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }}
        button:disabled {{
            opacity: 0.7;
            cursor: not-allowed;
            transform: none;
        }}
        .error {{
            background: #fee;
            color: #c00;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
            display: none;
        }}
        .aux-link {{
            text-align: right;
            margin-top: 6px;
        }}
        .aux-link a {{
            color: #667eea;
            font-size: 13px;
            text-decoration: none;
        }}
        .aux-link a:hover {{
            text-decoration: underline;
        }}
        .footer {{
            text-align: center;
            margin-top: 24px;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <h1>&#128274; Janua</h1>
            <p>Identity Platform</p>
        </div>

        <div class="app-info">
            <span>Signing in to <strong>{app_name}</strong></span>
        </div>

        <div class="error" id="error"></div>

        <form id="loginForm" method="POST" action="/api/v1/auth/login-form">
            {hidden_fields}
            <div class="form-group">
                <label for="email">Email</label>
                <input type="email" id="email" name="email" required autocomplete="email" autofocus>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required autocomplete="current-password">
                <div class="aux-link"><a href="/api/v1/auth/forgot-password">Forgot your password?</a></div>
            </div>
            <button type="submit" id="submitBtn">Sign In</button>
        </form>

        <div class="footer">
            Powered by Janua &bull; Secure Authentication
        </div>
    </div>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


# Form-based login for OAuth flows (handles browser form POST, sets cookies, redirects)
@router.post("/login-form")
@limiter.limit("5/minute")
async def login_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
    auth_request_id: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    client_name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    redis: ResilientRedisClient = Depends(get_redis),
):
    """
    Handle form-based login for OAuth authorization flows.

    This endpoint:
    1. Authenticates the user with email/password
    2. Sets access_token cookie for subsequent requests
    3. Redirects to the OAuth authorize endpoint (reconstructed from Redis) or 'next' URL

    This works without JavaScript, avoiding CSP issues with inline scripts.

    SECURITY: When auth_request_id is present, the OAuth parameters are retrieved from
    Redis and the authorize URL is reconstructed fresh, avoiding double-encoding issues
    with urlencode() that caused redirect loops. Falls back to the 'next' param for
    non-OAuth logins.
    """
    import html

    from fastapi.responses import HTMLResponse, RedirectResponse

    # Determine the redirect target: prefer Redis-backed auth request over 'next' URL.
    # This avoids the double-encoding bug where urlencode(redirect_uri) produced
    # mangled query strings that caused infinite redirect loops.
    #
    # Branch outcomes (each emits a structured log so silent UX failures are
    # diagnosable post-hoc — track via log line key `login_form.redirect_branch`):
    #   - redis_hit             → OAuth flow resumes (happy path)
    #   - redis_miss_oauth_recovered → OAuth flow resumes via OAuthClient fallback
    #   - redis_miss_no_recovery → renders an "expired session" error page (NOT
    #                              a silent redirect to JSON `/`, the historical bug)
    #   - redis_miss_parse_error → same as redis_miss_no_recovery
    #   - non_oauth             → normal `next` URL flow
    safe_next = "/"
    oauth_recovery_attempted = False
    redirect_branch = "non_oauth"
    if auth_request_id:
        # Retrieve stored OAuth parameters from Redis
        stored_data = await redis.get(f"oauth:pre_login:{auth_request_id}")
        if stored_data:
            try:
                auth_params = json.loads(stored_data)
                # Reconstruct the authorize URL fresh from stored parameters.
                # Only include non-None parameters to avoid polluting the URL.
                query_params = {}
                for key in [
                    "response_type", "client_id", "redirect_uri", "scope",
                    "state", "nonce", "code_challenge", "code_challenge_method",
                ]:
                    if auth_params.get(key) is not None:
                        query_params[key] = auth_params[key]

                safe_next = f"/api/v1/oauth/authorize?{urlencode(query_params)}"
                redirect_branch = "redis_hit"
                logger.info(
                    "login_form.redirect_branch",
                    branch=redirect_branch,
                    auth_request_id=auth_request_id,
                    client_id=auth_params.get("client_id"),
                )
            except (json.JSONDecodeError, KeyError) as e:
                redirect_branch = "redis_miss_parse_error"
                logger.warning(
                    "login_form.redirect_branch",
                    branch=redirect_branch,
                    auth_request_id=auth_request_id,
                    error=str(e),
                )
                oauth_recovery_attempted = True
        else:
            redirect_branch = "redis_miss"
            logger.warning(
                "login_form.redirect_branch",
                branch=redirect_branch,
                auth_request_id=auth_request_id,
                client_id_present=bool(client_id),
            )
            oauth_recovery_attempted = True

        # OAuth flow recovery: when Redis lost the params (TTL expired or API
        # restart), try to reconstruct a minimal authorize URL from the
        # OAuth client's first registered redirect_uri. This avoids the silent
        # redirect to `/` (raw JSON) that previously made "Sign In does
        # nothing". The user still needs to re-consent / re-grant if scopes
        # changed, but they land somewhere meaningful.
        if oauth_recovery_attempted and client_id:
            recovered = await _recover_authorize_url_from_client(client_id, db)
            if recovered:
                safe_next = recovered
                redirect_branch = "redis_miss_oauth_recovered"
                logger.info(
                    "login_form.redirect_branch",
                    branch=redirect_branch,
                    client_id=client_id,
                )
            else:
                logger.warning(
                    "login_form.redirect_branch",
                    branch="redis_miss_no_recovery",
                    client_id=client_id,
                )
                redirect_branch = "redis_miss_no_recovery"
    else:
        # Fallback: validate the 'next' URL for non-OAuth logins (CWE-601)
        safe_next = validate_redirect_url(next, default_url="/")

    # Preserve full OAuth context on error-page retries (including client_id so
    # Redis expiry recovery still works after a wrong-password attempt).
    error_hidden_field = _oauth_context_hidden_fields_html(
        auth_request_id=auth_request_id,
        client_id=client_id,
        client_name=client_name,
        next_url=safe_next if not auth_request_id else None,
    )

    # Helper to return error page
    def make_error_page(error_message: str) -> HTMLResponse:
        error_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign in - Janua</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .login-container {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            width: 100%;
            max-width: 400px;
        }}
        .logo {{ text-align: center; margin-bottom: 30px; }}
        .logo h1 {{ font-size: 28px; color: #333; margin-bottom: 8px; }}
        .logo p {{ color: #666; font-size: 14px; }}
        .form-group {{ margin-bottom: 20px; }}
        label {{ display: block; margin-bottom: 6px; color: #333; font-weight: 500; font-size: 14px; }}
        input[type="email"], input[type="password"] {{
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e1e5eb;
            border-radius: 8px;
            font-size: 16px;
        }}
        input:focus {{ outline: none; border-color: #667eea; }}
        button {{
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
        }}
        .error {{
            background: #fee;
            color: #c00;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        .footer {{ text-align: center; margin-top: 24px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <h1>&#128274; Janua</h1>
            <p>Identity Platform</p>
        </div>
        <div class="error">{html.escape(error_message)}</div>
        <form method="POST" action="/api/v1/auth/login-form">
            {error_hidden_field}
            <div class="form-group">
                <label for="email">Email</label>
                <input type="email" id="email" name="email" value="{html.escape(email)}" required autofocus>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
                <div style="text-align:right;margin-top:6px"><a href="/api/v1/auth/forgot-password" style="color:#667eea;font-size:13px;text-decoration:none">Forgot your password?</a></div>
            </div>
            <button type="submit">Sign In</button>
        </form>
        <div class="footer">Powered by Janua &bull; Secure Authentication</div>
    </div>
</body>
</html>
"""
        return HTMLResponse(content=error_html, status_code=401)

    # Find user by email (without status filter to check lockout first)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        return make_error_page("Invalid email or password. Please try again.")

    # Check if account is locked
    is_locked, seconds_remaining = AccountLockoutService.is_account_locked(user)
    if is_locked:
        minutes_remaining = (seconds_remaining or 0) // 60 + 1
        return make_error_page(
            f"Account temporarily locked due to too many failed login attempts. "
            f"Please try again in {minutes_remaining} minute(s)."
        )

    # Check user status after lockout check
    if user.status != UserStatus.ACTIVE:
        return make_error_page("Invalid email or password. Please try again.")

    # Verify password
    if not user.password_hash or not AuthService.verify_password(password, user.password_hash):
        # Record failed attempt
        ip_address = request.client.host if request.client else None
        is_now_locked, lock_seconds = await AccountLockoutService.record_failed_attempt(
            db, user, ip_address=ip_address
        )
        if is_now_locked:
            minutes_remaining = (lock_seconds or 0) // 60 + 1
            return make_error_page(
                f"Account locked due to too many failed login attempts. "
                f"Please try again in {minutes_remaining} minute(s)."
            )
        return make_error_page("Invalid email or password. Please try again.")

    # Reset failed attempts on successful login
    await AccountLockoutService.reset_failed_attempts(db, user)

    # Create session and tokens
    access_token, refresh_token, session = await AuthService.create_session(
        db, user, ip_address=request.client.host, user_agent=request.headers.get("user-agent")
    )

    # SECURITY: Delete the Redis key after successful login (single-use)
    # This prevents replay attacks where a leaked auth_request_id could be reused
    if auth_request_id:
        try:
            await redis.delete(f"oauth:pre_login:{auth_request_id}")
        except Exception:
            pass  # Best-effort cleanup; the key has a TTL anyway

    # If the OAuth context was unrecoverable (Redis expired AND we couldn't
    # reconstruct from the OAuthClient registration), render an explicit
    # "session expired" page instead of silently redirecting to JSON `/`.
    # This was the long-standing UX bug where Sign In appeared to do nothing.
    if redirect_branch in ("redis_miss_no_recovery", "redis_miss_parse_error") and (
        not auth_request_id or safe_next == "/"
    ):
        expired_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign-in session expired - Janua</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex; align-items: center; justify-content: center;
            padding: 20px;
        }}
        .container {{
            background: white; border-radius: 16px; padding: 40px;
            width: 100%; max-width: 440px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{ color: #333; font-size: 22px; margin-bottom: 16px; }}
        p {{ color: #555; line-height: 1.55; margin-bottom: 12px; }}
        .footer {{ text-align: center; margin-top: 24px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>&#128274; Sign-in session expired</h1>
        <p>Your sign-in session for <strong>{html.escape(client_name or "this application")}</strong> expired before you completed login. Your credentials were accepted, but the OAuth flow can't continue from here.</p>
        <p>Return to the application and start sign-in again.</p>
        <div class="footer">Powered by Janua &bull; Secure Authentication</div>
    </div>
</body>
</html>
"""
        # Cookies are still set so the next OAuth /authorize will short-circuit
        # via get_user_from_cookie_or_header — the user won't have to re-type
        # their password.
        response = HTMLResponse(content=expired_html, status_code=200)
    else:
        # SECURITY: Create redirect response with validated URL (CWE-601 mitigation)
        # For OAuth flows, safe_next is the freshly-reconstructed authorize URL.
        # For non-OAuth flows, safe_next was validated against the redirect allowlist.
        response = RedirectResponse(url=safe_next, status_code=302)

    # Build cookie kwargs — include domain for cross-subdomain SSO when configured
    access_cookie_kwargs: dict = {
        "httponly": False,  # Allow JS access for API calls
        "samesite": "lax",
        "secure": True,  # HTTPS only
        "max_age": 3600,  # 1 hour
    }
    if settings.COOKIE_DOMAIN:
        access_cookie_kwargs["domain"] = settings.COOKIE_DOMAIN

    refresh_cookie_kwargs: dict = {
        "httponly": True,  # HttpOnly for security
        "samesite": "lax",
        "secure": True,
        "max_age": 604800,  # 7 days
    }
    if settings.COOKIE_DOMAIN:
        refresh_cookie_kwargs["domain"] = settings.COOKIE_DOMAIN

    response.set_cookie(key="janua_access_token", value=access_token, **access_cookie_kwargs)
    response.set_cookie(key="janua_refresh_token", value=refresh_token, **refresh_cookie_kwargs)

    return response


# Alias for /signup (the TypeScript SDK and @janua/ui components post to /register)
@router.post("/register", response_model=SignInResponse)
@limiter.limit("3/minute")  # Same strict rate limiting as /signup
async def register(
    request: Request,
    signup_data: SignUpRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Create a new user account (alias for /signup)"""
    return await sign_up(request, signup_data, background_tasks, db)


# Alias for /signin (tests expect /login)
@router.post("/login", response_model=SignInResponse)
@limiter.limit("5/minute")
async def login(credentials: SignInRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticate user and get tokens (alias for /signin)"""
    return await sign_in(credentials, request, db)


# Alias for /signout (tests expect /logout)
@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Sign out current session (alias for /signout)"""
    return await sign_out(current_user, credentials, db)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh access token using refresh token"""
    result = await AuthService.refresh_tokens(db, request.refresh_token)

    if not result:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    access_token, refresh_token = result

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/signout")
async def sign_out(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Sign out current session"""
    token = credentials.credentials
    payload = await AuthService.verify_token(token, token_type="access")

    if payload:
        # Blacklist the access token JTI
        try:
            from app.core.jwt_manager import jwt_manager
            await jwt_manager.blacklist_token(payload["jti"], "access")
        except Exception:
            pass  # Best-effort blacklisting

        # Find and revoke session in DB
        try:
            result = await db.execute(
                select(UserSession).where(UserSession.access_token_jti == payload["jti"])
            )
            session = result.scalar_one_or_none()

            if session:
                session.revoked = True
                # Also blacklist the refresh token
                if session.refresh_token_jti:
                    try:
                        from app.core.jwt_manager import jwt_manager
                        await jwt_manager.blacklist_token(session.refresh_token_jti, "refresh")
                    except Exception:
                        pass
                await db.commit()
        except Exception:
            pass  # Best-effort session revocation

    # Log activity (best-effort, don't fail logout)
    try:
        await log_activity(db, str(current_user.id), "signout", {})
    except Exception:
        pass
    try:
        await log_audit_event(db, str(current_user.id), "signout", {})
    except Exception:
        pass

    return {"message": "Successfully signed out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        email_verified=current_user.email_verified,
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        profile_image_url=current_user.profile_image_url,
        is_admin=getattr(current_user, "is_admin", False),
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_sign_in_at=current_user.last_sign_in_at,
    )


async def _dispatch_password_reset(
    email: str,
    redirect_base_raw: Optional[str],
    background_tasks: BackgroundTasks,
    db,
) -> None:
    """Create a reset token and queue the email — shared by the JSON endpoint
    and the hosted forgot-password form. Does nothing when no ACTIVE user
    matches: enumeration safety is both callers' contract, so absence must be
    indistinguishable from success at every transport."""
    result = await db.execute(
        select(User).where(User.email == email, User.status == UserStatus.ACTIVE)
    )
    user = result.scalar_one_or_none()
    if not (user and settings.EMAIL_ENABLED):
        return

    reset_token = secrets.token_urlsafe(32)
    reset = PasswordReset(
        user_id=user.id, token=reset_token, expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    db.add(reset)
    await db.commit()

    # Only a pre-registered product page may receive the token.
    redirect_base = None
    if redirect_base_raw:
        allowed = {
            origin.strip()
            for origin in (settings.PASSWORD_RESET_REDIRECT_ORIGINS or "").split(",")
            if origin.strip()
        }
        if redirect_base_raw in allowed:
            redirect_base = redirect_base_raw

    # Send email in background via the REAL mailer, with THE token that
    # /password/reset validates. The previous dispatch pointed at a
    # placebo EmailService (app.services.email logs and returns True —
    # nothing was ever sent) and even misnamed its method
    # (send_password_reset_email vs the placebo's send_password_reset),
    # while the SMTP-capable service generated a DIFFERENT token for the
    # URL than the one stored in password_resets. Recovery could never
    # complete by construction.
    background_tasks.add_task(
        send_password_reset_email_task,
        user.email,
        reset_token,
        redirect_base,
        locale=getattr(user, "locale", None),
    )


async def _consume_password_reset(token: str, new_password: str, db) -> tuple[bool, str]:
    """Validate a reset token and set the new password — shared by the JSON
    endpoint and the hosted reset form. Token check precedes policy check so a
    dead link surfaces before a weak password does."""
    result = await db.execute(
        select(PasswordReset).where(
            PasswordReset.token == token,
            PasswordReset.used == False,
            PasswordReset.expires_at > datetime.utcnow(),
        )
    )
    reset = result.scalar_one_or_none()

    if not reset:
        return False, "Invalid or expired reset token"

    valid, message = AuthService.validate_password_strength(new_password)
    if not valid:
        return False, message

    user = await db.get(User, reset.user_id)
    user.password_hash = AuthService.hash_password(new_password)
    # Completing a reset proves control of the mailbox the token was mailed
    # to — the same evidence the magic-link flow auto-verifies on. Without
    # this, an unverified account recovers its password only to be blocked
    # minutes later at the authorize endpoint's REQUIRE_EMAIL_VERIFICATION
    # gate (observed live 2026-08-13).
    user.email_verified = True

    reset.used = True
    reset.used_at = datetime.utcnow()

    await db.commit()

    await log_activity(db, str(user.id), "password_reset", {})
    await log_audit_event(db, str(user.id), "password_reset", {})

    return True, "Password successfully reset"


@router.post("/password/forgot")
@limiter.limit("3/hour")  # Strict rate limiting for password reset requests
async def forgot_password(
    request: Request,
    forgot_data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Request password reset email"""
    await _dispatch_password_reset(
        forgot_data.email, forgot_data.redirect_base, background_tasks, db
    )
    # Don't reveal if user exists
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/password/reset")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password with token"""
    ok, message = await _consume_password_reset(request.token, request.new_password, db)
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


def _recovery_page_html(body: str) -> str:
    """Visual shell for the hosted recovery pages — same look as the hosted
    login page (whose CSS is inlined per-page by existing convention)."""
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Password recovery - Janua</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .login-container {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            width: 100%;
            max-width: 400px;
        }}
        .logo {{ text-align: center; margin-bottom: 30px; }}
        .logo h1 {{ font-size: 28px; color: #333; margin-bottom: 8px; }}
        .logo p {{ color: #666; font-size: 14px; }}
        .lead {{ color: #666; font-size: 14px; margin-bottom: 20px; }}
        .lead a {{ color: #667eea; }}
        .hint {{ color: #666; font-size: 12px; margin: -8px 0 16px; }}
        .form-group {{ margin-bottom: 20px; }}
        label {{
            display: block;
            margin-bottom: 6px;
            color: #333;
            font-weight: 500;
            font-size: 14px;
        }}
        input[type="email"], input[type="password"] {{
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e1e5eb;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.2s, box-shadow 0.2s;
        }}
        input:focus {{
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}
        button {{
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }}
        .alert-error {{
            background: #fee;
            color: #c00;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        .alert-ok {{
            background: #e8f5ee;
            color: #14683c;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        .footer {{
            text-align: center;
            margin-top: 24px;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="login-container">
{body}
    </div>
</body>
</html>
"""


def _reset_form_body(token: str, error: Optional[str] = None) -> str:
    import html as html_mod

    error_html = f'<div class="alert-error">{html_mod.escape(error)}</div>' if error else ""
    return f"""
        <div class="logo"><h1>&#128274; Janua</h1><p>Choose a new password</p></div>
        {error_html}
        <form method="POST" action="/api/v1/auth/reset-password-form">
            <input type="hidden" name="token" value="{html_mod.escape(token)}">
            <div class="form-group">
                <label for="new_password">New password</label>
                <input type="password" id="new_password" name="new_password" required autocomplete="new-password" autofocus>
            </div>
            <div class="form-group">
                <label for="confirm_password">Confirm new password</label>
                <input type="password" id="confirm_password" name="confirm_password" required autocomplete="new-password">
            </div>
            <p class="hint">At least 12 characters, with an uppercase letter, a lowercase letter, a number, and a special character.</p>
            <button type="submit">Set new password</button>
        </form>
        <div class="footer">Powered by Janua &bull; Secure Authentication</div>
    """


@router.get("/forgot-password")
async def forgot_password_page():
    """Hosted forgot-password page, linked from the hosted login page.

    Before this page existed the hosted login form offered no recovery
    affordance at all — a user who forgot their password had nowhere to go
    (observed live 2026-08-13)."""
    from fastapi.responses import HTMLResponse

    body = """
        <div class="logo"><h1>&#128274; Janua</h1><p>Password recovery</p></div>
        <p class="lead">Enter your account email and we&#39;ll send you a reset link. The link works once and expires in 1 hour.</p>
        <form method="POST" action="/api/v1/auth/forgot-password-form">
            <div class="form-group">
                <label for="email">Email</label>
                <input type="email" id="email" name="email" required autocomplete="email" autofocus>
            </div>
            <button type="submit">Send reset link</button>
        </form>
        <div class="footer">Powered by Janua &bull; Secure Authentication</div>
    """
    return HTMLResponse(content=_recovery_page_html(body))


@router.post("/forgot-password-form")
@limiter.limit("3/hour")  # Same budget as the JSON endpoint — one recovery surface
async def forgot_password_form(
    request: Request,
    background_tasks: BackgroundTasks,
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    """Browser half of /password/forgot: same dispatch, rendered as a page.
    No redirect_base — the emailed link lands on the API-hosted reset page."""
    import html as html_mod

    from fastapi.responses import HTMLResponse

    await _dispatch_password_reset(email, None, background_tasks, db)
    body = f"""
        <div class="logo"><h1>&#128274; Janua</h1><p>Password recovery</p></div>
        <div class="alert-ok">If an account exists for <strong>{html_mod.escape(email)}</strong>, a reset link is on its way. It works once and expires in 1 hour.</div>
        <p class="lead">Didn&#39;t get it? Check spam, or <a href="/api/v1/auth/forgot-password">try again</a> in a few minutes.</p>
        <div class="footer">Powered by Janua &bull; Secure Authentication</div>
    """
    return HTMLResponse(content=_recovery_page_html(body))


@router.get("/reset-password")
async def reset_password_page(token: Optional[str] = None):
    """Hosted reset page — the reset email's default landing since 2026-08-13.

    The previous default pointed at the product frontend, whose
    /auth/reset-password route sits behind the login wall: a user who cannot
    log in (the entire premise of a reset) was bounced to /login and the
    token was lost. This page is served by the API itself, on the same host
    that mints the token, so it can never be auth-walled away."""
    from fastapi.responses import HTMLResponse

    if not token:
        body = """
        <div class="logo"><h1>&#128274; Janua</h1><p>Choose a new password</p></div>
        <div class="alert-error">This page needs the link from your reset email. Open the most recent password-reset email and use its button or URL.</div>
        <p class="lead">Need a new link? <a href="/api/v1/auth/forgot-password">Request one here</a>.</p>
        <div class="footer">Powered by Janua &bull; Secure Authentication</div>
        """
        return HTMLResponse(content=_recovery_page_html(body), status_code=400)
    return HTMLResponse(content=_recovery_page_html(_reset_form_body(token)))


@router.post("/reset-password-form")
@limiter.limit("10/hour")
async def reset_password_form(
    request: Request,
    token: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Browser half of /password/reset: identical token validation and policy
    via _consume_password_reset, rendered as pages instead of JSON."""
    from fastapi.responses import HTMLResponse

    if new_password != confirm_password:
        return HTMLResponse(
            content=_recovery_page_html(
                _reset_form_body(token, "The two passwords don't match.")
            ),
            status_code=400,
        )

    ok, message = await _consume_password_reset(token, new_password, db)
    if ok:
        body = """
        <div class="logo"><h1>&#128274; Janua</h1><p>Password updated</p></div>
        <div class="alert-ok">Your password has been updated. Close this tab and sign in again from the application you came from.</div>
        <div class="footer">Powered by Janua &bull; Secure Authentication</div>
        """
        return HTMLResponse(content=_recovery_page_html(body))

    if message == "Invalid or expired reset token":
        body = """
        <div class="logo"><h1>&#128274; Janua</h1><p>Choose a new password</p></div>
        <div class="alert-error">This reset link is invalid or has expired (links work once and last 1 hour).</div>
        <p class="lead">Request a fresh one <a href="/api/v1/auth/forgot-password">here</a>.</p>
        <div class="footer">Powered by Janua &bull; Secure Authentication</div>
        """
        return HTMLResponse(content=_recovery_page_html(body), status_code=400)

    # Policy rejection — the token is still live, re-render the form with the
    # policy message so the user can try a stronger password on the same link.
    return HTMLResponse(
        content=_recovery_page_html(_reset_form_body(token, message)), status_code=400
    )


@router.post("/password/change")
async def change_password(
    request: ChangePasswordRequest,
    req: Request,
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Change password for authenticated user"""
    # Verify current password
    if not AuthService.verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Validate new password
    valid, message = AuthService.validate_password_strength(request.new_password)
    if not valid:
        raise HTTPException(status_code=400, detail=message)

    # Update password
    current_user.password_hash = AuthService.hash_password(request.new_password)
    await db.commit()

    # SECURITY: Revoke all sessions except current one to prevent stolen session reuse
    # Extract current session ID from the JWT claims
    current_session_id = None
    try:
        token = credentials.credentials
        payload = await AuthService.verify_token(token, token_type="access")
        if payload:
            # Find current session by access token JTI
            result = await db.execute(
                select(UserSession).where(UserSession.access_token_jti == payload.get("jti"))
            )
            current_session = result.scalar_one_or_none()
            if current_session:
                current_session_id = current_session.id
    except Exception:
        pass  # If we can't determine current session, revoke all

    await AuthService.invalidate_user_sessions(
        db, current_user.id, exclude_session_id=current_session_id
    )

    # Log activity
    await log_activity(db, str(current_user.id), "password_change", {}, req)
    await log_audit_event(db, str(current_user.id), "password_change", {}, req)

    return {"message": "Password successfully changed"}


# Alias for /email/verify (tests expect /verify-email)
@router.post("/verify-email")
async def verify_email_alias(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify email with token (alias for /email/verify)"""
    return await verify_email(request, db)


@router.post("/email/verify")
async def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify email with token"""
    # Find valid verification token
    result = await db.execute(
        select(EmailVerification).where(
            EmailVerification.token == request.token,
            EmailVerification.verified == False,
            EmailVerification.expires_at > datetime.utcnow(),
        )
    )
    verification = result.scalar_one_or_none()

    if not verification:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    # Mark email as verified
    user = await db.get(User, verification.user_id)
    user.email_verified = True
    user.email_verified_at = datetime.utcnow()

    # Mark verification as used
    verification.verified = True
    verification.verified_at = datetime.utcnow()

    await db.commit()

    # Log activity
    await log_activity(db, str(user.id), "email_verified", {})
    await log_audit_event(db, str(user.id), "email_verified", {})

    return {"message": "Email successfully verified"}


@router.post("/email/resend-verification")
@limiter.limit("5/hour")  # Rate limiting for email verification requests
async def resend_verification_email(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resend verification email"""
    if current_user.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    if not settings.EMAIL_ENABLED:
        raise HTTPException(status_code=400, detail="Email service not configured")

    # Create new verification token
    verification_token = secrets.token_urlsafe(32)
    verification = EmailVerification(
        user_id=current_user.id,
        token=verification_token,
        email=current_user.email,
        expires_at=datetime.utcnow() + timedelta(hours=48),
    )
    db.add(verification)
    await db.commit()

    # Send email in background
    background_tasks.add_task(
        send_verification_email_task,
        current_user.email,
        verification_token,
        locale=getattr(current_user, "locale", None),
    )

    return {"message": "Verification email sent"}


@router.post("/magic-link")
@limiter.limit("5/hour")  # Rate limiting for magic link requests
async def send_magic_link(
    request: Request,
    magic_link_data: MagicLinkRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Send magic link for passwordless signin"""
    if not settings.ENABLE_MAGIC_LINKS:
        raise HTTPException(status_code=403, detail="Magic links are disabled")

    if not settings.EMAIL_ENABLED:
        raise HTTPException(status_code=400, detail="Email service not configured")

    # Find or create user
    result = await db.execute(
        select(User).where(User.email == magic_link_data.email, User.status == UserStatus.ACTIVE)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Create user without password for magic link only
        user = User(
            email=magic_link_data.email,
            email_verified=True,  # Auto-verify for magic link users
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # SECURITY: Validate the redirect URL to prevent open redirect attacks
    safe_redirect_url = None
    if magic_link_data.redirect_url:
        safe_redirect_url = validate_redirect_url(magic_link_data.redirect_url, default_url=None)
        # If validation failed (returned None), we simply won't include a redirect

    # Create magic link token
    magic_token = secrets.token_urlsafe(32)
    magic_link = MagicLink(
        user_id=user.id,
        token=magic_token,
        redirect_url=safe_redirect_url,  # Use validated URL
        expires_at=datetime.utcnow() + timedelta(minutes=15),
    )
    db.add(magic_link)
    await db.commit()

    # Send email in background
    background_tasks.add_task(
        send_magic_link_email_task,
        user.email,
        magic_token,
        safe_redirect_url,
        locale=getattr(user, "locale", None),
    )

    return {"message": "Magic link sent to email"}


@router.get("/magic-link/callback")
async def magic_link_callback(
    token: Optional[str] = None,
    req: Request = None,
    db: Session = Depends(get_db),
):
    """Land a clicked magic link and forward to the product with a session.

    A link in an email is a GET, and only Janua can trade the one-time magic
    token for a session — so without this route the whole passwordless flow
    had no door to knock on: `/magic-link/verify` is a POST returning JSON,
    which no mail client can reach. Products (nauta's /portal/verify) expect
    to be handed the access token on the query string; that contract is why
    the token travels this way rather than in a body.
    """
    from fastapi.responses import HTMLResponse, RedirectResponse

    def _expired_page() -> HTMLResponse:
        return HTMLResponse(
            content=_recovery_page_html(
                '<h1>🔗 Link expired</h1>'
                '<p class="lede">Magic links work once and expire after 15 minutes.</p>'
                '<p>Request a new one from the page you were signing in to.</p>'
            ),
            status_code=400,
        )

    if not token:
        return _expired_page()

    result = await db.execute(
        select(MagicLink).where(
            MagicLink.token == token,
            MagicLink.used_at.is_(None),
            MagicLink.expires_at > datetime.utcnow(),
        )
    )
    magic_link = result.scalar_one_or_none()
    if not magic_link:
        return _expired_page()

    result = await db.execute(
        select(User).where(User.id == magic_link.user_id, User.status == UserStatus.ACTIVE)
    )
    user = result.scalar_one_or_none()
    if not user:
        return _expired_page()

    # Burn the token before minting anything: a link that has produced a
    # session must never produce a second one.
    magic_link.used_at = datetime.utcnow()

    access_token, _refresh_token, _session = await AuthService.create_session(
        db, user, ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
    )

    # Signing in by emailed link proves control of the mailbox.
    if not user.email_verified:
        user.email_verified = True
    await db.commit()

    await log_activity(db, str(user.id), "signin", {"method": "magic_link"}, req)

    # Re-validate at redemption: the allowlist may have changed since the link
    # was issued, and this is the moment a credential is handed over.
    destination = validate_redirect_url(magic_link.redirect_url, default_url=None)
    if not destination:
        return HTMLResponse(
            content=_recovery_page_html(
                '<h1>✅ Signed in</h1>'
                '<p class="lede">Your link was valid, but its destination is no longer '
                'an allowed address, so we did not forward you.</p>'
                '<p>Return to the site you were signing in to and try again.</p>'
            ),
            status_code=400,
        )

    separator = "&" if "?" in destination else "?"
    return RedirectResponse(url=f"{destination}{separator}token={access_token}", status_code=302)


@router.post("/magic-link/verify", response_model=SignInResponse)
async def verify_magic_link(
    request: VerifyMagicLinkRequest, req: Request, db: Session = Depends(get_db)
):
    """Sign in with magic link token"""
    # Find valid magic link
    result = await db.execute(
        select(MagicLink).where(
            MagicLink.token == request.token,
            MagicLink.used_at.is_(None),
            MagicLink.expires_at > datetime.utcnow(),
        )
    )
    magic_link = result.scalar_one_or_none()

    if not magic_link:
        raise HTTPException(status_code=400, detail="Invalid or expired magic link")

    # Get user
    result = await db.execute(
        select(User).where(User.id == magic_link.user_id, User.status == UserStatus.ACTIVE)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    # Mark magic link as used
    magic_link.used_at = datetime.utcnow()

    # Create session
    access_token, refresh_token, session = await AuthService.create_session(
        db, user, ip_address=req.client.host, user_agent=req.headers.get("user-agent")
    )

    # Log activity
    await log_activity(db, str(user.id), "signin", {"method": "magic_link"}, req)

    return SignInResponse(
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            email_verified=user.email_verified,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            profile_image_url=user.profile_image_url,
            is_admin=getattr(user, "is_admin", False),
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_sign_in_at=user.last_sign_in_at,
        ),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )
