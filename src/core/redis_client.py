"""Redis client for caching and rate limiting."""

import json
from typing import Any, Optional

import redis.asyncio as aioredis
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import RedisError

from src.core.config import settings


class RedisManager:
    """Manages Redis connection and operations."""

    def __init__(self):
        """Initialize Redis manager."""
        self._pool: ConnectionPool | None = None
        self._redis: Redis | None = None

    def initialize(self) -> None:
        """Initialize Redis connection pool.

        This should be called during application startup.
        """
        # Create connection pool
        self._pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            socket_timeout=settings.redis_socket_timeout,
            socket_connect_timeout=settings.redis_socket_timeout,
            decode_responses=True,  # Automatically decode byte responses to strings
        )

        # Create Redis client
        self._redis = Redis(connection_pool=self._pool)

    async def close(self) -> None:
        """Close Redis connection pool.

        This should be called during application shutdown.
        """
        if self._redis:
            await self._redis.close()
        if self._pool:
            await self._pool.disconnect()

    @property
    def redis(self) -> Redis:
        """Get Redis client.

        Returns:
            Redis: Redis async client

        Raises:
            RuntimeError: If Redis not initialized
        """
        if not self._redis:
            raise RuntimeError(
                "Redis client not initialized. Call initialize() first."
            )
        return self._redis

    # =========================================================================
    # Rate Limiting Operations (Token Bucket Algorithm)
    # =========================================================================

    async def get_rate_limit_tokens(self, key: str) -> Optional[int]:
        """Get current token count for rate limiting.

        Args:
            key: Rate limit key (e.g., 'rate_limit:customer_id:tokens')

        Returns:
            Current token count or None if key doesn't exist
        """
        try:
            value = await self.redis.get(key)
            return int(value) if value is not None else None
        except (RedisError, ValueError):
            return None

    async def set_rate_limit_tokens(
        self, key: str, tokens: int, ttl: Optional[int] = None
    ) -> bool:
        """Set token count for rate limiting.

        Args:
            key: Rate limit key
            tokens: Number of tokens
            ttl: Time-to-live in seconds (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            if ttl:
                await self.redis.setex(key, ttl, tokens)
            else:
                await self.redis.set(key, tokens)
            return True
        except RedisError:
            return False

    async def decrement_rate_limit_tokens(self, key: str) -> Optional[int]:
        """Decrement token count (consume one token).

        Args:
            key: Rate limit key

        Returns:
            New token count or None if operation failed
        """
        try:
            new_value = await self.redis.decr(key)
            return new_value
        except RedisError:
            return None

    async def get_last_refill_time(self, key: str) -> Optional[float]:
        """Get last token refill timestamp.

        Args:
            key: Refill time key (e.g., 'rate_limit:customer_id:last_refill')

        Returns:
            Unix timestamp or None if key doesn't exist
        """
        try:
            value = await self.redis.get(key)
            return float(value) if value is not None else None
        except (RedisError, ValueError):
            return None

    async def set_last_refill_time(self, key: str, timestamp: float) -> bool:
        """Set last token refill timestamp.

        Args:
            key: Refill time key
            timestamp: Unix timestamp

        Returns:
            True if successful, False otherwise
        """
        try:
            await self.redis.set(key, timestamp)
            return True
        except RedisError:
            return False

    # =========================================================================
    # API Key Caching
    # =========================================================================

    async def cache_api_key(
        self, key_hash: str, key_data: dict, ttl: int = 300
    ) -> bool:
        """Cache API key data to avoid database lookups.

        Args:
            key_hash: API key hash
            key_data: API key data dictionary
            ttl: Time-to-live in seconds (default: 5 minutes)

        Returns:
            True if successful, False otherwise
        """
        try:
            cache_key = f"api_key:hash:{key_hash}"
            await self.redis.setex(cache_key, ttl, json.dumps(key_data))
            return True
        except RedisError:
            return False

    async def get_cached_api_key(self, key_hash: str) -> Optional[dict]:
        """Get cached API key data.

        Args:
            key_hash: API key hash

        Returns:
            API key data dictionary or None if not cached
        """
        try:
            cache_key = f"api_key:hash:{key_hash}"
            value = await self.redis.get(cache_key)
            if value:
                return json.loads(value)
            return None
        except (RedisError, json.JSONDecodeError):
            return None

    async def invalidate_api_key_cache(self, key_hash: str) -> bool:
        """Invalidate cached API key.

        Args:
            key_hash: API key hash

        Returns:
            True if successful, False otherwise
        """
        try:
            cache_key = f"api_key:hash:{key_hash}"
            await self.redis.delete(cache_key)
            return True
        except RedisError:
            return False

    # =========================================================================
    # Model Normalization Caching
    # =========================================================================

    async def cache_model_normalization(
        self, model_name: str, robot_type: str, normalization_data: dict
    ) -> bool:
        """Cache model normalization statistics.

        Args:
            model_name: VLA model name
            robot_type: Robot type
            normalization_data: Normalization statistics

        Returns:
            True if successful, False otherwise
        """
        try:
            cache_key = f"model:{model_name}:{robot_type}:normalization"
            await self.redis.set(cache_key, json.dumps(normalization_data))
            return True
        except RedisError:
            return False

    async def get_cached_model_normalization(
        self, model_name: str, robot_type: str
    ) -> Optional[dict]:
        """Get cached model normalization statistics.

        Args:
            model_name: VLA model name
            robot_type: Robot type

        Returns:
            Normalization statistics or None if not cached
        """
        try:
            cache_key = f"model:{model_name}:{robot_type}:normalization"
            value = await self.redis.get(cache_key)
            if value:
                return json.loads(value)
            return None
        except (RedisError, json.JSONDecodeError):
            return None

    # =========================================================================
    # Inference Queue Monitoring
    # =========================================================================

    async def set_queue_depth(self, depth: int) -> bool:
        """Set current inference queue depth.

        Args:
            depth: Number of requests in queue

        Returns:
            True if successful, False otherwise
        """
        try:
            await self.redis.set("inference:queue:depth", depth)
            return True
        except RedisError:
            return False

    async def get_queue_depth(self) -> Optional[int]:
        """Get current inference queue depth.

        Returns:
            Queue depth or None if unavailable
        """
        try:
            value = await self.redis.get("inference:queue:depth")
            return int(value) if value is not None else None
        except (RedisError, ValueError):
            return None

    # =========================================================================
    # General Operations
    # =========================================================================

    async def get(self, key: str) -> Optional[str]:
        """Get value by key.

        Args:
            key: Redis key

        Returns:
            Value or None if key doesn't exist
        """
        try:
            return await self.redis.get(key)
        except RedisError:
            return None

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Set key-value pair.

        Args:
            key: Redis key
            value: Value to store
            ttl: Time-to-live in seconds (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            if ttl:
                await self.redis.setex(key, ttl, value)
            else:
                await self.redis.set(key, value)
            return True
        except RedisError:
            return False

    async def delete(self, key: str) -> bool:
        """Delete key.

        Args:
            key: Redis key

        Returns:
            True if successful, False otherwise
        """
        try:
            await self.redis.delete(key)
            return True
        except RedisError:
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists.

        Args:
            key: Redis key

        Returns:
            True if key exists, False otherwise
        """
        try:
            return await self.redis.exists(key) > 0
        except RedisError:
            return False

    async def health_check(self) -> bool:
        """Check Redis connectivity.

        Returns:
            True if Redis is healthy, False otherwise
        """
        try:
            await self.redis.ping()
            return True
        except RedisError:
            return False


# Global Redis manager instance
redis_manager = RedisManager()


def get_redis() -> Redis:
    """FastAPI dependency for Redis client.

    Returns:
        Redis: Redis async client

    Example:
        ```python
        @app.get("/cache")
        async def get_cache(redis: Redis = Depends(get_redis)):
            value = await redis.get("my_key")
            return {"value": value}
        ```
    """
    return redis_manager.redis


async def init_redis() -> None:
    """Initialize Redis connection.

    This should be called during application startup.
    """
    redis_manager.initialize()


async def close_redis() -> None:
    """Close Redis connection.

    This should be called during application shutdown.
    """
    await redis_manager.close()
