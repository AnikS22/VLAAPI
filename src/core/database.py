"""Database connection management with async SQLAlchemy."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.core.config import settings


class DatabaseManager:
    """Manages database connection and session lifecycle."""

    def __init__(self):
        """Initialize database manager."""
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def initialize(self) -> None:
        """Initialize database engine and session factory.

        This should be called during application startup.
        """
        # Create async engine with connection pooling
        self._engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,  # Log SQL queries in debug mode
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            pool_recycle=settings.database_pool_recycle,
            pool_pre_ping=True,  # Verify connections before use
            future=True,
        )

        # Create session factory
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Don't expire objects after commit
            autocommit=False,
            autoflush=False,
        )

    async def close(self) -> None:
        """Close database engine and cleanup connections.

        This should be called during application shutdown.
        """
        if self._engine:
            await self._engine.dispose()

    @property
    def engine(self) -> AsyncEngine:
        """Get database engine.

        Returns:
            AsyncEngine: SQLAlchemy async engine

        Raises:
            RuntimeError: If engine not initialized
        """
        if not self._engine:
            raise RuntimeError(
                "Database engine not initialized. Call initialize() first."
            )
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get session factory.

        Returns:
            async_sessionmaker: Session factory for creating new sessions

        Raises:
            RuntimeError: If session factory not initialized
        """
        if not self._session_factory:
            raise RuntimeError(
                "Session factory not initialized. Call initialize() first."
            )
        return self._session_factory

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session as async context manager.

        Yields:
            AsyncSession: Database session

        Example:
            ```python
            async with db_manager.get_session() as session:
                result = await session.execute(select(Customer))
                customers = result.scalars().all()
            ```
        """
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def health_check(self) -> bool:
        """Check database connectivity.

        Returns:
            bool: True if database is healthy, False otherwise
        """
        try:
            async with self.get_session() as session:
                await session.execute("SELECT 1")
            return True
        except Exception:
            return False


# Global database manager instance
db_manager = DatabaseManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.

    Yields:
        AsyncSession: Database session

    Example:
        ```python
        @app.get("/customers")
        async def get_customers(session: AsyncSession = Depends(get_db_session)):
            result = await session.execute(select(Customer))
            return result.scalars().all()
        ```
    """
    async with db_manager.get_session() as session:
        yield session


async def init_db() -> None:
    """Initialize database connection.

    This should be called during application startup.
    """
    db_manager.initialize()


async def close_db() -> None:
    """Close database connection.

    This should be called during application shutdown.
    """
    await db_manager.close()
