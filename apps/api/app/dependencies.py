"""
Shared dependencies for FastAPI routes and services

Ensures proper module structure for Railway deployment
"""

from fastapi import Depends, HTTPException
from typing import Optional
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.redis import get_redis
from .models import User, UserStatus, Organization, OrganizationMember
from app.services.auth import AuthService

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), 
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    
    # Decode token
    payload = AuthService.decode_token(token, token_type='access')
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Validate session
    session_valid = await AuthService.validate_session(db, payload['jti'])
    if not session_valid:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Get user using async session
    result = await db.execute(
        select(User).where(
            User.id == payload['sub'],
            User.status == UserStatus.ACTIVE
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current authenticated user from JWT token, returns None if not authenticated"""
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require user to be an admin"""
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user


async def require_org_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Require user to be an organization admin"""
    # Check if user has admin role in any organization using async session
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role.in_(['admin', 'owner'])
        )
    )
    org_member = result.scalar_one_or_none()

    if not org_member:
        raise HTTPException(status_code=403, detail="Organization admin privileges required")

    return current_user