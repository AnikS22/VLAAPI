"""
Comprehensive tests for EmbeddingCache Redis layer.
Tests TTL, serialization, batch operations, and connection pooling.
"""

import pytest
import numpy as np
from unittest.mock import AsyncMock, Mock, patch
import pickle
import asyncio

from src.services.embeddings.embedding_cache import EmbeddingCache


class TestCacheInitialization:
    """Test cache initialization and configuration."""

    def test_default_initialization(self):
        """Test cache with default settings."""
        cache = EmbeddingCache()

        assert cache.redis_url == "redis://localhost:6379"
        assert cache.ttl == EmbeddingCache.DEFAULT_TTL
        assert cache.ttl == 300  # 5 minutes
        assert cache.max_connections == 10
        assert cache._client is None  # Lazy connection

    def test_custom_initialization(self):
        """Test cache with custom settings."""
        cache = EmbeddingCache(
            redis_url="redis://custom:6380",
            ttl=600,
            max_connections=20
        )

        assert cache.redis_url == "redis://custom:6380"
        assert cache.ttl == 600
        assert cache.max_connections == 20

    def test_key_prefix(self):
        """Test cache key namespacing."""
        cache = EmbeddingCache()

        key = cache._make_key("test:123")
        assert key == "embedding:test:123"
        assert key.startswith(EmbeddingCache.KEY_PREFIX)


class TestRedisConnection:
    """Test Redis connection management."""

    @pytest.mark.asyncio
    @patch('src.services.embeddings.embedding_cache.redis.from_url')
    async def test_client_creation(self, mock_from_url):
        """Test Redis client is created lazily."""
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        cache = EmbeddingCache()
        assert cache._client is None

        client = await cache._get_client()

        assert client == mock_client
        mock_from_url.assert_called_once_with(
            "redis://localhost:6379",
            encoding="utf-8",
            decode_responses=False,
            max_connections=10
        )
        mock_client.ping.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.services.embeddings.embedding_cache.redis.from_url')
    async def test_client_reuse(self, mock_from_url):
        """Test Redis client is reused after creation."""
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        cache = EmbeddingCache()

        client1 = await cache._get_client()
        client2 = await cache._get_client()

        assert client1 == client2
        mock_from_url.assert_called_once()  # Only created once

    @pytest.mark.asyncio
    @patch('src.services.embeddings.embedding_cache.redis.from_url')
    async def test_connection_error(self, mock_from_url):
        """Test handling of Redis connection errors."""
        mock_from_url.side_effect = ConnectionError("Cannot connect to Redis")

        cache = EmbeddingCache()

        with pytest.raises(ConnectionError, match="Cannot connect to Redis"):
            await cache._get_client()

    @pytest.mark.asyncio
    async def test_close_connection(self):
        """Test closing Redis connection."""
        cache = EmbeddingCache()
        mock_client = AsyncMock()
        cache._client = mock_client

        await cache.close()

        mock_client.close.assert_called_once()
        assert cache._client is None


class TestSerialization:
    """Test embedding serialization and deserialization."""

    def test_serialize_embedding(self):
        """Test numpy array serialization to bytes."""
        cache = EmbeddingCache()

        embedding = np.random.rand(384).astype(np.float32)
        serialized = cache._serialize_embedding(embedding)

        assert isinstance(serialized, bytes)

        # Verify can deserialize
        deserialized = pickle.loads(serialized)
        assert np.array_equal(deserialized, embedding)

    def test_deserialize_embedding(self):
        """Test bytes deserialization to numpy array."""
        cache = EmbeddingCache()

        original = np.random.rand(512).astype(np.float32)
        serialized = pickle.dumps(original, protocol=pickle.HIGHEST_PROTOCOL)

        deserialized = cache._deserialize_embedding(serialized)

        assert isinstance(deserialized, np.ndarray)
        assert np.array_equal(deserialized, original)
        assert deserialized.dtype == np.float32

    def test_serialize_preserves_precision(self):
        """Test serialization preserves float precision."""
        cache = EmbeddingCache()

        embedding = np.array([0.123456789, 0.987654321], dtype=np.float32)
        serialized = cache._serialize_embedding(embedding)
        deserialized = cache._deserialize_embedding(serialized)

        assert np.allclose(deserialized, embedding, atol=1e-7)


