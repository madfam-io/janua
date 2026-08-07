"""
Type definitions for the Janua Python SDK.

This module contains all the data models and type definitions used throughout
the SDK, implemented using Pydantic for validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, HttpUrl, ConfigDict


# ====================
# Enumerations
# ====================

class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"
    PENDING = "pending"


class OrganizationRole(str, Enum):
    """Organization member roles."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class OAuthProvider(str, Enum):
    """Supported OAuth providers."""
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"
    DISCORD = "discord"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    APPLE = "apple"


class WebhookEventType(str, Enum):
    """Webhook event types."""
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_SIGNED_IN = "user.signed_in"
    USER_SIGNED_OUT = "user.signed_out"
    SESSION_CREATED = "session.created"
    SESSION_EXPIRED = "session.expired"
    ORGANIZATION_CREATED = "organization.created"
    ORGANIZATION_UPDATED = "organization.updated"
    ORGANIZATION_DELETED = "organization.deleted"
    ORGANIZATION_MEMBER_ADDED = "organization.member_added"
    ORGANIZATION_MEMBER_REMOVED = "organization.member_removed"
    ORGANIZATION_MEMBER_UPDATED = "organization.member_updated"


class SessionStatus(str, Enum):
    """Session status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


# ====================
# Base Models
# ====================

class BaseResponse(BaseModel):
    """Base response model with common fields."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(10, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: Optional[str] = Field("asc", pattern="^(asc|desc)$")


class PaginatedResponse(BaseResponse):
    """Base paginated response."""
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page")
    limit: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Has next page")
    has_prev: bool = Field(..., description="Has previous page")


# ====================
# User Models
# ====================

class User(BaseResponse):
    """User model."""
    id: UUID
    email: EmailStr
    email_verified: bool = False
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None
    phone_number: Optional[str] = None
    phone_verified: bool = False
    status: UserStatus = UserStatus.ACTIVE
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    last_sign_in_at: Optional[datetime] = None
    mfa_enabled: bool = False
    passkeys_enabled: bool = False
    oauth_accounts: List["OAuthAccount"] = Field(default_factory=list)
    # Flat list of linked provider names, as returned by the API alongside the
    # richer oauth_accounts (see the `oauth_providers: List[str]` field on the
    # server's user response in apps/api/app/routers/v1/admin.py, and the
    # matching field in packages/typescript-sdk/src/admin.ts).
    oauth_providers: List[str] = Field(default_factory=list)


class UserUpdateRequest(BaseModel):
    """User update request."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None
    phone_number: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class UserListResponse(PaginatedResponse):
    """User list response."""
    users: List[User]


# ====================
# Authentication Models
# ====================

class SignUpRequest(BaseModel):
    """Sign up request."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    invite_code: Optional[str] = None


class SignInRequest(BaseModel):
    """Sign in request."""
    email: EmailStr
    password: str
    remember_me: bool = False


class TokenResponse(BaseResponse):
    """Token response."""
    access_token: str
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int
    scope: Optional[str] = None


# Alias for compatibility
AuthTokens = TokenResponse


class AuthResponse(BaseResponse):
    """Authentication response."""
    user: User
    tokens: TokenResponse
    session: Optional["Session"] = None


class SignInResponse(AuthResponse):
    """Sign in response with user and tokens."""


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""
    email: EmailStr
    redirect_url: Optional[HttpUrl] = None


class ResetPasswordRequest(BaseModel):
    """Reset password request."""
    token: str
    new_password: str = Field(..., min_length=8)


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class MagicLinkRequest(BaseModel):
    """Magic link request."""
    email: EmailStr
    redirect_url: Optional[HttpUrl] = None
    expires_in: Optional[int] = Field(3600, ge=300, le=86400, description="Expiration in seconds")


# ====================
# Session Models
# ====================

class Session(BaseResponse):
    """Session model.

    `token`, `updated_at` and `last_activity_at` are optional: the server's
    SessionResponse (apps/api/app/routers/v1/sessions.py) has no `token` and no
    `updated_at` at all — a session's tokens are carried in the sibling `tokens`
    object of the sign-in response, not inside `session` — and the sign-in
    payload omits `last_activity_at`. Requiring them made every real response
    fail validation.
    """
    id: UUID
    user_id: UUID
    token: Optional[str] = None
    status: SessionStatus = SessionStatus.ACTIVE
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_info: Optional[Dict[str, Any]] = None
    location: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    expires_at: datetime
    last_activity_at: Optional[datetime] = None


