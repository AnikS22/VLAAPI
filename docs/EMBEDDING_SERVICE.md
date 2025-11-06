# Embedding Service Documentation

## Overview

The VLA Platform's Embedding Service provides semantic similarity search capabilities for instructions and images using state-of-the-art machine learning models and pgvector for efficient vector search.

## Features

- **Text Embeddings**: 384-dimensional embeddings using `all-MiniLM-L6-v2`
- **Image Embeddings**: 512-dimensional embeddings using CLIP ViT-B/32
- **Redis Caching**: 5-minute TTL for hot embeddings
- **pgvector Search**: Cosine similarity and Euclidean distance search
- **Batch Processing**: Efficient batch embedding generation
- **Lazy Loading**: Models loaded only when needed

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    VLA Inference Pipeline                    │
├─────────────────────────────────────────────────────────────┤
│  Instruction + Image  →  VLA Model  →  Action + Embeddings  │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   EmbeddingService                           │
├──────────────────────┬──────────────────────────────────────┤
│  Text Model (384d)   │  Image Model (512d)                  │
│  all-MiniLM-L6-v2    │  CLIP ViT-B/32                      │
└──────────┬───────────┴──────────────────┬──────────────────┘
           │                               │
           ↓                               ↓
┌──────────────────────────┐    ┌─────────────────────────┐
│   EmbeddingCache (Redis)  │    │  pgvector (PostgreSQL)  │
│   TTL: 5 minutes          │    │  HNSW/IVFFlat indexes   │
└──────────────────────────┘    └─────────────────────────┘
```

## Installation

### Dependencies

```bash
# Install embedding service dependencies
pip install -r requirements-embeddings.txt
```

Required packages:
- `sentence-transformers>=2.2.2` - Text embeddings
- `transformers>=4.35.0` - CLIP image embeddings
- `torch>=2.0.0` - PyTorch backend
- `redis[hiredis]>=5.0.0` - Caching layer
- `psycopg2-binary>=2.9.9` - PostgreSQL with pgvector

### Database Setup

1. Install pgvector extension:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

2. Add embedding columns to tables:

```sql
-- Instruction embeddings (384 dimensions)
ALTER TABLE instruction_analytics
ADD COLUMN instruction_embedding vector(384);

-- Image embeddings (512 dimensions)
ALTER TABLE context_metadata
ADD COLUMN image_embedding vector(512);
```

3. Create indexes for fast similarity search:

```python
from src.utils.vector_search import create_hnsw_index

# HNSW index for instruction embeddings (best quality)
await create_hnsw_index(
    db=session,
    table="instruction_analytics",
    embedding_column="instruction_embedding",
    m=16,
    ef_construction=64,
    distance_metric="cosine"
)

# HNSW index for image embeddings
await create_hnsw_index(
    db=session,
    table="context_metadata",
    embedding_column="image_embedding",
    m=16,
    ef_construction=64,
    distance_metric="cosine"
)
```

### Redis Setup

```bash
# Start Redis server
redis-server

# Or with Docker
docker run -d -p 6379:6379 redis:latest
```

## Configuration

### Environment Variables

```bash
# Enable/disable embeddings
EMBEDDING_ENABLE_EMBEDDINGS=true

# Model selection
EMBEDDING_TEXT_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_IMAGE_MODEL_NAME=openai/clip-vit-base-patch32

# Device (cuda, cpu, or auto)
EMBEDDING_DEVICE=auto

# Redis configuration
EMBEDDING_REDIS_URL=redis://localhost:6379
EMBEDDING_CACHE_TTL=300
EMBEDDING_CACHE_MAX_CONNECTIONS=10

# Similarity search settings
EMBEDDING_SIMILARITY_THRESHOLD=0.7
EMBEDDING_SIMILARITY_TOP_K=10

# Index settings
EMBEDDING_USE_HNSW_INDEX=true
EMBEDDING_HNSW_M=16
EMBEDDING_HNSW_EF_CONSTRUCTION=64
```

### Python Configuration

```python
from src.config.embedding_config import embedding_config

