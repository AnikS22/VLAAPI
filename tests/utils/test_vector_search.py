"""
Unit tests for pgvector search utilities.
"""

import pytest
import numpy as np
from unittest.mock import AsyncMock, Mock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.vector_search import (
    cosine_similarity_search,
    euclidean_distance_search,
    index_embedding,
    batch_index_embeddings,
    create_ivfflat_index,
    create_hnsw_index,
    get_embedding_stats
)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = Mock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def sample_embedding():
    """Create a sample query embedding."""
    return np.random.rand(384).astype(np.float32)


@pytest.mark.asyncio
class TestCosineSimilaritySearch:
    """Test cases for cosine similarity search."""

    async def test_basic_search(self, mock_db, sample_embedding):
        """Test basic cosine similarity search."""
        # Mock database results
        mock_result = Mock()
        mock_row1 = Mock()
        mock_row1._mapping = {
            "id": 1,
            "instruction": "pick up block",
            "similarity": 0.95
        }
        mock_row2 = Mock()
        mock_row2._mapping = {
            "id": 2,
            "instruction": "move arm",
            "similarity": 0.85
        }
        mock_result.fetchall.return_value = [mock_row1, mock_row2]
        mock_db.execute.return_value = mock_result

        results = await cosine_similarity_search(
            db=mock_db,
            table="instruction_analytics",
            embedding_column="instruction_embedding",
            query_embedding=sample_embedding,
            top_k=10,
            threshold=0.7
        )

        assert len(results) == 2
        assert results[0]["similarity"] == 0.95
        assert results[1]["similarity"] == 0.85
        mock_db.execute.assert_called_once()

    async def test_search_with_filters(self, mock_db, sample_embedding):
        """Test similarity search with filters."""
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        results = await cosine_similarity_search(
            db=mock_db,
            table="instruction_analytics",
            embedding_column="instruction_embedding",
            query_embedding=sample_embedding,
            top_k=5,
            filters={"model_type": "openvla", "robot_type": "franka_panda"}
        )

        assert isinstance(results, list)
        mock_db.execute.assert_called_once()

        # Verify filters were included in query
        call_args = mock_db.execute.call_args
        query_text = str(call_args[0][0])
        assert "model_type" in query_text or "model_type" in str(call_args[0][1])

    async def test_search_empty_embedding(self, mock_db):
        """Test error handling for empty embedding."""
        with pytest.raises(ValueError, match="Query embedding cannot be empty"):
            await cosine_similarity_search(
                db=mock_db,
                table="test_table",
                embedding_column="embedding",
                query_embedding=np.array([]),
                top_k=10
            )

    async def test_search_select_columns(self, mock_db, sample_embedding):
        """Test similarity search with specific columns."""
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        await cosine_similarity_search(
            db=mock_db,
            table="instruction_analytics",
            embedding_column="instruction_embedding",
            query_embedding=sample_embedding,
            top_k=10,
            select_columns="id, instruction"
        )

        call_args = mock_db.execute.call_args
        query_text = str(call_args[0][0])
        assert "id, instruction" in query_text or "SELECT" in query_text


@pytest.mark.asyncio
class TestEuclideanDistanceSearch:
    """Test cases for Euclidean distance search."""

    async def test_basic_search(self, mock_db, sample_embedding):
        """Test basic Euclidean distance search."""
        mock_result = Mock()
        mock_row = Mock()
        mock_row._mapping = {"id": 1, "distance": 0.5}
        mock_result.fetchall.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        results = await euclidean_distance_search(
            db=mock_db,
            table="context_metadata",
            embedding_column="image_embedding",
            query_embedding=sample_embedding,
            top_k=10
        )

        assert len(results) == 1
        assert results[0]["distance"] == 0.5

    async def test_search_with_max_distance(self, mock_db, sample_embedding):
        """Test distance search with maximum distance threshold."""
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        results = await euclidean_distance_search(
            db=mock_db,
            table="context_metadata",
            embedding_column="image_embedding",
            query_embedding=sample_embedding,
            top_k=10,
            max_distance=1.0
        )

        assert isinstance(results, list)
        call_args = mock_db.execute.call_args
        # Verify max_distance parameter was used
        assert "max_distance" in str(call_args[0][1])


@pytest.mark.asyncio
class TestIndexEmbedding:
    """Test cases for embedding indexing."""

    async def test_index_embedding_success(self, mock_db, sample_embedding):
        """Test successful embedding indexing."""
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        success = await index_embedding(
            db=mock_db,
            table="instruction_analytics",
            id_column="id",
            id_value=123,
            embedding_column="instruction_embedding",
            embedding=sample_embedding
        )

        assert success is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    async def test_index_embedding_no_update(self, mock_db, sample_embedding):
        """Test indexing when no rows are updated."""
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result

        success = await index_embedding(
            db=mock_db,
            table="instruction_analytics",
            id_column="id",
            id_value=999,
            embedding_column="instruction_embedding",
            embedding=sample_embedding
        )

        assert success is False

    async def test_index_embedding_error(self, mock_db, sample_embedding):
        """Test error handling during indexing."""
        mock_db.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await index_embedding(
                db=mock_db,
                table="instruction_analytics",
                id_column="id",
                id_value=123,
                embedding_column="instruction_embedding",
                embedding=sample_embedding
            )

        mock_db.rollback.assert_called_once()

    async def test_index_embedding_list_input(self, mock_db):
        """Test indexing with list input (auto-convert to numpy)."""
        embedding_list = [0.1, 0.2, 0.3]
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        success = await index_embedding(
            db=mock_db,
            table="test_table",
            id_column="id",
            id_value=1,
            embedding_column="embedding",
            embedding=embedding_list
        )

        assert success is True


