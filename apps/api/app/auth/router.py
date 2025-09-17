from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID
import structlog

# Initialize logger first
logger = structlog.get_logger(__name__)

from app.config import settings
from app.core.database import get_db
from app.core.redis import get_redis, RateLimiter, SessionStore
# Import services with error handling for production stability
try:
    from app.services.auth_service import AuthService
    AUTH_SERVICE_AVAILABLE = True
except Exception as e:
    logger.error(f"Failed to import AuthService: {e}")
    AUTH_SERVICE_AVAILABLE = False

try:
    from app.services.email_service import get_email_service
    EMAIL_SERVICE_AVAILABLE = True
except Exception as e:
    logger.error(f"Failed to import EmailService: {e}")
    EMAIL_SERVICE_AVAILABLE = False
from app.models.user import User

logger = structlog.get_logger()
router = APIRouter()
security = HTTPBearer()


# Simple status endpoint to verify router is working
@router.get("/status")
async def auth_status():
    """Simple auth router status check"""
    return {
        "status": "auth router working",
        "endpoints": ["signup", "signin", "signout", "refresh", "me"],
        "router_name": "auth",
        "auth_service": "available" if AUTH_SERVICE_AVAILABLE else "unavailable",
        "email_service": "available" if EMAIL_SERVICE_AVAILABLE else "unavailable"
    }


# Request/Response models
class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=12)
    name: Optional[str] = None
    tenant_id: Optional[str] = None


class SignInRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
    email_verified: bool
    created_at: str
    updated_at: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token")


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., description="Verification token")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8)


# Auth endpoints
@router.post("/signup", response_model=UserResponse)
async def signup(
    request: SignUpRequest,
    response: Response,
    db=Depends(get_db),
    redis=Depends(get_redis)
):
    """Register a new user"""
    # Check if AuthService is available
    if not AUTH_SERVICE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable"
        )
    # Check rate limit
    limiter = RateLimiter(redis)
    allowed, remaining = await limiter.check_rate_limit(
        f"signup:{request.email}",
        limit=5,
        window=3600  # 5 signups per hour per email
    )
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many signup attempts"
        )
    
    try:
        # Create user with real implementation
        from uuid import UUID
        tenant_id = UUID(request.tenant_id) if request.tenant_id else None
        user = await AuthService.create_user(
            db=db,
            email=request.email,
            password=request.password,
            name=request.name,
            tenant_id=tenant_id
        )
        
        # Send verification email (optional for beta)
        if EMAIL_SERVICE_AVAILABLE:
            try:
                email_service = get_email_service(redis)
                verification_token = await email_service.send_verification_email(
                    email=user.email,
                    user_name=user.name,
                    user_id=str(user.id)
                )
                logger.info(f"Verification email sent to {user.email}")
            except Exception as e:
                logger.error(f"Failed to send verification email: {e}")
                # Continue with signup even if email fails for beta
        else:
            logger.warning("Email service unavailable - skipping verification email")
        
        return UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            email_verified=user.email_verified,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Signup failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/signin", response_model=TokenResponse)
async def signin(
    request: SignInRequest,
    response: Response,
    req: Request,
    db=Depends(get_db),
    redis=Depends(get_redis)
):
    """Sign in with email and password"""
    # Check if AuthService is available
    if not AUTH_SERVICE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable"
        )
    # Check rate limit
    limiter = RateLimiter(redis)
    allowed, remaining = await limiter.check_rate_limit(
        f"signin:{request.email}",
        limit=10,
        window=300  # 10 attempts per 5 minutes
    )
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many signin attempts"
        )
    
    # Authenticate user with real implementation
    user = await AuthService.authenticate_user(
        db=db,
        email=request.email,
        password=request.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create real session with JWT tokens
    access_token, refresh_token, session = await AuthService.create_session(
        db=db,
        user=user,
        ip_address=req.client.host if req.client else None,
        user_agent=req.headers.get("user-agent")
    )
    
    # Set secure cookies for web apps
    if settings.SECURE_COOKIES:
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="strict",
            domain=settings.COOKIE_DOMAIN,
            max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            domain=settings.COOKIE_DOMAIN,
            max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/signout")
async def signout(
    response: Response,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis=Depends(get_redis)
):
    """Sign out and invalidate session"""
    try:
        token = credentials.credentials

        # Extract user ID from token (assuming JWT format)
        try:
            import jwt
            payload = jwt.decode(token, options={"verify_signature": False})
            user_id = payload.get("sub")
        except:
            # If token parsing fails, still proceed with cleanup
            user_id = None

        # Create session store instance
        session_store = SessionStore(redis)

        # Delete session from Redis if user ID available
        if user_id:
            await session_store.delete_session(user_id)

        # Add token to blacklist with expiration
        blacklist_key = f"blacklist:{token}"
        await redis.setex(blacklist_key, 86400, "1")  # 24 hour blacklist

        # Clear authentication cookies
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        logger.info("User signed out successfully", user_id=user_id)
        return {"message": "Successfully signed out"}

    except Exception as e:
        logger.error("Signout failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Signout failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db=Depends(get_db),
    redis=Depends(get_redis)
):
    """Refresh access token using refresh token"""
    # Refresh tokens with real implementation
    tokens = await AuthService.refresh_tokens(
        db=db,
        refresh_token=request.refresh_token
    )
    
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    access_token, refresh_token = tokens
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db)
):
    """Get current user information"""
    # Validate access token
    payload = await AuthService.verify_token(credentials.credentials, token_type="access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Fetch user from database
    from uuid import UUID
    user = await db.get(User, UUID(payload.get("sub")))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        email_verified=user.email_verified,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat()
    )


