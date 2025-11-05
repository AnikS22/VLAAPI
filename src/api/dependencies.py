"""FastAPI dependencies for dependency injection."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.core.redis_client import get_redis
from src.middleware.authentication import get_current_api_key
from src.middleware.rate_limiting import check_rate_limit

# Database session dependency
async def get_db() -> AsyncSession:
    """Get database session."""
    async for session in get_db_session():
        yield session


# Convenience dependency that combines authentication and rate limiting
async def get_authenticated_user(
    api_key = Depends(check_rate_limit)
):
    """Get authenticated and rate-limited API key.

    This dependency performs both authentication and rate limiting.
    """
    return api_key


__all__ = [
    "get_db",
    "get_authenticated_user",
    "get_redis",
]