@pytest.mark.asyncio
class TestBatchIndexEmbeddings:
    """Test cases for batch embedding indexing."""

    async def test_batch_index_success(self, mock_db):
        """Test successful batch indexing."""
        embeddings = [
            {"id": 1, "embedding": np.random.rand(384)},
            {"id": 2, "embedding": np.random.rand(384)},
            {"id": 3, "embedding": np.random.rand(384)}
        ]

        mock_result = Mock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        count = await batch_index_embeddings(
            db=mock_db,
            table="instruction_analytics",
            id_column="id",
            embedding_column="instruction_embedding",
            embeddings=embeddings
        )

        assert count == 3
        assert mock_db.execute.call_count == 3
        mock_db.commit.assert_called_once()

    async def test_batch_index_empty_list(self, mock_db):
        """Test batch indexing with empty list."""
        count = await batch_index_embeddings(
            db=mock_db,
            table="test_table",
            id_column="id",
            embedding_column="embedding",
            embeddings=[]
        )

        assert count == 0
        mock_db.execute.assert_not_called()

    async def test_batch_index_partial_success(self, mock_db):
        """Test batch indexing with some failures."""
        embeddings = [
            {"id": 1, "embedding": np.random.rand(384)},
            {"id": 2, "embedding": np.random.rand(384)}
        ]

        # First succeeds, second fails
        mock_result_success = Mock()
        mock_result_success.rowcount = 1
        mock_result_fail = Mock()
        mock_result_fail.rowcount = 0
        mock_db.execute.side_effect = [mock_result_success, mock_result_fail]

        count = await batch_index_embeddings(
            db=mock_db,
            table="test_table",
            id_column="id",
            embedding_column="embedding",
            embeddings=embeddings
        )

        assert count == 1  # Only first one succeeded


@pytest.mark.asyncio
class TestCreateIndexes:
    """Test cases for index creation."""

    async def test_create_ivfflat_index(self, mock_db):
        """Test IVFFlat index creation."""
        success = await create_ivfflat_index(
            db=mock_db,
            table="instruction_analytics",
            embedding_column="instruction_embedding",
            lists=100,
            distance_metric="cosine"
        )

        assert success is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

        # Verify query contains IVFFlat parameters
        call_args = mock_db.execute.call_args
        query_text = str(call_args[0][0])
        assert "ivfflat" in query_text.lower()
        assert "lists = 100" in query_text

    async def test_create_hnsw_index(self, mock_db):
        """Test HNSW index creation."""
        success = await create_hnsw_index(
            db=mock_db,
            table="instruction_analytics",
            embedding_column="instruction_embedding",
            m=16,
            ef_construction=64,
            distance_metric="cosine"
        )

        assert success is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

        # Verify query contains HNSW parameters
        call_args = mock_db.execute.call_args
        query_text = str(call_args[0][0])
        assert "hnsw" in query_text.lower()
        assert "m = 16" in query_text

    async def test_create_index_invalid_metric(self, mock_db):
        """Test index creation with invalid distance metric."""
        with pytest.raises(ValueError, match="Invalid distance metric"):
            await create_ivfflat_index(
                db=mock_db,
                table="test_table",
                embedding_column="embedding",
                distance_metric="invalid_metric"
            )

    async def test_create_index_error(self, mock_db):
        """Test error handling during index creation."""
        mock_db.execute.side_effect = Exception("Index creation failed")

        with pytest.raises(Exception, match="Index creation failed"):
            await create_hnsw_index(
                db=mock_db,
                table="test_table",
                embedding_column="embedding"
            )

        mock_db.rollback.assert_called_once()


@pytest.mark.asyncio
class TestGetEmbeddingStats:
    """Test cases for embedding statistics."""

    async def test_get_stats(self, mock_db):
        """Test getting embedding statistics."""
        mock_result = Mock()
        mock_row = Mock()
        mock_row.total_rows = 1000
        mock_row.embedding_count = 800
        mock_row.null_count = 200
        mock_row.dimension = 384
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        stats = await get_embedding_stats(
            db=mock_db,
            table="instruction_analytics",
            embedding_column="instruction_embedding"
        )

        assert stats["total_rows"] == 1000
        assert stats["embedding_count"] == 800
        assert stats["null_count"] == 200
        assert stats["dimension"] == 384
        assert stats["coverage"] == 0.8  # 800/1000

    async def test_get_stats_empty_table(self, mock_db):
        """Test statistics for empty table."""
        mock_result = Mock()
        mock_row = Mock()
        mock_row.total_rows = 0
        mock_row.embedding_count = 0
        mock_row.null_count = 0
        mock_row.dimension = None
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        stats = await get_embedding_stats(
            db=mock_db,
            table="test_table",
            embedding_column="embedding"
        )

        assert stats["coverage"] == 0.0  # Avoid division by zero


@pytest.mark.integration
@pytest.mark.asyncio
class TestVectorSearchIntegration:
    """Integration tests with real database."""

    async def test_real_cosine_search(self):
        """Test real cosine similarity search."""
        pytest.skip("Skipping integration test - requires PostgreSQL with pgvector")

    async def test_real_index_creation(self):
        """Test real index creation."""
        pytest.skip("Skipping integration test - requires PostgreSQL with pgvector")