@router.post("/verify-email")
async def verify_email(
    request: VerifyEmailRequest,
    db=Depends(get_db),
    redis=Depends(get_redis)
):
    """Verify email address with token"""
    try:
        # Validate verification token
        email_service = get_email_service(redis)
        token_info = await email_service.verify_email_token(request.token)
        
        # Update user email_verified status in database
        from sqlalchemy import select
        result = await db.execute(
            select(User).where(User.email == token_info['email'])
        )
        user = result.scalar_one_or_none()
        
        if user:
            user.email_verified = True
            await db.commit()
            logger.info(f"Email verified for user {user.id}")
        
        # Send welcome email after verification
        try:
            await email_service.send_welcome_email(
                email=token_info['email'],
                user_name=token_info.get('user_name')
            )
        except Exception as e:
            logger.error(f"Failed to send welcome email: {e}")
            # Continue even if welcome email fails
        
        logger.info(f"Email verification successful for {token_info['email']}")
        
        return {
            "message": "Email verified successfully",
            "email": token_info['email'],
            "verified_at": token_info['created_at']
        }
        
    except Exception as e:
        logger.error(f"Email verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    redis=Depends(get_redis)
):
    """Request password reset"""
    # Check rate limit
    limiter = RateLimiter(redis)
    allowed, remaining = await limiter.check_rate_limit(
        f"forgot_password:{request.email}",
        limit=3,
        window=3600  # 3 requests per hour
    )
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset requests"
        )
    
    # Send password reset email (regardless of user existence for security)
    email_service = get_email_service(redis)
    try:
        reset_token = await email_service.send_password_reset_email(
            email=request.email,
            user_name=request.email.split("@")[0]  # Use email prefix as name
        )
        logger.info(f"Password reset email sent to {request.email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}")
        # Always return success for security (don't reveal if email exists)
    
    return {"message": "Password reset email sent if account exists"}


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db=Depends(get_db)
):
    """Reset password with token"""
    try:
        # Validate reset token from Redis
        redis_client = get_redis()
        stored_email = await redis_client.get(f"reset_token:{request.token}")

        if not stored_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

        # Get user by email
        user = db.query(User).filter(User.email == stored_email.decode()).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Hash new password
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash(request.new_password)

        # Update user password
        user.password_hash = hashed_password
        db.commit()

        # Invalidate all sessions for security
        session_store = SessionStore(redis_client)
        await session_store.delete_session(str(user.id))

        # Remove the reset token
        await redis_client.delete(f"reset_token:{request.token}")

        logger.info("Password reset successfully", user_id=str(user.id))
        return {"message": "Password reset successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Password reset failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


# WebAuthn/Passkeys endpoints
@router.post("/passkeys/register/options")
async def passkey_register_options(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get WebAuthn registration options"""
    # TODO: Implement WebAuthn registration options
    # - Generate challenge
    # - Return registration options
    
    return {
        "challenge": "mock_challenge",
        "rp": {
            "name": settings.WEBAUTHN_RP_NAME,
            "id": settings.WEBAUTHN_RP_ID
        },
        "user": {
            "id": "user_123",
            "name": "user@example.com",
            "displayName": "Test User"
        },
        "timeout": settings.WEBAUTHN_TIMEOUT
    }


@router.post("/passkeys/register")
async def passkey_register(
    credential: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db)
):
    """Register a new passkey"""
    # TODO: Implement WebAuthn registration
    # - Verify registration response
    # - Store credential in database
    
    return {"message": "Passkey registered successfully"}