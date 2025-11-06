"""
Comprehensive tests for EmbeddingService.
Tests text/image embeddings, caching, lazy loading, and similarity search.
"""

import pytest
import numpy as np
from PIL import Image
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import hashlib

from src.services.embeddings.embedding_service import EmbeddingService
from src.services.embeddings.embedding_cache import EmbeddingCache


class TestEmbeddingServiceInitialization:
    """Test service initialization and lazy loading."""

    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        service = EmbeddingService()

        assert service.text_model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert service.image_model_name == "openai/clip-vit-base-patch32"
        assert service.device in ["cuda", "cpu"]
        assert service._text_model is None  # Lazy loading
        assert service._image_model is None
        assert service._image_processor is None

    def test_init_custom_parameters(self):
        """Test initialization with custom parameters."""
        cache = EmbeddingCache()
        service = EmbeddingService(
            cache=cache,
            text_model_name="custom/text-model",
            image_model_name="custom/image-model",
            device="cpu"
        )

        assert service.cache == cache
        assert service.text_model_name == "custom/text-model"
        assert service.image_model_name == "custom/image-model"
        assert service.device == "cpu"

    @patch('src.services.embeddings.embedding_service.torch.cuda.is_available')
    def test_device_auto_selection_cuda(self, mock_cuda):
        """Test automatic CUDA device selection."""
        mock_cuda.return_value = True
        service = EmbeddingService()
        assert service.device == "cuda"

    @patch('src.services.embeddings.embedding_service.torch.cuda.is_available')
    def test_device_auto_selection_cpu(self, mock_cuda):
        """Test automatic CPU device selection."""
        mock_cuda.return_value = False
        service = EmbeddingService()
        assert service.device == "cpu"


class TestEmbeddingServiceLazyLoading:
    """Test lazy loading of ML models."""

    @patch('src.services.embeddings.embedding_service.SentenceTransformer')
    def test_text_model_lazy_loading(self, mock_transformer):
        """Test text model is loaded on first access."""
        mock_model = Mock()
        mock_transformer.return_value = mock_model

        service = EmbeddingService(device="cpu")
        assert service._text_model is None

        # Access property triggers loading
        model = service.text_model

        assert service._text_model == mock_model
        mock_transformer.assert_called_once_with("sentence-transformers/all-MiniLM-L6-v2")
        mock_model.to.assert_called_once_with("cpu")

    @patch('src.services.embeddings.embedding_service.CLIPModel')
    def test_image_model_lazy_loading(self, mock_clip):
        """Test image model is loaded on first access."""
        mock_model = Mock()
        mock_clip.from_pretrained.return_value = mock_model

        service = EmbeddingService(device="cpu")
        assert service._image_model is None

        # Access property triggers loading
        model = service.image_model

        assert service._image_model == mock_model
        mock_clip.from_pretrained.assert_called_once_with("openai/clip-vit-base-patch32")
        mock_model.to.assert_called_once_with("cpu")
        mock_model.eval.assert_called_once()

    @patch('src.services.embeddings.embedding_service.CLIPProcessor')
    def test_image_processor_lazy_loading(self, mock_processor):
        """Test CLIP processor is loaded on first access."""
        mock_proc = Mock()
        mock_processor.from_pretrained.return_value = mock_proc

        service = EmbeddingService()
        assert service._image_processor is None

        # Access property triggers loading
        proc = service.image_processor

        assert service._image_processor == mock_proc
        mock_processor.from_pretrained.assert_called_once_with("openai/clip-vit-base-patch32")

    @patch('src.services.embeddings.embedding_service.SentenceTransformer')
    def test_text_model_loading_error(self, mock_transformer):
        """Test error handling when text model fails to load."""
        mock_transformer.side_effect = RuntimeError("Model download failed")

        service = EmbeddingService()

        with pytest.raises(RuntimeError, match="Model download failed"):
            _ = service.text_model


