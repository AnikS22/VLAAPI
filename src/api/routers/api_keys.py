"""API key management endpoints for customers."""

import hashlib
import secrets
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routers.auth import get_current_user
from src.core.config import get_settings
from src.core.database import get_db_session
from src.models.database import APIKey, Customer, User

router = APIRouter(prefix="/v1/api-keys", tags=["API Keys"])
settings = get_settings()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class CreateAPIKeyRequest(BaseModel):
    """Create API key request."""

    key_name: str = Field(..., max_length=100, description="Friendly name for the API key")
    scopes: list[str] = Field(
        default=["inference"],
        description="Key scopes: inference, admin"
    )
    expires_in_days: int | None = Field(
        None,
        ge=1,
        le=365,
        description="Expiration in days (None = never expires)"
    )


class APIKeyResponse(BaseModel):
    """API key response (without the secret key)."""

    key_id: uuid.UUID
    key_name: str | None
    key_prefix: str
    scopes: list[str]
    created_at: str
    last_used_at: str | None
    expires_at: str | None
    is_active: bool


class CreatedAPIKeyResponse(APIKeyResponse):
    """Response when creating a new API key (includes full key once)."""

    api_key: str = Field(..., description="Full API key (only shown once!)")


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def generate_api_key(prefix: str = "vla_live") -> tuple[str, str, str]:
    """Generate a new API key.

    Args:
        prefix: Key prefix (vla_live or vla_test)

    Returns:
        Tuple of (full_key, key_prefix, key_hash)
    """
    # Generate random suffix (32 bytes = 64 hex chars)
    random_suffix = secrets.token_hex(32)

    # Create full key: prefix_randomsuffix
    full_key = f"{prefix}_{random_suffix}"

    # Key prefix: first 12 characters (e.g., "vla_live_abc")
    key_prefix = full_key[:12]

    # Hash for storage (SHA-256)
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()

    return full_key, key_prefix, key_hash


async def get_customer_for_user(
    user: User,
    db: AsyncSession
) -> Customer:
    """Get customer associated with user.

    Args:
        user: User object
        db: Database session

    Returns:
        Customer object

    Raises:
        HTTPException: If customer not found
    """
    result = await db.execute(
        select(Customer).where(Customer.user_id == user.user_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer profile not found"
        )

    return customer


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get("", response_model=list[APIKeyResponse])
async def list_api_keys(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[APIKeyResponse]:
    """List all API keys for the current user's customer account.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of APIKeyResponse objects
    """
    customer = await get_customer_for_user(current_user, db)

    # Get all API keys for this customer
    result = await db.execute(
        select(APIKey)
        .where(APIKey.customer_id == customer.customer_id)
        .order_by(APIKey.created_at.desc())
    )
    api_keys = result.scalars().all()

    return [
        APIKeyResponse(
            key_id=key.key_id,
            key_name=key.key_name,
            key_prefix=key.key_prefix,
            scopes=key.scopes,
            created_at=key.created_at.isoformat(),
            last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
            expires_at=key.expires_at.isoformat() if key.expires_at else None,
            is_active=key.is_active,
        )
        for key in api_keys
    ]


@router.post("", response_model=CreatedAPIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: CreateAPIKeyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CreatedAPIKeyResponse:
    """Create a new API key for the current user's customer account.

    WARNING: The full API key is only returned once! Store it securely.

    Args:
        request: Create API key request
        current_user: Current authenticated user
        db: Database session

    Returns:
        CreatedAPIKeyResponse with the full API key (shown only once!)
    """
    customer = await get_customer_for_user(current_user, db)

    # Validate scopes
    valid_scopes = {"inference", "admin"}
    for scope in request.scopes:
        if scope not in valid_scopes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scope: {scope}. Valid scopes: {valid_scopes}"
            )

    # Generate API key
    full_key, key_prefix, key_hash = generate_api_key(prefix=settings.api_key_prefix)

    # Calculate expiration
    expires_at = None
    if request.expires_in_days:
        from datetime import timedelta
        expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)

    # Create API key record
    api_key = APIKey(
        key_id=uuid.uuid4(),
        customer_id=customer.customer_id,
        key_prefix=key_prefix,
        key_hash=key_hash,
        key_name=request.key_name,
        scopes=request.scopes,
        expires_at=expires_at,
        is_active=True,
    )

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return CreatedAPIKeyResponse(
        key_id=api_key.key_id,
        key_name=api_key.key_name,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        created_at=api_key.created_at.isoformat(),
        last_used_at=None,
        expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
        is_active=api_key.is_active,
        api_key=full_key,  # Only shown once!
    )


@router.patch("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    key_name: Annotated[str, Body(..., max_length=100, embed=True)],
) -> APIKeyResponse:
    """Update API key name.

    Args:
        key_id: API key UUID
        key_name: New name for the key
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated APIKeyResponse

    Raises:
        HTTPException: If key not found or not owned by user
    """
    customer = await get_customer_for_user(current_user, db)

    # Get API key
    result = await db.execute(
        select(APIKey)
        .where(APIKey.key_id == key_id)
        .where(APIKey.customer_id == customer.customer_id)
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    # Update name
    api_key.key_name = key_name
    await db.commit()
    await db.refresh(api_key)

    return APIKeyResponse(
        key_id=api_key.key_id,
        key_name=api_key.key_name,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        created_at=api_key.created_at.isoformat(),
        last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
        is_active=api_key.is_active,
    )


@router.delete("/{key_id}", response_model=MessageResponse)
async def revoke_api_key(
    key_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> MessageResponse:
    """Revoke (deactivate) an API key.

    Args:
        key_id: API key UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If key not found or not owned by user
    """
    customer = await get_customer_for_user(current_user, db)

    # Get API key
    result = await db.execute(
        select(APIKey)
        .where(APIKey.key_id == key_id)
        .where(APIKey.customer_id == customer.customer_id)
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    # Soft delete: mark as inactive
    api_key.is_active = False
    await db.commit()

    return MessageResponse(message="API key revoked successfully")
