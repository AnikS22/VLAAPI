"""User profile management endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routers.auth import get_current_user
from src.core.database import get_db_session
from src.models.database import Customer, User
from src.utils.auth import hash_password, verify_password

router = APIRouter(prefix="/users", tags=["Users"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class UserProfileResponse(BaseModel):
    """User profile with customer information."""

    user_id: uuid.UUID
    email: str
    full_name: str | None
    email_verified: bool
    is_active: bool
    created_at: str

    # Customer information
    customer_id: uuid.UUID | None
    company_name: str | None
    tier: str | None
    monthly_quota: int | None
    monthly_usage: int | None


class UpdateProfileRequest(BaseModel):
    """Update user profile request."""

    full_name: str | None = Field(None, description="User's full name")
    company_name: str | None = Field(None, description="Company name")


class ChangePasswordRequest(BaseModel):
    """Change password request."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get("/me/profile", response_model=UserProfileResponse)
async def get_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserProfileResponse:
    """Get current user's profile with customer information.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        UserProfileResponse with user and customer data
    """
    # Get customer linked to this user
    result = await db.execute(
        select(Customer).where(Customer.user_id == current_user.user_id)
    )
    customer = result.scalar_one_or_none()

    return UserProfileResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        full_name=current_user.full_name,
        email_verified=current_user.email_verified,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat(),
        customer_id=customer.customer_id if customer else None,
        company_name=customer.company_name if customer else None,
        tier=customer.tier if customer else None,
        monthly_quota=customer.monthly_quota if customer else None,
        monthly_usage=customer.monthly_usage if customer else None,
    )


@router.patch("/me/profile", response_model=UserProfileResponse)
async def update_user_profile(
    request: UpdateProfileRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserProfileResponse:
    """Update current user's profile.

    Args:
        request: Profile update request
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated UserProfileResponse
    """
    # Update user fields
    if request.full_name is not None:
        current_user.full_name = request.full_name

    # Update customer company name if provided
    if request.company_name is not None:
        result = await db.execute(
            select(Customer).where(Customer.user_id == current_user.user_id)
        )
        customer = result.scalar_one_or_none()

        if customer:
            customer.company_name = request.company_name

    await db.commit()
    await db.refresh(current_user)

    # Get updated customer
    result = await db.execute(
        select(Customer).where(Customer.user_id == current_user.user_id)
    )
    customer = result.scalar_one_or_none()

    return UserProfileResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        full_name=current_user.full_name,
        email_verified=current_user.email_verified,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat(),
        customer_id=customer.customer_id if customer else None,
        company_name=customer.company_name if customer else None,
        tier=customer.tier if customer else None,
        monthly_quota=customer.monthly_quota if customer else None,
        monthly_usage=customer.monthly_usage if customer else None,
    )


@router.post("/me/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> MessageResponse:
    """Change current user's password.

    Args:
        request: Change password request
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If current password is incorrect
    """
    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Update password
    current_user.hashed_password = hash_password(request.new_password)
    await db.commit()

    return MessageResponse(message="Password changed successfully")


@router.delete("/me", response_model=MessageResponse)
async def delete_user_account(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> MessageResponse:
    """Delete current user's account (soft delete - marks as inactive).

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message
    """
    # Soft delete: mark as inactive instead of hard delete
    current_user.is_active = False
    await db.commit()

    return MessageResponse(message="Account deactivated successfully")
