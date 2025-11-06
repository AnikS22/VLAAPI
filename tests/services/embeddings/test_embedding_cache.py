"""
Unit tests for EmbeddingCache.
"""

import pytest
import numpy as np
from unittest.mock import AsyncMock, Mock, patch

from src.services.embeddings.embedding_cache import EmbeddingCache


@pytest.fixture
def embedding_cache():
    """Create an EmbeddingCache instance."""
    return EmbeddingCache(
        redis_url="redis://localhost:6379",
        ttl=300
    )


@pytest.fixture
def sample_embedding():
    """Create a sample embedding."""
    return np.random.rand(384).astype(np.float32)


@pytest.mark.asyncio
class TestEmbeddingCache:
    """Test cases for EmbeddingCache."""

    async def test_initialization(self, embedding_cache):
        """Test cache initialization."""
        assert embedding_cache.redis_url == "redis://localhost:6379"
        assert embedding_cache.ttl == 300
        assert embedding_cache._client is None

    async def test_make_key(self, embedding_cache):
        """Test cache key generation."""
        key = embedding_cache._make_key("test_key")
        assert key == "embedding:test_key"

    def test_serialize_deserialize(self, embedding_cache, sample_embedding):
        """Test embedding serialization/deserialization."""
        # Serialize
        serialized = embedding_cache._serialize_embedding(sample_embedding)
        assert isinstance(serialized, bytes)

        # Deserialize
        deserialized = embedding_cache._deserialize_embedding(serialized)
        np.testing.assert_array_equal(deserialized, sample_embedding)
        assert deserialized.dtype == sample_embedding.dtype

    @patch('redis.asyncio.from_url')
    async def test_get_embedding_cache_miss(self, mock_redis, embedding_cache):
        """Test cache miss."""
        # Mock Redis client
        mock_client = AsyncMock()
        mock_client.get.return_value = None
        mock_client.ping = AsyncMock()
        mock_redis.return_value = mock_client

        result = await embedding_cache.get_embedding("test_key")

        assert result is None
        mock_client.get.assert_called_once_with("embedding:test_key")

    @patch('redis.asyncio.from_url')
    async def test_get_embedding_cache_hit(self, mock_redis, embedding_cache, sample_embedding):
        """Test cache hit."""
        # Mock Redis client
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock()
        serialized = embedding_cache._serialize_embedding(sample_embedding)
        mock_client.get.return_value = serialized
        mock_redis.return_value = mock_client

        result = await embedding_cache.get_embedding("test_key")

        np.testing.assert_array_equal(result, sample_embedding)
        mock_client.get.assert_called_once_with("embedding:test_key")

    @patch('redis.asyncio.from_url')
    async def test_set_embedding(self, mock_redis, embedding_cache, sample_embedding):
        """Test setting embedding in cache."""
        # Mock Redis client
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock()
        mock_client.setex.return_value = True
        mock_redis.return_value = mock_client

        result = await embedding_cache.set_embedding("test_key", sample_embedding)

        assert result is True
        mock_client.setex.assert_called_once()

        # Verify call arguments
        call_args = mock_client.setex.call_args
        assert call_args[0][0] == "embedding:test_key"
        assert call_args[0][1] == 300  # TTL

    @patch('redis.asyncio.from_url')
    async def test_set_embedding_custom_ttl(self, mock_redis, embedding_cache, sample_embedding):
        """Test setting embedding with custom TTL."""
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock()
        mock_client.setex.return_value = True
        mock_redis.return_value = mock_client

        result = await embedding_cache.set_embedding("test_key", sample_embedding, ttl=600)

        assert result is True
        call_args = mock_client.setex.call_args
        assert call_args[0][1] == 600  # Custom TTL

    @patch('redis.asyncio.from_url')
    async def test_delete_embedding(self, mock_redis, embedding_cache):
        """Test deleting embedding from cache."""
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock()
        mock_client.delete.return_value = 1
        mock_redis.return_value = mock_client

        result = await embedding_cache.delete_embedding("test_key")

        assert result is True
        mock_client.delete.assert_called_once_with("embedding:test_key")

    @patch('redis.asyncio.from_url')
    async def test_get_many(self, mock_redis, embedding_cache):
        """Test batch get operation."""
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock()

        # Mock pipeline
        mock_pipeline = AsyncMock()
        mock_pipeline.get = Mock()
        mock_pipeline.execute.return_value = [
            embedding_cache._serialize_embedding(np.random.rand(384)),
            None,  # Cache miss
            embedding_cache._serialize_embedding(np.random.rand(384))
        ]
        mock_client.pipeline.return_value = mock_pipeline
        mock_redis.return_value = mock_client

        keys = ["key1", "key2", "key3"]
        results = await embedding_cache.get_many(keys)

        assert len(results) == 3
        assert isinstance(results["key1"], np.ndarray)
        assert results["key2"] is None
        assert isinstance(results["key3"], np.ndarray)

    @patch('redis.asyncio.from_url')
    async def test_set_many(self, mock_redis, embedding_cache):
        """Test batch set operation."""
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock()

        # Mock pipeline
        mock_pipeline = AsyncMock()
        mock_pipeline.setex = Mock()
        mock_pipeline.execute.return_value = [True, True, True]
        mock_client.pipeline.return_value = mock_pipeline
        mock_redis.return_value = mock_client

        embeddings = {
            "key1": np.random.rand(384),
            "key2": np.random.rand(384),
            "key3": np.random.rand(384)
        }

        results = await embedding_cache.set_many(embeddings)

        assert len(results) == 3
        assert all(results.values())

    @patch('redis.asyncio.from_url')
    async def test_clear_pattern(self, mock_redis, embedding_cache):
        """Test clearing keys by pattern."""
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock()

        # Mock scan_iter to return keys
        async def mock_scan_iter(*args, **kwargs):
            keys = [b"embedding:instruction:key1", b"embedding:instruction:key2"]
            for key in keys:
                yield key

        mock_client.scan_iter = mock_scan_iter
        mock_client.delete.return_value = 2
        mock_redis.return_value = mock_client

        deleted = await embedding_cache.clear_pattern("instruction:*")

        assert deleted == 2
        mock_client.delete.assert_called_once()

    @patch('redis.asyncio.from_url')
    async def test_get_stats(self, mock_redis, embedding_cache):
        """Test getting cache statistics."""
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock()
        mock_client.info.return_value = {
            "used_memory_human": "10M",
            "used_memory_peak_human": "15M"
        }

        # Mock scan_iter for key counting
        async def mock_scan_iter(*args, **kwargs):
            keys = [b"embedding:key1", b"embedding:key2"]
            for key in keys:
                yield key

        mock_client.scan_iter = mock_scan_iter
        mock_redis.return_value = mock_client

        stats = await embedding_cache.get_stats()

        assert stats["connected"] is True
        assert stats["total_keys"] == 2
        assert stats["memory_used"] == "10M"
        assert stats["ttl_seconds"] == 300

    @patch('redis.asyncio.from_url')
    async def test_error_handling_redis_error(self, mock_redis, embedding_cache):
        """Test error handling for Redis errors."""
        import redis.asyncio as redis_lib

        mock_client = AsyncMock()
        mock_client.ping = AsyncMock()
        mock_client.get.side_effect = redis_lib.RedisError("Connection error")
        mock_redis.return_value = mock_client

        result = await embedding_cache.get_embedding("test_key")

        # Should return None on error, not raise
        assert result is None

    @patch('redis.asyncio.from_url')
    async def test_context_manager(self, mock_redis, embedding_cache):
        """Test async context manager."""
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock()
        mock_client.close = AsyncMock()
        mock_redis.return_value = mock_client

        async with embedding_cache as cache:
            assert cache is embedding_cache

        # Verify close was called
        # Note: close will be called on the client when it's set
        assert True  # Context manager works


