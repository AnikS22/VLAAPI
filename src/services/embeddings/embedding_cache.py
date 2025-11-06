"""
Redis caching layer for embeddings.
Provides TTL-based caching with automatic serialization/deserialization.
"""

import logging
import pickle
from typing import Optional
import numpy as np
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """
    Redis-backed cache for embeddings with automatic TTL management.

    Features:
    - 5-minute TTL for hot embeddings
    - Automatic numpy serialization/deserialization
    - Key namespacing for different embedding types
    - Connection pooling and error handling
    """

    DEFAULT_TTL = 300  # 5 minutes
    KEY_PREFIX = "embedding"

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        ttl: int = DEFAULT_TTL,
        max_connections: int = 10
    ):
        """
        Initialize the embedding cache.

        Args:
            redis_url: Redis connection URL
            ttl: Time-to-live in seconds (default: 300s = 5min)
            max_connections: Maximum Redis connections in pool
        """
        self.redis_url = redis_url
        self.ttl = ttl
        self.max_connections = max_connections
        self._client: Optional[redis.Redis] = None

        logger.info(f"EmbeddingCache initialized with TTL: {ttl}s")

    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client with connection pooling."""
        if self._client is None:
            logger.info(f"Connecting to Redis: {self.redis_url}")
            try:
                self._client = await redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=False,  # We handle binary data
                    max_connections=self.max_connections
                )
                # Test connection
                await self._client.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return self._client

    def _make_key(self, key: str) -> str:
        """Create namespaced cache key."""
        return f"{self.KEY_PREFIX}:{key}"

    def _serialize_embedding(self, embedding: np.ndarray) -> bytes:
        """Serialize numpy array to bytes using pickle."""
        return pickle.dumps(embedding, protocol=pickle.HIGHEST_PROTOCOL)

    def _deserialize_embedding(self, data: bytes) -> np.ndarray:
        """Deserialize bytes to numpy array."""
        return pickle.loads(data)

    async def get_embedding(self, key: str) -> Optional[np.ndarray]:
        """
        Retrieve embedding from cache.

        Args:
            key: Cache key (without prefix)

        Returns:
            Cached embedding or None if not found
        """
        try:
            client = await self._get_client()
            cache_key = self._make_key(key)

            data = await client.get(cache_key)
            if data is None:
                logger.debug(f"Cache miss: {cache_key}")
                return None

            embedding = self._deserialize_embedding(data)
            logger.debug(f"Cache hit: {cache_key}, shape: {embedding.shape}")
            return embedding

        except redis.RedisError as e:
            logger.error(f"Redis error during get: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during cache get: {e}")
            return None

    async def set_embedding(
        self,
        key: str,
        embedding: np.ndarray,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store embedding in cache with TTL.

        Args:
            key: Cache key (without prefix)
            embedding: Numpy array to cache
            ttl: Optional custom TTL (uses default if not provided)

        Returns:
            True if successful, False otherwise
        """
        try:
            client = await self._get_client()
            cache_key = self._make_key(key)
            ttl_seconds = ttl or self.ttl

            data = self._serialize_embedding(embedding)
            await client.setex(cache_key, ttl_seconds, data)

            logger.debug(f"Cached embedding: {cache_key}, TTL: {ttl_seconds}s, shape: {embedding.shape}")
            return True

        except redis.RedisError as e:
            logger.error(f"Redis error during set: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during cache set: {e}")
            return False

    async def delete_embedding(self, key: str) -> bool:
        """
        Delete embedding from cache.

        Args:
            key: Cache key (without prefix)

        Returns:
            True if deleted, False otherwise
        """
        try:
            client = await self._get_client()
            cache_key = self._make_key(key)

            result = await client.delete(cache_key)
            logger.debug(f"Deleted cache key: {cache_key}, result: {result}")
            return result > 0

        except redis.RedisError as e:
            logger.error(f"Redis error during delete: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during cache delete: {e}")
            return False

    async def get_many(self, keys: list[str]) -> dict[str, Optional[np.ndarray]]:
        """
        Retrieve multiple embeddings in one operation.

        Args:
            keys: List of cache keys (without prefix)

        Returns:
            Dict mapping keys to embeddings (None if not found)
        """
        try:
            client = await self._get_client()
            cache_keys = [self._make_key(k) for k in keys]

            # Use pipeline for batch get
            pipe = client.pipeline()
            for cache_key in cache_keys:
                pipe.get(cache_key)
            results = await pipe.execute()

            # Build result dict
            embeddings = {}
            for key, data in zip(keys, results):
                if data is not None:
                    embeddings[key] = self._deserialize_embedding(data)
                else:
                    embeddings[key] = None

            hits = sum(1 for v in embeddings.values() if v is not None)
            logger.debug(f"Batch get: {hits}/{len(keys)} cache hits")
            return embeddings

        except redis.RedisError as e:
            logger.error(f"Redis error during batch get: {e}")
            return {k: None for k in keys}
        except Exception as e:
            logger.error(f"Unexpected error during batch get: {e}")
            return {k: None for k in keys}

    async def set_many(
        self,
        embeddings: dict[str, np.ndarray],
        ttl: Optional[int] = None
    ) -> dict[str, bool]:
        """
        Store multiple embeddings in one operation.

        Args:
            embeddings: Dict mapping keys to embeddings
            ttl: Optional custom TTL

        Returns:
            Dict mapping keys to success status
        """
        try:
            client = await self._get_client()
            ttl_seconds = ttl or self.ttl

            # Use pipeline for batch set
            pipe = client.pipeline()
            for key, embedding in embeddings.items():
                cache_key = self._make_key(key)
                data = self._serialize_embedding(embedding)
                pipe.setex(cache_key, ttl_seconds, data)

            results = await pipe.execute()

            # Build result dict
            success = {k: bool(r) for k, r in zip(embeddings.keys(), results)}
            successful = sum(success.values())
            logger.debug(f"Batch set: {successful}/{len(embeddings)} successful")
            return success

        except redis.RedisError as e:
            logger.error(f"Redis error during batch set: {e}")
            return {k: False for k in embeddings.keys()}
        except Exception as e:
            logger.error(f"Unexpected error during batch set: {e}")
            return {k: False for k in embeddings.keys()}

    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Redis key pattern (e.g., "instruction:*")

        Returns:
            Number of keys deleted
        """
        try:
            client = await self._get_client()
            full_pattern = self._make_key(pattern)

            # Scan for matching keys
            keys = []
            async for key in client.scan_iter(match=full_pattern, count=100):
                keys.append(key)

            if keys:
                deleted = await client.delete(*keys)
                logger.info(f"Cleared {deleted} keys matching pattern: {full_pattern}")
                return deleted
            else:
                logger.info(f"No keys found matching pattern: {full_pattern}")
                return 0

        except redis.RedisError as e:
            logger.error(f"Redis error during clear pattern: {e}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error during clear pattern: {e}")
            return 0

    async def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats (total_keys, memory_usage, etc.)
        """
        try:
            client = await self._get_client()
            info = await client.info("memory")

            # Count keys with our prefix
            key_count = 0
            async for _ in client.scan_iter(match=f"{self.KEY_PREFIX}:*", count=100):
                key_count += 1

            stats = {
                "total_keys": key_count,
                "memory_used": info.get("used_memory_human", "N/A"),
                "memory_peak": info.get("used_memory_peak_human", "N/A"),
                "ttl_seconds": self.ttl,
                "connected": True
            }

            logger.debug(f"Cache stats: {stats}")
            return stats

        except redis.RedisError as e:
            logger.error(f"Redis error during stats: {e}")
            return {"connected": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error during stats: {e}")
            return {"connected": False, "error": str(e)}

    async def close(self):
        """Close Redis connection."""
        if self._client is not None:
            logger.info("Closing Redis connection")
            await self._client.close()
            self._client = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