class TestTextEmbedding:
    """Test text embedding generation."""

    @pytest.mark.asyncio
    async def test_instruction_embedding_generation(self):
        """Test generating embedding for instruction text."""
        mock_cache = AsyncMock(spec=EmbeddingCache)
        mock_cache.get_embedding.return_value = None  # Cache miss
        mock_cache.set_embedding.return_value = True

        service = EmbeddingService(cache=mock_cache)

        # Mock the text model
        mock_model = Mock()
        mock_embedding = np.random.rand(384).astype(np.float32)
        mock_model.encode.return_value = mock_embedding
        service._text_model = mock_model

        instruction = "Pick up the red block"
        embedding = await service.get_instruction_embedding(instruction)

        assert embedding.shape == (384,)
        assert isinstance(embedding, np.ndarray)
        mock_model.encode.assert_called_once()
        mock_cache.set_embedding.assert_called_once()

    @pytest.mark.asyncio
    async def test_instruction_embedding_cache_hit(self):
        """Test cache hit for instruction embedding."""
        cached_embedding = np.random.rand(384).astype(np.float32)
        mock_cache = AsyncMock(spec=EmbeddingCache)
        mock_cache.get_embedding.return_value = cached_embedding

        service = EmbeddingService(cache=mock_cache)
        mock_model = Mock()
        service._text_model = mock_model

        instruction = "Pick up the red block"
        embedding = await service.get_instruction_embedding(instruction, use_cache=True)

        assert np.array_equal(embedding, cached_embedding)
        mock_model.encode.assert_not_called()  # Should not compute
        mock_cache.set_embedding.assert_not_called()  # Should not cache again

    @pytest.mark.asyncio
    async def test_instruction_embedding_cache_disabled(self):
        """Test embedding generation with cache disabled."""
        mock_cache = AsyncMock(spec=EmbeddingCache)
        service = EmbeddingService(cache=mock_cache)

        mock_model = Mock()
        mock_embedding = np.random.rand(384).astype(np.float32)
        mock_model.encode.return_value = mock_embedding
        service._text_model = mock_model

        instruction = "Pick up the red block"
        embedding = await service.get_instruction_embedding(instruction, use_cache=False)

        assert embedding.shape == (384,)
        mock_cache.get_embedding.assert_not_called()
        mock_cache.set_embedding.assert_not_called()

    @pytest.mark.asyncio
    async def test_instruction_embedding_empty_input(self):
        """Test error handling for empty instruction."""
        service = EmbeddingService()

        with pytest.raises(ValueError, match="Instruction cannot be empty"):
            await service.get_instruction_embedding("")

        with pytest.raises(ValueError, match="Instruction cannot be empty"):
            await service.get_instruction_embedding("   ")

    @pytest.mark.asyncio
    async def test_instruction_embedding_normalization(self):
        """Test that embeddings are normalized."""
        mock_cache = AsyncMock(spec=EmbeddingCache)
        mock_cache.get_embedding.return_value = None

        service = EmbeddingService(cache=mock_cache)

        mock_model = Mock()
        mock_embedding = np.random.rand(384).astype(np.float32)
        mock_model.encode.return_value = mock_embedding
        service._text_model = mock_model

        embedding = await service.get_instruction_embedding("Test instruction")

        # Check normalize_embeddings flag was passed
        call_kwargs = mock_model.encode.call_args[1]
        assert call_kwargs.get('normalize_embeddings') == True


