"""Admin API routes for consent management."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.core.dependencies import get_redis
from src.models.contracts.consent import (
    AnonymizationLevel,
    ConsentTier,
    ConsentUpdate,
    CustomerDataConsentContract,
)
from src.services.consent import get_consent_manager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/customers",
    tags=["admin", "consent"],
    responses={
        401: {"description": "Unauthorized - Invalid or missing API key"},
        403: {"description": "Forbidden - Insufficient permissions"},
        404: {"description": "Customer not found"},
    },
)


@router.get("/{customer_id}/consent", response_model=CustomerDataConsentContract)
async def get_customer_consent(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> CustomerDataConsentContract:
    """Get customer data consent preferences.

    Retrieves current consent settings for a customer including:
    - Consent tier level
    - Data storage permissions
    - Anonymization level
    - Expiration date

    Args:
        customer_id: Customer UUID
        db: Database session
        redis: Redis client

    Returns:
        Current consent contract

    Raises:
        HTTPException: 404 if customer doesn't exist
    """
    try:
        consent_manager = get_consent_manager(redis)
        consent = await consent_manager.get_consent(str(customer_id), db)

        logger.info(f"Retrieved consent for customer {customer_id}")
        return consent

    except ValueError as e:
        logger.error(f"Invalid customer ID {customer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid customer ID format: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Failed to get consent for customer {customer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customer consent",
        )


@router.post("/{customer_id}/consent", response_model=CustomerDataConsentContract)
async def update_customer_consent(
    customer_id: UUID,
    consent_update: ConsentUpdate,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> CustomerDataConsentContract:
    """Update customer data consent preferences.

    Allows administrators to update consent settings for a customer.
    Validates that permissions are consistent with the consent tier.

    **Consent Tier Logic**:
    - NONE: No data storage or processing allowed
    - BASIC: Store only necessary operational data
    - ANALYTICS: Store data for service improvement (embeddings allowed)
    - RESEARCH: Full data usage including ML training

    Args:
        customer_id: Customer UUID
        consent_update: New consent settings
        db: Database session
        redis: Redis client

    Returns:
        Updated consent contract

    Raises:
        HTTPException: 400 if consent logic is invalid
        HTTPException: 404 if customer doesn't exist
        HTTPException: 500 on internal error
    """
    try:
        consent_manager = get_consent_manager(redis)

        # Update consent with validation
        updated_consent = await consent_manager.update_consent(
            customer_id=str(customer_id),
            db=db,
            tier=consent_update.consent_tier,
            can_store_images=consent_update.can_store_images,
            can_store_embeddings=consent_update.can_store_embeddings,
            can_use_for_training=consent_update.can_use_for_training,
            anonymization_level=consent_update.anonymization_level,
            expires_at=consent_update.expires_at,
        )

        logger.info(
            f"Updated consent for customer {customer_id} to tier {consent_update.consent_tier}"
        )
        return updated_consent

    except ValueError as e:
        logger.warning(f"Invalid consent update for customer {customer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid consent configuration: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Failed to update consent for customer {customer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update customer consent",
        )


@router.delete("/{customer_id}/consent", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_customer_consent(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> None:
    """Revoke all customer data consent.

    Sets customer consent to NONE tier and disables all data permissions.
    This is equivalent to customer requesting complete data opt-out.

    Args:
        customer_id: Customer UUID
        db: Database session
        redis: Redis client

    Raises:
        HTTPException: 404 if customer doesn't exist
        HTTPException: 500 on internal error
    """
    try:
        consent_manager = get_consent_manager(redis)
        await consent_manager.revoke_consent(str(customer_id), db)

        logger.info(f"Revoked consent for customer {customer_id}")

    except Exception as e:
        logger.error(f"Failed to revoke consent for customer {customer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke customer consent",
        )


@router.get("/{customer_id}/consent/permissions")
async def check_customer_permissions(
    customer_id: UUID,
    check: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """Check specific customer data permissions.

    Query parameters:
    - check: Permission to check (images, embeddings, training, anonymization)

    Args:
        customer_id: Customer UUID
        check: Optional permission type to check
        db: Database session
        redis: Redis client

    Returns:
        Permission check results
    """
    try:
        consent_manager = get_consent_manager(redis)

        if check == "images":
            allowed = await consent_manager.can_store_images(str(customer_id), db)
            return {"permission": "store_images", "allowed": allowed}

        elif check == "embeddings":
            allowed = await consent_manager.can_store_embeddings(str(customer_id), db)
            return {"permission": "store_embeddings", "allowed": allowed}

        elif check == "training":
            allowed = await consent_manager.can_use_for_training(str(customer_id), db)
            return {"permission": "use_for_training", "allowed": allowed}

        elif check == "anonymization":
            level = await consent_manager.get_anonymization_level(str(customer_id), db)
            return {"permission": "anonymization_level", "level": level.value}

        else:
            # Return all permissions
            can_images = await consent_manager.can_store_images(str(customer_id), db)
            can_embeddings = await consent_manager.can_store_embeddings(
                str(customer_id), db
            )
            can_training = await consent_manager.can_use_for_training(
                str(customer_id), db
            )
            anon_level = await consent_manager.get_anonymization_level(
                str(customer_id), db
            )

            return {
                "customer_id": str(customer_id),
                "permissions": {
                    "can_store_images": can_images,
                    "can_store_embeddings": can_embeddings,
                    "can_use_for_training": can_training,
                    "anonymization_level": anon_level.value,
                },
            }

    except Exception as e:
        logger.error(f"Failed to check permissions for customer {customer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check customer permissions",
        )