class SessionListResponse(PaginatedResponse):
    """Session list response."""
    sessions: List[Session]


# ====================
# Organization Models
# ====================

class Organization(BaseResponse):
    """Organization model."""
    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    logo_url: Optional[HttpUrl] = None
    website_url: Optional[HttpUrl] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    member_count: int = 0
    owner_id: UUID


class OrganizationMember(BaseResponse):
    """Organization member model."""
    id: UUID
    organization_id: UUID
    user_id: UUID
    user: Optional[User] = None
    role: OrganizationRole
    permissions: List[str] = Field(default_factory=list)
    joined_at: datetime
    updated_at: datetime


class OrganizationInvitation(BaseResponse):
    """Organization invitation model."""
    id: UUID
    organization_id: UUID
    organization: Optional[Organization] = None
    email: EmailStr
    role: OrganizationRole
    invited_by_id: UUID
    invited_by: Optional[User] = None
    accepted: bool = False
    expires_at: datetime
    created_at: datetime
    accepted_at: Optional[datetime] = None


class OrganizationCreateRequest(BaseModel):
    """Organization create request."""
    name: str = Field(..., min_length=1, max_length=100)
    slug: Optional[str] = Field(None, min_length=3, max_length=50, pattern="^[a-z0-9-]+$")
    description: Optional[str] = None
    logo_url: Optional[HttpUrl] = None
    website_url: Optional[HttpUrl] = None
    metadata: Optional[Dict[str, Any]] = None