class TestImageEmbedding:
    """Test image embedding generation."""

    @pytest.mark.asyncio
    async def test_image_embedding_pil(self):
        """Test generating embedding for PIL Image."""
        mock_cache = AsyncMock(spec=EmbeddingCache)
        mock_cache.get_embedding.return_value = None
        mock_cache.set_embedding.return_value = True

        service = EmbeddingService(cache=mock_cache)

        # Mock the image model and processor
        mock_processor = Mock()
        mock_inputs = {"pixel_values": Mock()}
        mock_inputs_tensor = Mock()
        mock_inputs_tensor.to.return_value = mock_inputs
        mock_processor.return_value = mock_inputs_tensor
        service._image_processor = mock_processor

        mock_model = Mock()
        mock_features = Mock()
        mock_features.norm.return_value = Mock()
        mock_normalized = np.random.rand(512).astype(np.float32)
        mock_features.__truediv__ = Mock(return_value=Mock(cpu=Mock(return_value=Mock(numpy=Mock(return_value=[mock_normalized])))))
        mock_model.get_image_features.return_value = mock_features
        service._image_model = mock_model

        image = Image.new('RGB', (224, 224), color='red')
        embedding = await service.get_image_embedding(image)

        assert embedding.shape == (512,)
        assert isinstance(embedding, np.ndarray)

    @pytest.mark.asyncio
    async def test_image_embedding_numpy(self):
        """Test generating embedding for numpy array image."""
        mock_cache = AsyncMock(spec=EmbeddingCache)
        mock_cache.get_embedding.return_value = None

        service = EmbeddingService(cache=mock_cache)
        service._image_processor = Mock()
        service._image_model = Mock()

        # Create numpy image (RGB)
        image_array = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)

        with patch.object(service, 'get_image_embedding', wraps=service.get_image_embedding) as mock_method:
            # Mock the actual embedding generation
            mock_embedding = np.random.rand(512).astype(np.float32)
            mock_method.return_value = mock_embedding

            embedding = await service.get_image_embedding(image_array)

            assert embedding.shape == (512,)

    @pytest.mark.asyncio
    async def test_image_embedding_bytes(self):
        """Test generating embedding for image bytes."""
        mock_cache = AsyncMock(spec=EmbeddingCache)
        mock_cache.get_embedding.return_value = None

        service = EmbeddingService(cache=mock_cache)

        # Create image bytes
        image = Image.new('RGB', (224, 224), color='blue')
        import io
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()

        with patch.object(service, 'get_image_embedding', wraps=service.get_image_embedding) as mock_method:
            mock_embedding = np.random.rand(512).astype(np.float32)
            mock_method.return_value = mock_embedding

            embedding = await service.get_image_embedding(img_bytes)

            assert embedding.shape == (512,)

    @pytest.mark.asyncio
    async def test_image_embedding_invalid_type(self):
        """Test error handling for invalid image type."""
        service = EmbeddingService()

        with pytest.raises(ValueError, match="Image must be PIL.Image, numpy array, or bytes"):
            await service.get_image_embedding("not_an_image")

    @pytest.mark.asyncio
    async def test_image_embedding_cache_hit(self):
        """Test cache hit for image embedding."""
        cached_embedding = np.random.rand(512).astype(np.float32)
        mock_cache = AsyncMock(spec=EmbeddingCache)
        mock_cache.get_embedding.return_value = cached_embedding

        service = EmbeddingService(cache=mock_cache)

        image = Image.new('RGB', (224, 224))
        embedding = await service.get_image_embedding(image)

        assert np.array_equal(embedding, cached_embedding)


class TestBatchEmbedding:
    """Test batch embedding generation."""

    @pytest.mark.asyncio
    async def test_batch_text_embeddings(self):
        """Test batch generation of text embeddings."""
        service = EmbeddingService()

        texts = [
            "Pick up the red block",
            "Move the blue cube",
            "Place the object on the table"
        ]

        with patch.object(service, 'get_instruction_embedding') as mock_method:
            mock_method.side_effect = [
                np.random.rand(384).astype(np.float32),
                np.random.rand(384).astype(np.float32),
                np.random.rand(384).astype(np.float32)
            ]

            results = await service.batch_generate_embeddings(texts=texts)

            assert 'text_embeddings' in results
            assert results['text_embeddings'].shape == (3, 384)
            assert mock_method.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_image_embeddings(self):
        """Test batch generation of image embeddings."""
        service = EmbeddingService()

        images = [
            Image.new('RGB', (224, 224), color='red'),
            Image.new('RGB', (224, 224), color='blue')
        ]

        with patch.object(service, 'get_image_embedding') as mock_method:
            mock_method.side_effect = [
                np.random.rand(512).astype(np.float32),
                np.random.rand(512).astype(np.float32)
            ]

            results = await service.batch_generate_embeddings(images=images)

            assert 'image_embeddings' in results
            assert results['image_embeddings'].shape == (2, 512)
            assert mock_method.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_mixed_embeddings(self):
        """Test batch generation of both text and image embeddings."""
        service = EmbeddingService()

        texts = ["Pick up", "Move"]
        images = [Image.new('RGB', (224, 224))]

        with patch.object(service, 'get_instruction_embedding') as mock_text, \
             patch.object(service, 'get_image_embedding') as mock_image:

            mock_text.side_effect = [
                np.random.rand(384).astype(np.float32),
                np.random.rand(384).astype(np.float32)
            ]
            mock_image.side_effect = [
                np.random.rand(512).astype(np.float32)
            ]

            results = await service.batch_generate_embeddings(texts=texts, images=images)

            assert 'text_embeddings' in results
            assert 'image_embeddings' in results
            assert results['text_embeddings'].shape == (2, 384)
            assert results['image_embeddings'].shape == (1, 512)


