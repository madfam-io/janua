"""
Enhanced Cache Service for Performance Optimization

Provides multi-layer caching for auth flows with intelligent invalidation:
- Token validation caching (5min TTL)
- User lookup caching (15min TTL)
- Session validation caching (5min TTL)
- Permission caching (15min TTL)
"""

import hashlib
import json
from datetime import timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID

import structlog
from app.core.redis import get_redis

logger = structlog.get_logger()


class CacheService:
    """Enhanced caching service for auth performance optimization"""

    # Cache key prefixes
    PREFIX_TOKEN = "token:validation"
    PREFIX_USER_EMAIL = "user:email"
    PREFIX_USER_ID = "user:id"
    PREFIX_SESSION = "session:token"
    PREFIX_PERMISSIONS = "permissions"

    # Cache TTLs (in seconds)
    TTL_TOKEN = 300  # 5 minutes
    TTL_USER = 900  # 15 minutes
    TTL_SESSION = 300  # 5 minutes
    TTL_PERMISSIONS = 900  # 15 minutes

    def __init__(self):
        self.redis = None

    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis = await get_redis()
            logger.info("CacheService initialized successfully")
        except Exception as e:
            logger.warning("Failed to initialize Redis cache", error=str(e))
            # Graceful degradation - cache operations will be no-ops

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash token for cache key (security + key length)"""
        return hashlib.sha256(token.encode()).hexdigest()[:16]

    @staticmethod
    def _serialize(data: Any) -> str:
        """Serialize data for Redis storage"""
        if isinstance(data, (dict, list)):
            return json.dumps(data, default=str)
        return str(data)

    @staticmethod
    def _deserialize(data: str) -> Any:
        """Deserialize data from Redis"""
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data

    async def _get(self, key: str) -> Optional[Any]:
        """Internal get with error handling"""
        if not self.redis:
            return None
        try:
            value = await self.redis.get(key)
            return self._deserialize(value) if value else None
        except Exception as e:
            logger.warning("Cache get failed", key=key, error=str(e))
            return None

    async def _set(self, key: str, value: Any, ttl: int) -> bool:
        """Internal set with error handling"""
        if not self.redis:
            return False
        try:
            serialized = self._serialize(value)
            await self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning("Cache set failed", key=key, error=str(e))
            return False

    async def _delete(self, key: str) -> bool:
        """Internal delete with error handling"""
        if not self.redis:
            return False
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.warning("Cache delete failed", key=key, error=str(e))
            return False

    # Token Validation Cache
    async def get_token_validation(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get cached token validation result

        Returns:
            {user_id: str, permissions: List[str], expires_at: str} or None
        """
        token_hash = self._hash_token(token)
        key = f"{self.PREFIX_TOKEN}:{token_hash}"
        cached = await self._get(key)

        if cached:
            logger.debug("Token validation cache HIT", token_hash=token_hash)
        else:
            logger.debug("Token validation cache MISS", token_hash=token_hash)

        return cached

    async def set_token_validation(
        self,
        token: str,
        user_id: UUID,
        permissions: List[str],
        expires_at: str
    ) -> bool:
        """Cache token validation result"""
        token_hash = self._hash_token(token)
        key = f"{self.PREFIX_TOKEN}:{token_hash}"

        value = {
            "user_id": str(user_id),
            "permissions": permissions,
            "expires_at": expires_at
        }

        success = await self._set(key, value, self.TTL_TOKEN)
        if success:
            logger.debug("Token validation cached", token_hash=token_hash)
        return success

    async def invalidate_token(self, token: str) -> bool:
        """Invalidate cached token validation"""
        token_hash = self._hash_token(token)
        key = f"{self.PREFIX_TOKEN}:{token_hash}"
        return await self._delete(key)

    # User Lookup Cache
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get cached user by email"""
        key = f"{self.PREFIX_USER_EMAIL}:{email.lower()}"
        cached = await self._get(key)

        if cached:
            logger.debug("User email cache HIT", email=email)
        else:
            logger.debug("User email cache MISS", email=email)

        return cached

    async def get_user_by_id(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get cached user by ID"""
        key = f"{self.PREFIX_USER_ID}:{str(user_id)}"
        cached = await self._get(key)

        if cached:
            logger.debug("User ID cache HIT", user_id=str(user_id))
        else:
            logger.debug("User ID cache MISS", user_id=str(user_id))

        return cached

    async def set_user(self, user_data: Dict[str, Any]) -> bool:
        """
        Cache user data by both email and ID

        Args:
            user_data: Dict with 'id', 'email', and other user fields
        """
        user_id = user_data.get("id")
        email = user_data.get("email")

        if not user_id or not email:
            logger.warning("Cannot cache user without id and email")
            return False

        # Cache by both email and ID for flexible lookups
        email_key = f"{self.PREFIX_USER_EMAIL}:{email.lower()}"
        id_key = f"{self.PREFIX_USER_ID}:{str(user_id)}"

        success_email = await self._set(email_key, user_data, self.TTL_USER)
        success_id = await self._set(id_key, user_data, self.TTL_USER)

        if success_email or success_id:
            logger.debug("User cached", user_id=str(user_id), email=email)

        return success_email or success_id

    async def invalidate_user(self, user_id: UUID, email: str) -> bool:
        """Invalidate cached user by both ID and email"""
        email_key = f"{self.PREFIX_USER_EMAIL}:{email.lower()}"
        id_key = f"{self.PREFIX_USER_ID}:{str(user_id)}"

        success_email = await self._delete(email_key)
        success_id = await self._delete(id_key)

        logger.debug("User cache invalidated", user_id=str(user_id), email=email)
        return success_email or success_id

    # Session Validation Cache
    async def get_session_validation(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get cached session validation result

        Returns:
            {session_id: str, user_id: str, is_active: bool} or None
        """
        token_hash = self._hash_token(token)
        key = f"{self.PREFIX_SESSION}:{token_hash}"
        cached = await self._get(key)

        if cached:
            logger.debug("Session validation cache HIT", token_hash=token_hash)
        else:
            logger.debug("Session validation cache MISS", token_hash=token_hash)

        return cached

    async def set_session_validation(
        self,
        token: str,
        session_id: UUID,
        user_id: UUID,
        is_active: bool
    ) -> bool:
        """Cache session validation result"""
        token_hash = self._hash_token(token)
        key = f"{self.PREFIX_SESSION}:{token_hash}"

        value = {
            "session_id": str(session_id),
            "user_id": str(user_id),
            "is_active": is_active
        }

        success = await self._set(key, value, self.TTL_SESSION)
        if success:
            logger.debug("Session validation cached", token_hash=token_hash)
        return success

    async def invalidate_session(self, token: str) -> bool:
        """Invalidate cached session"""
        token_hash = self._hash_token(token)
        key = f"{self.PREFIX_SESSION}:{token_hash}"
        return await self._delete(key)

    # Permission Cache
    async def get_permissions(self, user_id: UUID) -> Optional[List[str]]:
        """Get cached user permissions"""
        key = f"{self.PREFIX_PERMISSIONS}:{str(user_id)}"
        cached = await self._get(key)

        if cached:
            logger.debug("Permissions cache HIT", user_id=str(user_id))
        else:
            logger.debug("Permissions cache MISS", user_id=str(user_id))

        return cached

    async def set_permissions(self, user_id: UUID, permissions: List[str]) -> bool:
        """Cache user permissions"""
        key = f"{self.PREFIX_PERMISSIONS}:{str(user_id)}"

        success = await self._set(key, permissions, self.TTL_PERMISSIONS)
        if success:
            logger.debug("Permissions cached", user_id=str(user_id), count=len(permissions))
        return success

    async def invalidate_permissions(self, user_id: UUID) -> bool:
        """Invalidate cached permissions"""
        key = f"{self.PREFIX_PERMISSIONS}:{str(user_id)}"
        return await self._delete(key)

    # Bulk Invalidation
    async def invalidate_user_all(self, user_id: UUID, email: str) -> bool:
        """Invalidate all caches for a user (on logout, permission change, etc.)"""
        tasks = [
            self.invalidate_user(user_id, email),
            self.invalidate_permissions(user_id)
        ]

        # Note: We don't invalidate tokens/sessions here as they have specific tokens
        # Use invalidate_token() or invalidate_session() with specific tokens

        results = await asyncio.gather(*tasks, return_exceptions=True)
        success = any(r is True for r in results if not isinstance(r, Exception))

        logger.info("User caches invalidated", user_id=str(user_id), success=success)
        return success

    # Cache Statistics (for monitoring)
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.redis:
            return {"status": "unavailable"}

        try:
            info = await self.redis.info("stats")
            return {
                "status": "available",
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                )
            }
        except Exception as e:
            logger.warning("Failed to get cache stats", error=str(e))
            return {"status": "error", "error": str(e)}

    @staticmethod
    def _calculate_hit_rate(hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage"""
        total = hits + misses
        if total == 0:
            return 0.0
        return (hits / total) * 100


# Global cache service instance
_cache_service: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """Get or create global cache service instance"""
    global _cache_service

    if _cache_service is None:
        _cache_service = CacheService()
        await _cache_service.initialize()

    return _cache_service


# Add asyncio import at top
import asyncio