class OrganizationUpdateRequest(BaseModel):
    """Organization update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    logo_url: Optional[HttpUrl] = None
    website_url: Optional[HttpUrl] = None
    metadata: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None


class OrganizationInviteRequest(BaseModel):
    """Organization invite request."""
    email: EmailStr
    role: OrganizationRole = OrganizationRole.MEMBER
    send_email: bool = True


class OrganizationListResponse(PaginatedResponse):
    """Organization list response."""
    organizations: List[Organization]


class OrganizationMemberListResponse(PaginatedResponse):
    """Organization member list response."""
    members: List[OrganizationMember]


# ====================
# MFA Models
# ====================

class MFAStatusResponse(BaseResponse):
    """MFA status response."""
    enabled: bool
    methods: List[str] = Field(default_factory=list)
    backup_codes_remaining: int = 0
    last_verified_at: Optional[datetime] = None


class MFAEnableRequest(BaseModel):
    """MFA enable request."""
    method: str = Field("totp", description="MFA method to enable")
    password: str = Field(..., description="Current password for verification")


class MFAEnableResponse(BaseResponse):
    """MFA enable response."""
    secret: str
    qr_code: str
    backup_codes: List[str]
    recovery_codes: List[str]


class MFAVerifyRequest(BaseModel):
    """MFA verify request."""
    code: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]+$")
    method: str = Field("totp")


class MFADisableRequest(BaseModel):
    """MFA disable request."""
    password: str
    code: Optional[str] = Field(None, min_length=6, max_length=6)


# ====================
# Passkey Models
# ====================

class PasskeyResponse(BaseResponse):
    """Passkey response."""
    id: UUID
    user_id: UUID
    name: str
    credential_id: str
    public_key: str
    sign_count: int
    transports: List[str]
    created_at: datetime
    last_used_at: Optional[datetime] = None


class PasskeyRegisterRequest(BaseModel):
    """Passkey register request."""
    name: str = Field(..., min_length=1, max_length=100)
    credential: Dict[str, Any]


class PasskeyUpdateRequest(BaseModel):
    """Passkey update request."""
    name: str = Field(..., min_length=1, max_length=100)


class PasskeyListResponse(PaginatedResponse):
    """Passkey list response."""
    passkeys: List[PasskeyResponse]


# ====================
# Webhook Models
# ====================

class WebhookEndpoint(BaseResponse):
    """Webhook endpoint model."""
    id: UUID
    url: HttpUrl
    description: Optional[str] = None
    events: List[WebhookEventType]
    enabled: bool = True
    secret: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    failure_count: int = 0
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None


class WebhookEndpointCreateRequest(BaseModel):
    """Webhook endpoint create request."""
    url: HttpUrl
    events: List[WebhookEventType]
    description: Optional[str] = None
    enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None


class WebhookEndpointUpdateRequest(BaseModel):
    """Webhook endpoint update request."""
    url: Optional[HttpUrl] = None
    events: Optional[List[WebhookEventType]] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class WebhookEvent(BaseResponse):
    """Webhook event model."""
    id: UUID
    endpoint_id: UUID
    event_type: WebhookEventType
    payload: Dict[str, Any]
    created_at: datetime
    delivered_at: Optional[datetime] = None
    attempts: int = 0
    status: str
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    next_retry_at: Optional[datetime] = None


class WebhookDelivery(BaseResponse):
    """Webhook delivery model."""
    id: UUID
    event_id: UUID
    endpoint_id: UUID
    status: str
    attempt: int
    response_status: Optional[int] = None
    response_headers: Optional[Dict[str, str]] = None
    response_body: Optional[str] = None
    error: Optional[str] = None
    delivered_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


class WebhookEndpointListResponse(PaginatedResponse):
    """Webhook endpoint list response."""
    endpoints: List[WebhookEndpoint]


class WebhookEventListResponse(PaginatedResponse):
    """Webhook event list response."""
    events: List[WebhookEvent]


# ====================
# Admin Models
# ====================

class AdminStatsResponse(BaseResponse):
    """Admin statistics response."""
    total_users: int
    active_users: int
    total_organizations: int
    total_sessions: int
    active_sessions: int
    mfa_enabled_users: int
    passkey_enabled_users: int
    oauth_connected_users: int
    period_start: datetime
    period_end: datetime
    user_growth: float
    organization_growth: float


class SystemHealthResponse(BaseResponse):
    """System health response."""
    status: str
    version: str
    uptime: int
    database_status: str
    cache_status: str
    queue_status: str
    storage_status: str
    services: Dict[str, str]
    last_checked_at: datetime


# ====================
# OAuth Models
# ====================

class OAuthProviderInfo(BaseResponse):
    """OAuth provider information."""
    provider: OAuthProvider
    enabled: bool
    client_id: str
    authorization_url: str
    token_url: str
    scopes: List[str]


class OAuthAccount(BaseResponse):
    """OAuth account model."""
    id: UUID
    user_id: UUID
    provider: OAuthProvider
    provider_user_id: str
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class OAuthAuthorizeRequest(BaseModel):
    """OAuth authorize request."""
    provider: OAuthProvider
    redirect_url: HttpUrl
    state: Optional[str] = None
    code_challenge: Optional[str] = None


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request."""
    provider: OAuthProvider
    code: str
    state: Optional[str] = None
    code_verifier: Optional[str] = None


# ====================
# Client Configuration
# ====================

class JanuaConfig(BaseModel):
    """Resolved client configuration.

    Built once by :class:`janua.client.JanuaClient` and handed to every service
    client. Mutable: ``JanuaClient.set_api_key`` / ``set_environment`` /
    ``enable_debug`` / ``disable_debug`` assign to it after construction.
    """
    api_key: str = Field(..., description="API key used to authenticate requests")
    base_url: str = Field(..., description="Base URL of the Janua API")
    timeout: float = Field(30.0, description="Per-request timeout in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts per request")
    environment: str = Field("production", description="Deployment environment")
    debug: bool = Field(False, description="Emit verbose client-side diagnostics")


# ====================
# Generic List Response
# ====================

T = TypeVar("T")


class ListResponse(BaseResponse, Generic[T]):
    """Offset-paginated collection returned by the list endpoints.

    Distinct from :class:`PaginatedResponse`, which is page-based and carries no
    ``items``. The service clients construct this by subscripting at runtime,
    e.g. ``ListResponse[Organization](items=..., total=..., limit=..., offset=...)``.
    """
    items: List[T] = Field(default_factory=list, description="Items in this page")
    total: int = Field(..., description="Total number of items across all pages")
    limit: int = Field(..., description="Maximum items requested")
    offset: int = Field(..., description="Offset of the first item")


# ====================
# Additional User Models
# ====================

