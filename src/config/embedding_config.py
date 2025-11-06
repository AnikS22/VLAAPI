"""
Configuration for embedding models and cache settings.
"""

from typing import Dict, Any
from pydantic import BaseSettings, Field


class EmbeddingConfig(BaseSettings):
    """Configuration for embedding service."""

    # Enable/disable embedding generation
    enable_embeddings: bool = Field(
        default=True,
        description="Enable embedding generation for analytics"
    )

    # Text embedding model
    text_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="HuggingFace model for text embeddings (384-dim)"
    )

    # Image embedding model
    image_model_name: str = Field(
        default="openai/clip-vit-base-patch32",
        description="HuggingFace model for image embeddings (512-dim)"
    )

    # Device selection
    embedding_device: str = Field(
        default="auto",
        description="Device for embedding models: 'cuda', 'cpu', or 'auto'"
    )

    # Redis cache settings
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL for embedding cache"
    )

    embedding_cache_ttl: int = Field(
        default=300,
        description="Cache TTL in seconds (default: 5 minutes)"
    )

    embedding_cache_max_connections: int = Field(
        default=10,
        description="Maximum Redis connections in pool"
    )

    # Similarity search settings
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold for search results"
    )

    similarity_top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of similar results to return"
    )

    # pgvector index settings
    use_hnsw_index: bool = Field(
        default=True,
        description="Use HNSW index (better quality) vs IVFFlat (faster)"
    )

    hnsw_m: int = Field(
        default=16,
        ge=2,
        le=100,
        description="HNSW index parameter: connections per layer"
    )

    hnsw_ef_construction: int = Field(
        default=64,
        ge=4,
        le=1000,
        description="HNSW index parameter: construction candidate list size"
    )

    ivfflat_lists: int = Field(
        default=100,
        ge=1,
        description="IVFFlat index parameter: number of inverted lists"
    )

    # Batch processing
    embedding_batch_size: int = Field(
        default=32,
        ge=1,
        le=128,
        description="Batch size for embedding generation"
    )

    # Model download settings
    huggingface_cache_dir: str = Field(
        default=".cache/huggingface",
        description="Directory for caching HuggingFace models"
    )

    class Config:
        env_prefix = "EMBEDDING_"
        case_sensitive = False


# Global embedding configuration instance
embedding_config = EmbeddingConfig()


def get_embedding_model_config() -> Dict[str, Any]:
    """
    Get embedding model configuration as dictionary.

    Returns:
        Dict with model names, dimensions, and settings
    """
    return {
        "text": {
            "model_name": embedding_config.text_model_name,
            "dimension": 384,
            "description": "all-MiniLM-L6-v2 for instruction embeddings"
        },
        "image": {
            "model_name": embedding_config.image_model_name,
            "dimension": 512,
            "description": "CLIP ViT-B/32 for image embeddings"
        },
        "cache": {
            "redis_url": embedding_config.redis_url,
            "ttl_seconds": embedding_config.embedding_cache_ttl,
            "max_connections": embedding_config.embedding_cache_max_connections
        },
        "search": {
            "threshold": embedding_config.similarity_threshold,
            "top_k": embedding_config.similarity_top_k,
            "use_hnsw": embedding_config.use_hnsw_index
        },
        "device": embedding_config.embedding_device
    }


def get_index_config() -> Dict[str, Any]:
    """
    Get pgvector index configuration.

    Returns:
        Dict with index type and parameters
    """
    if embedding_config.use_hnsw_index:
        return {
            "type": "hnsw",
            "params": {
                "m": embedding_config.hnsw_m,
                "ef_construction": embedding_config.hnsw_ef_construction
            },
            "description": "High-quality approximate nearest neighbor search"
        }
    else:
        return {
            "type": "ivfflat",
            "params": {
                "lists": embedding_config.ivfflat_lists
            },
            "description": "Fast approximate nearest neighbor search"
        }