class TestSimilaritySearch:
    """Test similarity search functionality."""

    @pytest.mark.asyncio
    async def test_find_similar_instructions(self):
        """Test finding similar instructions via cosine similarity."""
        service = EmbeddingService()

        query_embedding = np.random.rand(384).astype(np.float32)
        mock_db = AsyncMock()

        # Mock database results
        mock_result = Mock()
        mock_rows = [
            Mock(similarity=0.95, id=1, instruction="Pick up red block"),
            Mock(similarity=0.87, id=2, instruction="Pick up blue block")
        ]
        mock_result.fetchall.return_value = mock_rows
        mock_db.execute.return_value = mock_result

        results = await service.find_similar_instructions(
            embedding=query_embedding,
            db=mock_db,
            top_k=10,
            threshold=0.7
        )

        assert len(results) == 2
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_similar_instructions_with_filters(self):
        """Test similarity search with filters."""
        service = EmbeddingService()

        query_embedding = np.random.rand(384).astype(np.float32)
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        filters = {"model_type": "openvla", "robot_type": "arm"}

        await service.find_similar_instructions(
            embedding=query_embedding,
            db=mock_db,
            filters=filters
        )

        # Check filters were included in query
        call_args = mock_db.execute.call_args
        query_params = call_args[0][1]
        assert query_params["model_type"] == "openvla"
        assert query_params["robot_type"] == "arm"

    @pytest.mark.asyncio
    async def test_find_similar_instructions_wrong_dimension(self):
        """Test error for wrong embedding dimension."""
        service = EmbeddingService()

        wrong_embedding = np.random.rand(512).astype(np.float32)  # Should be 384
        mock_db = AsyncMock()

        with pytest.raises(ValueError, match="Expected 384-dim embedding"):
            await service.find_similar_instructions(
                embedding=wrong_embedding,
                db=mock_db
            )

    @pytest.mark.asyncio
    async def test_find_similar_contexts(self):
        """Test finding similar visual contexts."""
        service = EmbeddingService()

        query_embedding = np.random.rand(512).astype(np.float32)
        mock_db = AsyncMock()

        mock_result = Mock()
        mock_rows = [
            Mock(similarity=0.92, id=1, scene_type="kitchen"),
            Mock(similarity=0.85, id=2, scene_type="workshop")
        ]
        mock_result.fetchall.return_value = mock_rows
        mock_db.execute.return_value = mock_result

        results = await service.find_similar_contexts(
            embedding=query_embedding,
            db=mock_db,
            top_k=5,
            threshold=0.8
        )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_find_similar_contexts_wrong_dimension(self):
        """Test error for wrong context embedding dimension."""
        service = EmbeddingService()

        wrong_embedding = np.random.rand(384).astype(np.float32)  # Should be 512
        mock_db = AsyncMock()

        with pytest.raises(ValueError, match="Expected 512-dim embedding"):
            await service.find_similar_contexts(
                embedding=wrong_embedding,
                db=mock_db
            )


class TestHashingAndCaching:
    """Test hashing and cache key generation."""

    def test_compute_hash_string(self):
        """Test hash computation for strings."""
        service = EmbeddingService()

        text = "Test instruction"
        hash1 = service._compute_hash(text)
        hash2 = service._compute_hash(text)

        assert hash1 == hash2  # Deterministic
        assert len(hash1) == 64  # SHA256 hex length

        # Different text produces different hash
        hash3 = service._compute_hash("Different instruction")
        assert hash1 != hash3

    def test_compute_hash_bytes(self):
        """Test hash computation for bytes."""
        service = EmbeddingService()

        data = b"Test data"
        hash1 = service._compute_hash(data)
        hash2 = service._compute_hash(data)

        assert hash1 == hash2
        assert len(hash1) == 64


class TestCleanup:
    """Test resource cleanup."""

    @patch('src.services.embeddings.embedding_service.torch.cuda.is_available')
    @patch('src.services.embeddings.embedding_service.torch.cuda.empty_cache')
    def test_cleanup_with_cuda(self, mock_empty_cache, mock_cuda_available):
        """Test cleanup releases GPU memory."""
        mock_cuda_available.return_value = True

        service = EmbeddingService()
        service._text_model = Mock()
        service._image_model = Mock()
        service._image_processor = Mock()

        service.cleanup()

        assert service._text_model is None
        assert service._image_model is None
        assert service._image_processor is None
        mock_empty_cache.assert_called_once()

    @patch('src.services.embeddings.embedding_service.torch.cuda.is_available')
    def test_cleanup_without_cuda(self, mock_cuda_available):
        """Test cleanup works without CUDA."""
        mock_cuda_available.return_value = False

        service = EmbeddingService()
        service._text_model = Mock()

        service.cleanup()  # Should not raise

        assert service._text_model is None