class UserRole(str, Enum):
    """Platform-level user role.

    Distinct from :class:`OrganizationRole`, which scopes a user within a single
    organization. Serialized via ``.value`` into both query params and request
    bodies.
    """
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserProfile(BaseResponse):
    """Extended profile fields for a user."""
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None


class UserPreferences(BaseResponse):
    """Per-user display and notification preferences."""
    language: Optional[str] = None
    timezone: Optional[str] = None
    date_format: Optional[str] = None
    time_format: Optional[str] = Field(None, description="12h or 24h")
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None


# ====================
# Additional Auth Models
# ====================

class EmailVerificationRequest(BaseModel):
    """Request a verification email be (re)sent to an address."""
    email: EmailStr


# `AuthClient.request_password_reset` sends only an address, matching
# ForgotPasswordRequest. Note this is NOT ResetPasswordRequest, whose required
# token/new_password would reject an email-only payload.
PasswordResetRequest = ForgotPasswordRequest


# ====================
# Additional Organization Models
# ====================

class OrganizationSettings(BaseResponse):
    """Organization-wide policy settings."""
    require_mfa: Optional[bool] = None
    allowed_email_domains: Optional[List[str]] = None
    session_duration: Optional[int] = Field(None, description="Session lifetime in seconds")
    password_policy: Optional[Dict[str, Any]] = None


OrganizationInvite = OrganizationInvitation


# ====================
# Additional MFA Models
# ====================

class MFAMethod(str, Enum):
    """A second-factor method.

    Constructed from raw server strings in ``MFAClient.list_methods`` and
    serialized via ``.value`` when sent, so it must remain a ``str`` enum.
    """
    TOTP = "totp"
    SMS = "sms"
    BACKUP_CODES = "backup_codes"


class MFAChallenge(BaseResponse):
    """A pending second-factor challenge awaiting verification."""
    id: str = Field(..., description="Challenge id, passed back to verify_challenge")
    method: Optional[MFAMethod] = None
    user_id: Optional[UUID] = None
    expires_at: Optional[datetime] = None


class TOTPSetup(BaseResponse):
    """Enrollment material for a TOTP authenticator."""
    secret: Optional[str] = Field(None, description="Shared secret in base32")
    qr_code_url: Optional[str] = Field(None, description="Provisioning URI, renderable as a QR code")
    backup_codes: Optional[List[str]] = None


class SMSSetup(BaseResponse):
    """Enrollment state for SMS-delivered codes."""
    phone_number: Optional[str] = None
    verified: bool = Field(False, description="Whether the number has been confirmed")


class BackupCodes(BaseResponse):
    """A set of single-use account recovery codes."""
    codes: List[str] = Field(default_factory=list, description="The codes themselves")
    remaining: Optional[int] = Field(None, description="Unused codes left")


MFASettings = MFAStatusResponse


# ====================
# Additional Passkey Models
# ====================

Passkey = PasskeyResponse


class PasskeyChallenge(BaseResponse):
    """A WebAuthn challenge.

    Serves both ceremonies — registration (creation options) and authentication
    (request options) — so the raw option payload is kept permissive.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra="allow")

    id: str = Field(..., description="Challenge id, passed back to the complete_* call")
    challenge: Optional[str] = None
    options: Optional[Dict[str, Any]] = Field(None, description="Raw WebAuthn options")


class PasskeyCredential(BaseResponse):
    """A WebAuthn credential as returned by the authenticator."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra="allow")

    id: Optional[str] = None
    raw_id: Optional[str] = None
    type: Optional[str] = None
    response: Optional[Dict[str, Any]] = None


# ====================
# Additional Session Models
# ====================

class SessionDevice(BaseResponse):
    """The device a session is bound to."""
    name: Optional[str] = None
    trusted: Optional[bool] = None
    device_type: Optional[str] = None
    os: Optional[str] = None
    browser: Optional[str] = None
    last_seen_at: Optional[datetime] = None


class SessionActivity(BaseResponse):
    """A single audit entry recorded against a session."""
    id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    action: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    location: Optional[str] = None
    created_at: Optional[datetime] = None


# Update forward references
User.model_rebuild()
AuthResponse.model_rebuild()
OrganizationInvitation.model_rebuild()
OrganizationMember.model_rebuild()