class TestCacheGetSet:
    """Test basic cache get/set operations."""

    @pytest.mark.asyncio
    async def test_set_embedding(self):
        """Test storing embedding in cache."""
        cache = EmbeddingCache()
        mock_client = AsyncMock()
        cache._client = mock_client

        embedding = np.random.rand(384).astype(np.float32)
        success = await cache.set_embedding("test:123", embedding)

        assert success is True
        mock_client.setex.assert_called_once()

        # Verify call arguments
        call_args = mock_client.setex.call_args[0]
        assert call_args[0] == "embedding:test:123"  # Key with prefix
        assert call_args[1] == 300  # TTL
        assert isinstance(call_args[2], bytes)  # Serialized data

    @pytest.mark.asyncio
    async def test_set_embedding_custom_ttl(self):
        """Test storing embedding with custom TTL."""
        cache = EmbeddingCache(ttl=600)
        mock_client = AsyncMock()
        cache._client = mock_client

        embedding = np.random.rand(384).astype(np.float32)
        await cache.set_embedding("test:456", embedding, ttl=120)

        # Should use custom TTL
        call_args = mock_client.setex.call_args[0]
        assert call_args[1] == 120

    @pytest.mark.asyncio
    async def test_get_embedding_hit(self):
        """Test retrieving embedding from cache (hit)."""
        cache = EmbeddingCache()
        mock_client = AsyncMock()

        original = np.random.rand(384).astype(np.float32)
        serialized = cache._serialize_embedding(original)
        mock_client.get.return_value = serialized

        cache._client = mock_client

        result = await cache.get_embedding("test:123")

        assert result is not None
        assert np.array_equal(result, original)
        mock_client.get.assert_called_once_with("embedding:test:123")

    @pytest.mark.asyncio
    async def test_get_embedding_miss(self):
        """Test cache miss returns None."""
        cache = EmbeddingCache()
        mock_client = AsyncMock()
        mock_client.get.return_value = None
        cache._client = mock_client

        result = await cache.get_embedding("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_embedding_redis_error(self):
        """Test handling Redis errors during get."""
        cache = EmbeddingCache()
        mock_client = AsyncMock()

        import redis.asyncio as redis
        mock_client.get.side_effect = redis.RedisError("Connection lost")
        cache._client = mock_client

        result = await cache.get_embedding("test:123")

        assert result is None  # Returns None on error

    @pytest.mark.asyncio
    async def test_set_embedding_redis_error(self):
        """Test handling Redis errors during set."""
        cache = EmbeddingCache()
        mock_client = AsyncMock()

        import redis.asyncio as redis
        mock_client.setex.side_effect = redis.RedisError("Connection lost")
        cache._client = mock_client

        embedding = np.random.rand(384).astype(np.float32)
        success = await cache.set_embedding("test:123", embedding)

        assert success is False


class TestCacheDelete:
    """Test cache deletion operations."""

    @pytest.mark.asyncio
    async def test_delete_embedding(self):
        """Test deleting embedding from cache."""
        cache = EmbeddingCache()
        mock_client = AsyncMock()
        mock_client.delete.return_value = 1  # 1 key deleted
        cache._client = mock_client

        result = await cache.delete_embedding("test:123")

        assert result is True
        mock_client.delete.assert_called_once_with("embedding:test:123")

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self):
        """Test deleting non-existent key."""
        cache = EmbeddingCache()
        mock_client = AsyncMock()
        mock_client.delete.return_value = 0  # No keys deleted
        cache._client = mock_client

        result = await cache.delete_embedding("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_clear_pattern(self):
        """Test clearing keys matching pattern."""
        cache = EmbeddingCache()
        mock_client = AsyncMock()

        # Mock scan_iter to return some keys
        mock_keys = [b"embedding:instruction:1", b"embedding:instruction:2"]

        async def mock_scan_iter(match, count):
            for key in mock_keys:
                yield key

        mock_client.scan_iter = mock_scan_iter
        mock_client.delete.return_value = 2
        cache._client = mock_client

        deleted = await cache.clear_pattern("instruction:*")

        assert deleted == 2
        mock_client.delete.assert_called_once()


class TestBatchOperations:
    """Test batch get/set operations."""

    @pytest.mark.asyncio
    async def test_get_many(self):
        """Test batch retrieval of embeddings."""
        cache = EmbeddingCache()
        mock_client = AsyncMock()

        # Create test embeddings
        emb1 = np.random.rand(384).astype(np.float32)
        emb2 = np.random.rand(384).astype(np.float32)

        # Mock pipeline
        mock_pipeline = AsyncMock()
        mock_pipeline.execute.return_value = [
            cache._serialize_embedding(emb1),
            cache._serialize_embedding(emb2),
            None  # Cache miss for third key
        ]
        mock_client.pipeline.return_value = mock_pipeline
        cache._client = mock_client

        keys = ["key1", "key2", "key3"]
        results = await cache.get_many(keys)

        assert len(results) == 3
        assert np.array_equal(results["key1"], emb1)
        assert np.array_equal(results["key2"], emb2)
        assert results["key3"] is None

        # Verify pipeline was used
        assert mock_pipeline.get.call_count == 3

    @pytest.mark.asyncio
    async def test_set_many(self):
        """Test batch storage of embeddings."""
        cache = EmbeddingCache()
        mock_client = AsyncMock()

        # Mock pipeline
        mock_pipeline = AsyncMock()
        mock_pipeline.execute.return_value = [True, True, True]
        mock_client.pipeline.return_value = mock_pipeline
        cache._client = mock_client

        embeddings = {
            "key1": np.random.rand(384).astype(np.float32),
            "key2": np.random.rand(384).astype(np.float32),
            "key3": np.random.rand(384).astype(np.float32)
        }

        results = await cache.set_many(embeddings)

        assert len(results) == 3
        assert all(results.values())  # All successful
        assert mock_pipeline.setex.call_count == 3

    @pytest.mark.asyncio
    async def test_set_many_custom_ttl(self):
        """Test batch storage with custom TTL."""
        cache = EmbeddingCache(ttl=300)
        mock_client = AsyncMock()

        mock_pipeline = AsyncMock()
        mock_pipeline.execute.return_value = [True, True]
        mock_client.pipeline.return_value = mock_pipeline
        cache._client = mock_client

        embeddings = {
            "key1": np.random.rand(384).astype(np.float32),
            "key2": np.random.rand(384).astype(np.float32)
        }

        await cache.set_many(embeddings, ttl=600)

        # Check custom TTL was used
        for call in mock_pipeline.setex.call_args_list:
            assert call[0][1] == 600  # TTL argument

    @pytest.mark.asyncio
    async def test_batch_operations_partial_failure(self):
        """Test handling partial failures in batch operations."""
        cache = EmbeddingCache()
        mock_client = AsyncMock()

        mock_pipeline = AsyncMock()
        mock_pipeline.execute.return_value = [True, False, True]  # Middle one fails
        mock_client.pipeline.return_value = mock_pipeline
        cache._client = mock_client

        embeddings = {
            "key1": np.random.rand(384).astype(np.float32),
            "key2": np.random.rand(384).astype(np.float32),
            "key3": np.random.rand(384).astype(np.float32)
        }

        results = await cache.set_many(embeddings)

        assert results["key1"] is True
        assert results["key2"] is False
        assert results["key3"] is True


class TestCacheStats:
    """Test cache statistics and monitoring."""

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test retrieving cache statistics."""
        cache = EmbeddingCache()
        mock_client = AsyncMock()

        # Mock Redis info command
        mock_client.info.return_value = {
            "used_memory_human": "10.5M",
            "used_memory_peak_human": "15.2M"
        }

        # Mock scan_iter for key count
        async def mock_scan_iter(match, count):
            for i in range(42):
                yield f"embedding:key{i}"

        mock_client.scan_iter = mock_scan_iter
        cache._client = mock_client

        stats = await cache.get_stats()

        assert stats["total_keys"] == 42
        assert stats["memory_used"] == "10.5M"
        assert stats["memory_peak"] == "15.2M"
        assert stats["ttl_seconds"] == 300
        assert stats["connected"] is True

    @pytest.mark.asyncio
    async def test_get_stats_connection_error(self):
        """Test stats when Redis is disconnected."""
        cache = EmbeddingCache()
        mock_client = AsyncMock()

        import redis.asyncio as redis
        mock_client.info.side_effect = redis.RedisError("Not connected")
        cache._client = mock_client

        stats = await cache.get_stats()

        assert stats["connected"] is False
        assert "error" in stats


class TestContextManager:
    """Test async context manager support."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test using cache as async context manager."""
        mock_client = AsyncMock()

        with patch('src.services.embeddings.embedding_cache.redis.from_url') as mock_from_url:
            mock_from_url.return_value = mock_client
            mock_client.ping.return_value = True

            async with EmbeddingCache() as cache:
                assert cache is not None
                # Use cache
                await cache._get_client()

            # Connection should be closed
            mock_client.close.assert_called_once()


class TestTTLExpiration:
    """Test TTL expiration behavior."""

    @pytest.mark.asyncio
    async def test_ttl_expiration_simulation(self):
        """Test that TTL is properly set (simulated)."""
        cache = EmbeddingCache(ttl=1)  # 1 second TTL
        mock_client = AsyncMock()
        cache._client = mock_client

        embedding = np.random.rand(384).astype(np.float32)
        await cache.set_embedding("short_lived", embedding)

        # Verify TTL was set to 1 second
        call_args = mock_client.setex.call_args[0]
        assert call_args[1] == 1

    @pytest.mark.asyncio
    async def test_different_ttls_per_key(self):
        """Test setting different TTLs for different keys."""
        cache = EmbeddingCache(ttl=300)  # Default 5 min
        mock_client = AsyncMock()
        cache._client = mock_client

        emb = np.random.rand(384).astype(np.float32)

        # Default TTL
        await cache.set_embedding("key1", emb)
        call1_ttl = mock_client.setex.call_args[0][1]

        # Custom short TTL
        await cache.set_embedding("key2", emb, ttl=60)
        call2_ttl = mock_client.setex.call_args[0][1]

        # Custom long TTL
        await cache.set_embedding("key3", emb, ttl=3600)
        call3_ttl = mock_client.setex.call_args[0][1]

        assert call1_ttl == 300
        assert call2_ttl == 60
        assert call3_ttl == 3600
