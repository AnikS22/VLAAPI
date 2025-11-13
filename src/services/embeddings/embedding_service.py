"""
Embedding Service for VLA Platform
Handles text and image embeddings with model lazy loading and caching.
"""

import logging
from typing import List, Optional, Union
import numpy as np
import torch
from PIL import Image
import hashlib
import io

from src.models.database import InstructionAnalytics, ContextMetadata
from .embedding_cache import EmbeddingCache

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating and managing embeddings for instructions and images.

    Features:
    - Lazy loading of ML models
    - Redis caching for embeddings (5-min TTL)
    - pgvector similarity search
    - Support for both text (384-dim) and image (512-dim) embeddings
    """

    def __init__(
        self,
        cache: Optional[EmbeddingCache] = None,
        text_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        image_model_name: str = "openai/clip-vit-base-patch32",
        device: Optional[str] = None
    ):
        """
        Initialize the embedding service.

        Args:
            cache: Optional EmbeddingCache instance
            text_model_name: HuggingFace model name for text embeddings
            image_model_name: HuggingFace model name for image embeddings
            device: Device to run models on ('cuda', 'cpu', or None for auto)
        """
        self.cache = cache or EmbeddingCache()
        self.text_model_name = text_model_name
        self.image_model_name = image_model_name

        # Lazy loading - models initialized on first use
        self._text_model = None
        self._image_model = None
        self._image_processor = None

        # Device selection
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"EmbeddingService initialized with device: {self.device}")

    @property
    def text_model(self):
        """Lazy load text embedding model (all-MiniLM-L6-v2, 384-dim)."""
        if self._text_model is None:
            logger.info(f"Loading text model: {self.text_model_name}")
            try:
                from sentence_transformers import SentenceTransformer
                self._text_model = SentenceTransformer(self.text_model_name)
                self._text_model.to(self.device)
                logger.info("Text model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load text model: {e}")
                raise
        return self._text_model

    @property
    def image_model(self):
        """Lazy load image embedding model (CLIP ViT-B/32, 512-dim)."""
        if self._image_model is None:
            logger.info(f"Loading image model: {self.image_model_name}")
            try:
                from transformers import CLIPModel
                self._image_model = CLIPModel.from_pretrained(self.image_model_name)
                self._image_model.to(self.device)
                self._image_model.eval()
                logger.info("Image model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load image model: {e}")
                raise
        return self._image_model

    @property
    def image_processor(self):
        """Lazy load image processor for CLIP."""
        if self._image_processor is None:
            logger.info("Loading CLIP processor")
            try:
                from transformers import CLIPProcessor
                self._image_processor = CLIPProcessor.from_pretrained(self.image_model_name)
                logger.info("CLIP processor loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load CLIP processor: {e}")
                raise
        return self._image_processor

    def _compute_hash(self, data: Union[str, bytes]) -> str:
        """Compute SHA256 hash for caching keys."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return hashlib.sha256(data).hexdigest()

    async def get_instruction_embedding(
        self,
        instruction: str,
        use_cache: bool = True
    ) -> np.ndarray:
        """
        Generate 384-dimensional embedding for instruction text.

        Args:
            instruction: Natural language instruction
            use_cache: Whether to use Redis cache

        Returns:
            384-dimensional numpy array
        """
        if not instruction or not instruction.strip():
            raise ValueError("Instruction cannot be empty")

        # Check cache first
        if use_cache:
            cache_key = f"instruction:{self._compute_hash(instruction)}"
            cached = await self.cache.get_embedding(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for instruction embedding: {cache_key}")
                return cached

        # Generate embedding
        logger.debug(f"Generating embedding for instruction: {instruction[:50]}...")
        try:
            # SentenceTransformer handles batching internally
            embedding = self.text_model.encode(
                instruction,
                convert_to_numpy=True,
                normalize_embeddings=True
            )

            # Cache the result
            if use_cache:
                await self.cache.set_embedding(cache_key, embedding)

            logger.debug(f"Generated embedding shape: {embedding.shape}")
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate instruction embedding: {e}")
            raise

    async def get_image_embedding(
        self,
        image: Union[Image.Image, np.ndarray, bytes],
        use_cache: bool = True
    ) -> np.ndarray:
        """
        Generate 512-dimensional CLIP embedding for image.

        Args:
            image: PIL Image, numpy array, or raw bytes
            use_cache: Whether to use Redis cache

        Returns:
            512-dimensional numpy array
        """
        # Convert to PIL Image if needed
        if isinstance(image, bytes):
            image = Image.open(io.BytesIO(image))
        elif isinstance(image, np.ndarray):
            image = Image.fromarray(image)

        if not isinstance(image, Image.Image):
            raise ValueError("Image must be PIL.Image, numpy array, or bytes")

        # Compute hash for caching
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='PNG')
        image_hash = self._compute_hash(image_bytes.getvalue())

        # Check cache
        if use_cache:
            cache_key = f"image:{image_hash}"
            cached = await self.cache.get_embedding(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for image embedding: {cache_key}")
                return cached

        # Generate embedding
        logger.debug("Generating CLIP image embedding")
        try:
            # Process image
            inputs = self.image_processor(
                images=image,
                return_tensors="pt"
            ).to(self.device)

            # Generate embedding
            with torch.no_grad():
                image_features = self.image_model.get_image_features(**inputs)
                # Normalize
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                embedding = image_features.cpu().numpy()[0]

            # Cache the result
            if use_cache:
                await self.cache.set_embedding(cache_key, embedding)

            logger.debug(f"Generated image embedding shape: {embedding.shape}")
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate image embedding: {e}")
            raise

    async def find_similar_instructions(
        self,
        embedding: np.ndarray,
        db,
        top_k: int = 10,
        threshold: float = 0.7,
        filters: Optional[dict] = None
    ) -> List[InstructionAnalytics]:
        """
        Find similar instructions using pgvector cosine similarity.

        Args:
            embedding: Query embedding (384-dim)
            db: Database session
            top_k: Number of results to return
            threshold: Minimum similarity threshold (0-1)
            filters: Optional filters (e.g., {'model_type': 'openvla'})

        Returns:
            List of InstructionAnalytics objects ordered by similarity
        """
        if embedding.shape[0] != 384:
            raise ValueError(f"Expected 384-dim embedding, got {embedding.shape[0]}")

        logger.info(f"Searching for top {top_k} similar instructions")

        try:
            from sqlalchemy import text, and_

            # Build query with pgvector cosine similarity
            # Note: <=> is pgvector's cosine distance operator
            query = """
                SELECT *,
                       1 - (instruction_embedding <=> :embedding) as similarity
                FROM instruction_analytics
                WHERE instruction_embedding IS NOT NULL
            """

            # Add filters
            filter_conditions = []
            params = {"embedding": embedding.tolist(), "top_k": top_k, "threshold": threshold}

            if filters:
                for key, value in filters.items():
                    filter_conditions.append(f"{key} = :{key}")
                    params[key] = value

            if filter_conditions:
                query += " AND " + " AND ".join(filter_conditions)

            query += """
                AND (1 - (instruction_embedding <=> :embedding)) >= :threshold
                ORDER BY instruction_embedding <=> :embedding
                LIMIT :top_k
            """

            result = await db.execute(text(query), params)
            rows = result.fetchall()

            logger.info(f"Found {len(rows)} similar instructions")

            # Convert to InstructionAnalytics objects
            similar_instructions = []
            for row in rows:
                instruction = InstructionAnalytics(**dict(row))
                # Add similarity score as attribute
                instruction.similarity = row.similarity
                similar_instructions.append(instruction)

            return similar_instructions

        except Exception as e:
            logger.error(f"Failed to search similar instructions: {e}")
            raise

    async def find_similar_contexts(
        self,
        embedding: np.ndarray,
        db,
        top_k: int = 10,
        threshold: float = 0.7,
        filters: Optional[dict] = None
    ) -> List[ContextMetadata]:
        """
        Find similar visual contexts using pgvector cosine similarity.

        Args:
            embedding: Query embedding (512-dim CLIP)
            db: Database session
            top_k: Number of results to return
            threshold: Minimum similarity threshold (0-1)
            filters: Optional filters (e.g., {'robot_type': 'arm'})

        Returns:
            List of ContextMetadata objects ordered by similarity
        """
        if embedding.shape[0] != 512:
            raise ValueError(f"Expected 512-dim embedding, got {embedding.shape[0]}")

        logger.info(f"Searching for top {top_k} similar contexts")

        try:
            from sqlalchemy import text

            # Build query with pgvector cosine similarity
            query = """
                SELECT *,
                       1 - (image_embedding <=> :embedding) as similarity
                FROM context_metadata
                WHERE image_embedding IS NOT NULL
            """

            # Add filters
            filter_conditions = []
            params = {"embedding": embedding.tolist(), "top_k": top_k, "threshold": threshold}

            if filters:
                for key, value in filters.items():
                    filter_conditions.append(f"{key} = :{key}")
                    params[key] = value

            if filter_conditions:
                query += " AND " + " AND ".join(filter_conditions)

            query += """
                AND (1 - (image_embedding <=> :embedding)) >= :threshold
                ORDER BY image_embedding <=> :embedding
                LIMIT :top_k
            """

            result = await db.execute(text(query), params)
            rows = result.fetchall()

            logger.info(f"Found {len(rows)} similar contexts")

            # Convert to ContextMetadata objects
            similar_contexts = []
            for row in rows:
                context = ContextMetadata(**dict(row))
                # Add similarity score as attribute
                context.similarity = row.similarity
                similar_contexts.append(context)

            return similar_contexts

        except Exception as e:
            logger.error(f"Failed to search similar contexts: {e}")
            raise

    async def batch_generate_embeddings(
        self,
        texts: Optional[List[str]] = None,
        images: Optional[List[Union[Image.Image, np.ndarray]]] = None,
        use_cache: bool = True
    ) -> dict:
        """
        Generate embeddings in batch for efficiency.

        Args:
            texts: List of text instructions
            images: List of images
            use_cache: Whether to use cache

        Returns:
            Dict with 'text_embeddings' and/or 'image_embeddings' keys
        """
        results = {}

        if texts:
            logger.info(f"Batch generating {len(texts)} text embeddings")
            text_embeddings = []
            for text in texts:
                emb = await self.get_instruction_embedding(text, use_cache=use_cache)
                text_embeddings.append(emb)
            results['text_embeddings'] = np.array(text_embeddings)

        if images:
            logger.info(f"Batch generating {len(images)} image embeddings")
            image_embeddings = []
            for img in images:
                emb = await self.get_image_embedding(img, use_cache=use_cache)
                image_embeddings.append(emb)
            results['image_embeddings'] = np.array(image_embeddings)

        return results

    def cleanup(self):
        """Clean up resources and clear GPU memory."""
        logger.info("Cleaning up embedding service resources")

        if self._text_model is not None:
            del self._text_model
            self._text_model = None

        if self._image_model is not None:
            del self._image_model
            self._image_model = None

        if self._image_processor is not None:
            del self._image_processor
            self._image_processor = None

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Cleanup complete")