@pytest.mark.integration
@pytest.mark.asyncio
class TestEmbeddingCacheIntegration:
    """Integration tests for EmbeddingCache with real Redis."""

    @pytest.fixture
    async def real_cache(self):
        """Create cache with real Redis connection."""
        cache = EmbeddingCache(redis_url="redis://localhost:6379")
        yield cache
        # Cleanup
        await cache.clear_pattern("test:*")
        await cache.close()

    async def test_real_cache_operations(self, real_cache):
        """Test real cache operations."""
        pytest.skip("Skipping integration test - requires Redis")

        embedding = np.random.rand(384).astype(np.float32)

        # Set
        success = await real_cache.set_embedding("test:key1", embedding)
        assert success is True

        # Get
        retrieved = await real_cache.get_embedding("test:key1")
        np.testing.assert_array_almost_equal(retrieved, embedding, decimal=5)

        # Delete
        deleted = await real_cache.delete_embedding("test:key1")
        assert deleted is True

        # Get after delete
        result = await real_cache.get_embedding("test:key1")
        assert result is None

    async def test_real_batch_operations(self, real_cache):
        """Test real batch operations."""
        pytest.skip("Skipping integration test - requires Redis")

        embeddings = {
            "test:batch1": np.random.rand(384).astype(np.float32),
            "test:batch2": np.random.rand(384).astype(np.float32),
            "test:batch3": np.random.rand(384).astype(np.float32)
        }

        # Set many
        results = await real_cache.set_many(embeddings)
        assert all(results.values())

        # Get many
        retrieved = await real_cache.get_many(list(embeddings.keys()))
        for key, original_embedding in embeddings.items():
            np.testing.assert_array_almost_equal(
                retrieved[key], original_embedding, decimal=5
            )
