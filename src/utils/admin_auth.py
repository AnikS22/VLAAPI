"""Admin authentication and authorization utilities."""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from src.models.database import User
from src.utils.auth import get_current_user_from_token
from src.core.database import get_db


async def get_current_admin_user(
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Verify that the current user is an admin/superuser.

    Args:
        current_user: The authenticated user from JWT token
        db: Database session

    Returns:
        User object if user is admin

    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized. Admin access required."
        )

    return current_user
