"""
Unit tests for EmbeddingService.
"""

import pytest
import numpy as np
from PIL import Image
from unittest.mock import Mock, AsyncMock, patch

from src.services.embeddings.embedding_service import EmbeddingService
from src.services.embeddings.embedding_cache import EmbeddingCache


@pytest.fixture
def mock_cache():
    """Create a mock EmbeddingCache."""
    cache = Mock(spec=EmbeddingCache)
    cache.get_embedding = AsyncMock(return_value=None)
    cache.set_embedding = AsyncMock(return_value=True)
    return cache


@pytest.fixture
def embedding_service(mock_cache):
    """Create an EmbeddingService instance with mock cache."""
    return EmbeddingService(
        cache=mock_cache,
        device="cpu"  # Use CPU for tests
    )


@pytest.fixture
def sample_image():
    """Create a sample test image."""
    return Image.new("RGB", (224, 224), color="red")


@pytest.mark.asyncio
class TestEmbeddingService:
    """Test cases for EmbeddingService."""

    async def test_initialization(self, embedding_service):
        """Test service initialization."""
        assert embedding_service._text_model is None  # Lazy loading
        assert embedding_service._image_model is None
        assert embedding_service.device == "cpu"

    async def test_get_instruction_embedding(self, embedding_service, mock_cache):
        """Test instruction embedding generation."""
        instruction = "pick up the red block"

        # Mock the text model
        with patch.object(embedding_service, 'text_model') as mock_model:
            mock_model.encode = Mock(return_value=np.random.rand(384))

            embedding = await embedding_service.get_instruction_embedding(instruction)

            # Verify embedding shape
            assert embedding.shape == (384,)

            # Verify cache was checked and set
            mock_cache.get_embedding.assert_called_once()
            mock_cache.set_embedding.assert_called_once()

    async def test_get_instruction_embedding_cache_hit(self, embedding_service, mock_cache):
        """Test instruction embedding retrieval from cache."""
        instruction = "pick up the red block"
        cached_embedding = np.random.rand(384)

        # Mock cache hit
        mock_cache.get_embedding.return_value = cached_embedding

        embedding = await embedding_service.get_instruction_embedding(instruction)

        # Verify cached embedding was returned
        np.testing.assert_array_equal(embedding, cached_embedding)

        # Verify cache was checked but not set
        mock_cache.get_embedding.assert_called_once()
        mock_cache.set_embedding.assert_not_called()

    async def test_get_instruction_embedding_empty(self, embedding_service):
        """Test error handling for empty instruction."""
        with pytest.raises(ValueError, match="Instruction cannot be empty"):
            await embedding_service.get_instruction_embedding("")

    async def test_get_image_embedding(self, embedding_service, sample_image, mock_cache):
        """Test image embedding generation."""
        # Mock the image model and processor
        with patch.object(embedding_service, 'image_model') as mock_model, \
             patch.object(embedding_service, 'image_processor') as mock_processor:

            # Mock processor output
            mock_processor.return_value = {
                "pixel_values": np.random.rand(1, 3, 224, 224)
            }

            # Mock model output
            mock_features = Mock()
            mock_features.norm.return_value = Mock()
            mock_features.cpu.return_value.numpy.return_value = np.array([np.random.rand(512)])
            mock_model.get_image_features.return_value = mock_features

            embedding = await embedding_service.get_image_embedding(sample_image)

            # Verify embedding shape
            assert embedding.shape == (512,)

            # Verify cache was checked and set
            mock_cache.get_embedding.assert_called_once()
            mock_cache.set_embedding.assert_called_once()

    async def test_get_image_embedding_from_bytes(self, embedding_service, sample_image, mock_cache):
        """Test image embedding generation from bytes."""
        # Convert image to bytes
        import io
        img_bytes = io.BytesIO()
        sample_image.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()

        # Mock the image model and processor
        with patch.object(embedding_service, 'image_model') as mock_model, \
             patch.object(embedding_service, 'image_processor') as mock_processor:

            mock_processor.return_value = {"pixel_values": np.random.rand(1, 3, 224, 224)}
            mock_features = Mock()
            mock_features.norm.return_value = Mock()
            mock_features.cpu.return_value.numpy.return_value = np.array([np.random.rand(512)])
            mock_model.get_image_features.return_value = mock_features

            embedding = await embedding_service.get_image_embedding(img_bytes)

            assert embedding.shape == (512,)

    async def test_get_image_embedding_invalid_type(self, embedding_service):
        """Test error handling for invalid image type."""
        with pytest.raises(ValueError, match="Image must be PIL.Image"):
            await embedding_service.get_image_embedding("not_an_image")

    async def test_batch_generate_embeddings(self, embedding_service, sample_image):
        """Test batch embedding generation."""
        texts = ["instruction 1", "instruction 2", "instruction 3"]
        images = [sample_image, sample_image]

        # Mock methods
        with patch.object(embedding_service, 'get_instruction_embedding') as mock_text, \
             patch.object(embedding_service, 'get_image_embedding') as mock_image:

            mock_text.return_value = np.random.rand(384)
            mock_image.return_value = np.random.rand(512)

            results = await embedding_service.batch_generate_embeddings(
                texts=texts,
                images=images
            )

            # Verify results
            assert "text_embeddings" in results
            assert "image_embeddings" in results
            assert results["text_embeddings"].shape == (3, 384)
            assert results["image_embeddings"].shape == (2, 512)

            # Verify methods were called correct number of times
            assert mock_text.call_count == 3
            assert mock_image.call_count == 2

    async def test_cleanup(self, embedding_service):
        """Test resource cleanup."""
        # Set some models
        embedding_service._text_model = Mock()
        embedding_service._image_model = Mock()
        embedding_service._image_processor = Mock()

        # Cleanup
        embedding_service.cleanup()

        # Verify models were cleared
        assert embedding_service._text_model is None
        assert embedding_service._image_model is None
        assert embedding_service._image_processor is None

    async def test_cache_disabled(self, mock_cache):
        """Test embedding generation with cache disabled."""
        service = EmbeddingService(cache=mock_cache, device="cpu")

        with patch.object(service, 'text_model') as mock_model:
            mock_model.encode = Mock(return_value=np.random.rand(384))

            embedding = await service.get_instruction_embedding(
                "test instruction",
                use_cache=False
            )

            # Verify cache was not used
            mock_cache.get_embedding.assert_not_called()
            mock_cache.set_embedding.assert_not_called()
            assert embedding.shape == (384,)


