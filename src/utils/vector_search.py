"""
pgvector helper functions for similarity search and indexing.
Provides utilities for cosine similarity search and embedding management.
"""

import logging
from typing import List, Optional, Any, Dict
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


async def cosine_similarity_search(
    db: AsyncSession,
    table: str,
    embedding_column: str,
    query_embedding: np.ndarray,
    top_k: int = 10,
    threshold: float = 0.0,
    filters: Optional[Dict[str, Any]] = None,
    select_columns: str = "*"
) -> List[Dict]:
    """
    Perform cosine similarity search using pgvector.

    Args:
        db: Async database session
        table: Table name to search
        embedding_column: Column name containing embeddings
        query_embedding: Query embedding vector
        top_k: Number of results to return
        threshold: Minimum similarity threshold (0-1)
        filters: Optional WHERE clause filters
        select_columns: Columns to select (default: all)

    Returns:
        List of result dictionaries with similarity scores

    Example:
        results = await cosine_similarity_search(
            db=session,
            table="instruction_analytics",
            embedding_column="instruction_embedding",
            query_embedding=np.array([0.1, 0.2, ...]),
            top_k=10,
            threshold=0.7,
            filters={"model_type": "openvla"}
        )
    """
    if query_embedding is None or len(query_embedding) == 0:
        raise ValueError("Query embedding cannot be empty")

    if not isinstance(query_embedding, np.ndarray):
        query_embedding = np.array(query_embedding)

    logger.info(f"Cosine similarity search on {table}.{embedding_column}, top_k={top_k}, threshold={threshold}")

    try:
        # Build query with pgvector cosine distance operator (<=>)
        # Similarity = 1 - cosine_distance
        query = f"""
            SELECT {select_columns},
                   1 - ({embedding_column} <=> :embedding) as similarity
            FROM {table}
            WHERE {embedding_column} IS NOT NULL
        """

        # Build parameters
        params = {
            "embedding": query_embedding.tolist(),
            "threshold": threshold,
            "top_k": top_k
        }

        # Add filters
        if filters:
            for key, value in filters.items():
                query += f" AND {key} = :{key}"
                params[key] = value

        # Add threshold filter
        query += f" AND (1 - ({embedding_column} <=> :embedding)) >= :threshold"

        # Order by similarity (ascending distance = descending similarity)
        query += f"""
            ORDER BY {embedding_column} <=> :embedding
            LIMIT :top_k
        """

        # Execute query
        result = await db.execute(text(query), params)
        rows = result.fetchall()

        # Convert to list of dicts
        results = []
        for row in rows:
            row_dict = dict(row._mapping)
            results.append(row_dict)

        logger.info(f"Found {len(results)} results with similarity >= {threshold}")
        return results

    except Exception as e:
        logger.error(f"Cosine similarity search failed: {e}")
        raise