# Check configuration
print(embedding_config.text_model_name)  # all-MiniLM-L6-v2
print(embedding_config.similarity_threshold)  # 0.7
print(embedding_config.use_hnsw_index)  # True
```

## Usage

### Basic Usage

```python
from src.services.embeddings import EmbeddingService, EmbeddingCache

# Initialize service
cache = EmbeddingCache(redis_url="redis://localhost:6379")
service = EmbeddingService(cache=cache)

# Generate instruction embedding
instruction = "pick up the red block"
embedding = await service.get_instruction_embedding(instruction)
print(embedding.shape)  # (384,)

# Generate image embedding
from PIL import Image
image = Image.open("robot_view.jpg")
image_emb = await service.get_image_embedding(image)
print(image_emb.shape)  # (512,)
```

### Similarity Search

```python
from src.utils.vector_search import cosine_similarity_search

# Find similar instructions
query_embedding = await service.get_instruction_embedding("grab the cube")

similar_instructions = await cosine_similarity_search(
    db=session,
    table="instruction_analytics",
    embedding_column="instruction_embedding",
    query_embedding=query_embedding,
    top_k=10,
    threshold=0.7,
    filters={"model_type": "openvla"}
)

for result in similar_instructions:
    print(f"{result['instruction']}: {result['similarity']:.3f}")
```

### Integration with VLA Inference

```python
from src.services.vla_inference import inference_service

# Enable embeddings in inference request
result = await inference_service.infer(
    model_id="openvla-7b",
    image=robot_image,
    instruction="pick up the red block",
    robot_type="franka_panda",
    generate_embeddings=True,  # Enable embedding generation
    customer_id="customer_123",
    analytics_id=456
)

# Access embeddings from result
if result.instruction_embedding is not None:
    print("Instruction embedding shape:", result.instruction_embedding.shape)
if result.image_embedding is not None:
    print("Image embedding shape:", result.image_embedding.shape)
```

### Batch Processing

```python
# Generate embeddings for multiple items
instructions = [
    "pick up the red block",
    "move the arm to the left",
    "place the object on the table"
]

images = [image1, image2, image3]

results = await service.batch_generate_embeddings(
    texts=instructions,
    images=images
)

print(results["text_embeddings"].shape)  # (3, 384)
print(results["image_embeddings"].shape)  # (3, 512)
```

### Indexing Embeddings

```python
from src.utils.vector_search import index_embedding, batch_index_embeddings

# Index single embedding
await index_embedding(
    db=session,
    table="instruction_analytics",
    id_column="id",
    id_value=123,
    embedding_column="instruction_embedding",
    embedding=instruction_embedding
)

# Batch index embeddings
embeddings = [
    {"id": 1, "embedding": emb1},
    {"id": 2, "embedding": emb2},
    {"id": 3, "embedding": emb3}
]

count = await batch_index_embeddings(
    db=session,
    table="instruction_analytics",
    id_column="id",
    embedding_column="instruction_embedding",
    embeddings=embeddings
)
print(f"Indexed {count} embeddings")
```

## Performance Optimization

### Caching Strategy

The embedding service uses Redis for caching with the following strategy:

- **TTL**: 5 minutes for hot embeddings
- **Key Format**: `embedding:instruction:{hash}` or `embedding:image:{hash}`
- **Automatic Invalidation**: Old embeddings expire automatically

```python
# Clear cache for specific pattern
await cache.clear_pattern("instruction:*")