@pytest.mark.integration
@pytest.mark.asyncio
class TestEmbeddingServiceIntegration:
    """Integration tests for EmbeddingService with real models."""

    @pytest.fixture
    def real_service(self):
        """Create service with real cache and models."""
        cache = EmbeddingCache(redis_url="redis://localhost:6379")
        service = EmbeddingService(cache=cache, device="cpu")
        yield service
        # Cleanup
        service.cleanup()

    async def test_real_instruction_embedding(self, real_service):
        """Test instruction embedding with real model."""
        pytest.skip("Skipping integration test - requires model download")

        instruction = "pick up the red block"
        embedding = await real_service.get_instruction_embedding(instruction)

        assert embedding.shape == (384,)
        assert embedding.dtype == np.float32
        assert np.all(np.isfinite(embedding))

    async def test_real_image_embedding(self, real_service, sample_image):
        """Test image embedding with real model."""
        pytest.skip("Skipping integration test - requires model download")

        embedding = await real_service.get_image_embedding(sample_image)

        assert embedding.shape == (512,)
        assert embedding.dtype == np.float32
        assert np.all(np.isfinite(embedding))

    async def test_similarity_consistency(self, real_service):
        """Test that similar instructions have similar embeddings."""
        pytest.skip("Skipping integration test - requires model download")

        inst1 = "pick up the red block"
        inst2 = "grab the red cube"
        inst3 = "move the robot arm to the left"

        emb1 = await real_service.get_instruction_embedding(inst1)
        emb2 = await real_service.get_instruction_embedding(inst2)
        emb3 = await real_service.get_instruction_embedding(inst3)

        # Calculate cosine similarities
        sim_12 = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        sim_13 = np.dot(emb1, emb3) / (np.linalg.norm(emb1) * np.linalg.norm(emb3))

        # Similar instructions should be more similar
        assert sim_12 > sim_13
        assert sim_12 > 0.7  # High similarity
        assert sim_13 < 0.6  # Lower similarity