async def euclidean_distance_search(
    db: AsyncSession,
    table: str,
    embedding_column: str,
    query_embedding: np.ndarray,
    top_k: int = 10,
    max_distance: Optional[float] = None,
    filters: Optional[Dict[str, Any]] = None,
    select_columns: str = "*"
) -> List[Dict]:
    """
    Perform Euclidean distance search using pgvector.

    Args:
        db: Async database session
        table: Table name to search
        embedding_column: Column name containing embeddings
        query_embedding: Query embedding vector
        top_k: Number of results to return
        max_distance: Maximum distance threshold
        filters: Optional WHERE clause filters
        select_columns: Columns to select

    Returns:
        List of result dictionaries with distance scores
    """
    if query_embedding is None or len(query_embedding) == 0:
        raise ValueError("Query embedding cannot be empty")

    if not isinstance(query_embedding, np.ndarray):
        query_embedding = np.array(query_embedding)

    logger.info(f"Euclidean distance search on {table}.{embedding_column}, top_k={top_k}")

    try:
        # Build query with pgvector L2 distance operator (<->)
        query = f"""
            SELECT {select_columns},
                   {embedding_column} <-> :embedding as distance
            FROM {table}
            WHERE {embedding_column} IS NOT NULL
        """

        # Build parameters
        params = {
            "embedding": query_embedding.tolist(),
            "top_k": top_k
        }

        # Add filters
        if filters:
            for key, value in filters.items():
                query += f" AND {key} = :{key}"
                params[key] = value

        # Add distance threshold if provided
        if max_distance is not None:
            query += f" AND ({embedding_column} <-> :embedding) <= :max_distance"
            params["max_distance"] = max_distance

        # Order by distance (ascending)
        query += f"""
            ORDER BY {embedding_column} <-> :embedding
            LIMIT :top_k
        """

        # Execute query
        result = await db.execute(text(query), params)
        rows = result.fetchall()

        # Convert to list of dicts
        results = []
        for row in rows:
            row_dict = dict(row._mapping)
            results.append(row_dict)

        logger.info(f"Found {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"Euclidean distance search failed: {e}")
        raise


async def index_embedding(
    db: AsyncSession,
    table: str,
    id_column: str,
    id_value: Any,
    embedding_column: str,
    embedding: np.ndarray
) -> bool:
    """
    Insert or update embedding in pgvector column.

    Args:
        db: Async database session
        table: Table name
        id_column: Primary key column name
        id_value: Primary key value
        embedding_column: Column name for embedding
        embedding: Embedding vector to store

    Returns:
        True if successful, False otherwise

    Example:
        success = await index_embedding(
            db=session,
            table="instruction_analytics",
            id_column="id",
            id_value=123,
            embedding_column="instruction_embedding",
            embedding=np.array([0.1, 0.2, ...])
        )
    """
    if embedding is None or len(embedding) == 0:
        raise ValueError("Embedding cannot be empty")

    if not isinstance(embedding, np.ndarray):
        embedding = np.array(embedding)

    logger.debug(f"Indexing embedding for {table}.{id_column}={id_value}")

    try:
        # Update embedding using pgvector syntax
        query = f"""
            UPDATE {table}
            SET {embedding_column} = :embedding
            WHERE {id_column} = :id_value
        """

        params = {
            "embedding": embedding.tolist(),
            "id_value": id_value
        }

        result = await db.execute(text(query), params)
        await db.commit()

        if result.rowcount > 0:
            logger.debug(f"Successfully indexed embedding for {table}.{id_column}={id_value}")
            return True
        else:
            logger.warning(f"No rows updated for {table}.{id_column}={id_value}")
            return False

    except Exception as e:
        logger.error(f"Failed to index embedding: {e}")
        await db.rollback()
        raise


async def batch_index_embeddings(
    db: AsyncSession,
    table: str,
    id_column: str,
    embedding_column: str,
    embeddings: List[Dict[str, Any]]
) -> int:
    """
    Batch insert/update embeddings for efficiency.

    Args:
        db: Async database session
        table: Table name
        id_column: Primary key column name
        embedding_column: Column name for embeddings
        embeddings: List of dicts with 'id' and 'embedding' keys

    Returns:
        Number of successfully indexed embeddings

    Example:
        count = await batch_index_embeddings(
            db=session,
            table="instruction_analytics",
            id_column="id",
            embedding_column="instruction_embedding",
            embeddings=[
                {"id": 1, "embedding": np.array([...])},
                {"id": 2, "embedding": np.array([...])}
            ]
        )
    """
    if not embeddings:
        logger.warning("No embeddings to index")
        return 0

    logger.info(f"Batch indexing {len(embeddings)} embeddings for {table}")

    try:
        success_count = 0

        # Use a single transaction for all updates
        for item in embeddings:
            id_value = item["id"]
            embedding = item["embedding"]

            if not isinstance(embedding, np.ndarray):
                embedding = np.array(embedding)

            query = f"""
                UPDATE {table}
                SET {embedding_column} = :embedding
                WHERE {id_column} = :id_value
            """

            params = {
                "embedding": embedding.tolist(),
                "id_value": id_value
            }

            result = await db.execute(text(query), params)
            if result.rowcount > 0:
                success_count += 1

        await db.commit()
        logger.info(f"Successfully indexed {success_count}/{len(embeddings)} embeddings")
        return success_count

    except Exception as e:
        logger.error(f"Batch indexing failed: {e}")
        await db.rollback()
        raise


async def create_ivfflat_index(
    db: AsyncSession,
    table: str,
    embedding_column: str,
    index_name: Optional[str] = None,
    lists: int = 100,
    distance_metric: str = "cosine"
) -> bool:
    """
    Create IVFFlat index for approximate nearest neighbor search.
    IVFFlat provides faster search at the cost of some accuracy.

    Args:
        db: Async database session
        table: Table name
        embedding_column: Column name containing embeddings
        index_name: Optional custom index name
        lists: Number of inverted lists (default: 100, good for <1M rows)
        distance_metric: 'cosine', 'l2', or 'inner_product'

    Returns:
        True if successful

    Note:
        Recommended lists values:
        - <100k rows: 100
        - 100k-1M rows: 1000
        - 1M-10M rows: 10000
    """
    if index_name is None:
        index_name = f"{table}_{embedding_column}_ivfflat_idx"

    # Map distance metric to pgvector operator
    operator_map = {
        "cosine": "vector_cosine_ops",
        "l2": "vector_l2_ops",
        "inner_product": "vector_ip_ops"
    }

    if distance_metric not in operator_map:
        raise ValueError(f"Invalid distance metric: {distance_metric}")

    ops = operator_map[distance_metric]

    logger.info(f"Creating IVFFlat index {index_name} on {table}.{embedding_column} (lists={lists}, metric={distance_metric})")

    try:
        # Create IVFFlat index
        query = f"""
            CREATE INDEX IF NOT EXISTS {index_name}
            ON {table}
            USING ivfflat ({embedding_column} {ops})
            WITH (lists = {lists})
        """

        await db.execute(text(query))
        await db.commit()

        logger.info(f"Successfully created index {index_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to create IVFFlat index: {e}")
        await db.rollback()
        raise


async def create_hnsw_index(
    db: AsyncSession,
    table: str,
    embedding_column: str,
    index_name: Optional[str] = None,
    m: int = 16,
    ef_construction: int = 64,
    distance_metric: str = "cosine"
) -> bool:
    """
    Create HNSW index for high-quality approximate nearest neighbor search.
    HNSW provides better recall than IVFFlat but uses more memory.

    Args:
        db: Async database session
        table: Table name
        embedding_column: Column name containing embeddings
        index_name: Optional custom index name
        m: Number of connections per layer (default: 16, range: 2-100)
        ef_construction: Size of dynamic candidate list (default: 64, range: 4-1000)
        distance_metric: 'cosine', 'l2', or 'inner_product'

    Returns:
        True if successful

    Note:
        Recommended parameters:
        - m=16, ef_construction=64: Good balance (default)
        - m=32, ef_construction=128: Better recall, more memory
        - m=8, ef_construction=32: Less memory, lower recall
    """
    if index_name is None:
        index_name = f"{table}_{embedding_column}_hnsw_idx"

    # Map distance metric to pgvector operator
    operator_map = {
        "cosine": "vector_cosine_ops",
        "l2": "vector_l2_ops",
        "inner_product": "vector_ip_ops"
    }

    if distance_metric not in operator_map:
        raise ValueError(f"Invalid distance metric: {distance_metric}")

    ops = operator_map[distance_metric]

    logger.info(f"Creating HNSW index {index_name} on {table}.{embedding_column} (m={m}, ef_construction={ef_construction}, metric={distance_metric})")

    try:
        # Create HNSW index
        query = f"""
            CREATE INDEX IF NOT EXISTS {index_name}
            ON {table}
            USING hnsw ({embedding_column} {ops})
            WITH (m = {m}, ef_construction = {ef_construction})
        """

        await db.execute(text(query))
        await db.commit()

        logger.info(f"Successfully created index {index_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to create HNSW index: {e}")
        await db.rollback()
        raise


async def get_embedding_stats(
    db: AsyncSession,
    table: str,
    embedding_column: str
) -> Dict[str, Any]:
    """
    Get statistics about embeddings in a table.

    Args:
        db: Async database session
        table: Table name
        embedding_column: Column name containing embeddings

    Returns:
        Dict with statistics (count, dimension, null_count, etc.)
    """
    logger.info(f"Getting embedding stats for {table}.{embedding_column}")

    try:
        # Query for embedding statistics
        query = f"""
            SELECT
                COUNT(*) as total_rows,
                COUNT({embedding_column}) as embedding_count,
                COUNT(*) - COUNT({embedding_column}) as null_count,
                (SELECT vector_dims({embedding_column}) FROM {table} WHERE {embedding_column} IS NOT NULL LIMIT 1) as dimension
            FROM {table}
        """

        result = await db.execute(text(query))
        row = result.fetchone()

        stats = {
            "table": table,
            "column": embedding_column,
            "total_rows": row.total_rows,
            "embedding_count": row.embedding_count,
            "null_count": row.null_count,
            "dimension": row.dimension,
            "coverage": row.embedding_count / row.total_rows if row.total_rows > 0 else 0.0
        }

        logger.info(f"Embedding stats: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Failed to get embedding stats: {e}")
        raise