# Get cache statistics
stats = await cache.get_stats()
print(f"Total keys: {stats['total_keys']}")
print(f"Memory used: {stats['memory_used']}")
```

### Index Selection

**HNSW (Recommended)**:
- Best recall quality
- Good for production workloads
- Higher memory usage
- Parameters: `m=16`, `ef_construction=64`

**IVFFlat (Alternative)**:
- Faster build time
- Lower memory usage
- Slightly lower recall
- Parameters: `lists=100` (for <1M rows)

```python
# Create IVFFlat index for faster builds
await create_ivfflat_index(
    db=session,
    table="instruction_analytics",
    embedding_column="instruction_embedding",
    lists=100,
    distance_metric="cosine"
)
```

### Model Performance

| Model | Dimension | Inference Time (CPU) | Inference Time (GPU) |
|-------|-----------|----------------------|----------------------|
| all-MiniLM-L6-v2 | 384 | ~15ms | ~3ms |
| CLIP ViT-B/32 | 512 | ~50ms | ~8ms |

## API Reference

### EmbeddingService

#### Methods

- `get_instruction_embedding(instruction: str, use_cache: bool = True) -> np.ndarray`
  - Generate 384-dim text embedding

- `get_image_embedding(image: Union[Image.Image, np.ndarray, bytes], use_cache: bool = True) -> np.ndarray`
  - Generate 512-dim image embedding

- `batch_generate_embeddings(texts: List[str], images: List[Image.Image]) -> dict`
  - Generate embeddings in batch

- `cleanup() -> None`
  - Clean up resources and GPU memory

### EmbeddingCache

#### Methods

- `get_embedding(key: str) -> Optional[np.ndarray]`
  - Retrieve cached embedding

- `set_embedding(key: str, embedding: np.ndarray, ttl: Optional[int] = None) -> bool`
  - Store embedding with TTL

- `get_many(keys: List[str]) -> dict[str, Optional[np.ndarray]]`
  - Batch retrieve embeddings

- `set_many(embeddings: dict[str, np.ndarray], ttl: Optional[int] = None) -> dict[str, bool]`
  - Batch store embeddings

### Vector Search Functions

- `cosine_similarity_search(db, table, embedding_column, query_embedding, top_k, threshold, filters) -> List[dict]`
  - Cosine similarity search with pgvector

- `euclidean_distance_search(db, table, embedding_column, query_embedding, top_k, max_distance, filters) -> List[dict]`
  - Euclidean distance search

- `index_embedding(db, table, id_column, id_value, embedding_column, embedding) -> bool`
  - Index single embedding

- `batch_index_embeddings(db, table, id_column, embedding_column, embeddings) -> int`
  - Batch index embeddings

## Testing

```bash
# Run unit tests
pytest tests/services/embeddings/

# Run integration tests (requires Redis and PostgreSQL)
pytest tests/services/embeddings/ -m integration

# Run with coverage
pytest tests/services/embeddings/ --cov=src/services/embeddings
```

## Monitoring

### Metrics

The embedding service integrates with Prometheus for monitoring:

- `embedding_generation_seconds` - Embedding generation latency
- `embedding_cache_hits_total` - Cache hit rate
- `embedding_cache_misses_total` - Cache miss rate
- `similarity_search_seconds` - Search latency
- `similarity_search_results` - Number of results returned

### Logging

```python
import logging

# Enable debug logging
logging.getLogger("src.services.embeddings").setLevel(logging.DEBUG)

# Log output
# DEBUG: Cache hit for instruction embedding: embedding:instruction:abc123
# DEBUG: Generated embedding shape: (384,)
# INFO: Found 8 similar instructions with similarity >= 0.7
```

## Troubleshooting

### Common Issues

**Issue: Out of memory on GPU**
```python
# Solution: Use CPU for embeddings
service = EmbeddingService(cache=cache, device="cpu")
```

**Issue: Slow similarity search**
```python
# Solution: Create HNSW index
await create_hnsw_index(db, "instruction_analytics", "instruction_embedding")
```

**Issue: Cache misses**
```python
# Solution: Increase TTL or check Redis connection
cache = EmbeddingCache(redis_url="redis://localhost:6379", ttl=600)
stats = await cache.get_stats()
print(stats)  # Check if Redis is connected
```

**Issue: Models downloading slowly**
```python
# Solution: Pre-download models
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
```

## Best Practices

1. **Enable caching** for production workloads
2. **Use HNSW indexes** for best search quality
3. **Batch process** embeddings when possible
4. **Monitor cache hit rate** to optimize TTL
5. **Generate embeddings asynchronously** to avoid blocking inference
6. **Respect user consent** before storing embeddings
7. **Clean up resources** with `service.cleanup()` when done

## References

- [sentence-transformers documentation](https://www.sbert.net/)
- [CLIP documentation](https://github.com/openai/CLIP)
- [pgvector documentation](https://github.com/pgvector/pgvector)
- [Redis documentation](https://redis.io/docs/)

## Support

For issues or questions:
- Open an issue on GitHub
- Check the FAQ in the main documentation
- Contact the VLA Platform team
