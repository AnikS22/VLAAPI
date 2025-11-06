"""Consent management service for privacy compliance."""

import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.contracts.consent import (
    AnonymizationLevel,
    ConsentTier,
    CustomerDataConsentContract,
)
from src.models.database import CustomerDataConsent

logger = logging.getLogger(__name__)


class ConsentManager:
    """Manager for customer data consent with Redis caching."""

    CACHE_TTL_SECONDS = 600  # 10-minute cache TTL
    CACHE_KEY_PREFIX = "consent:"

    def __init__(self, redis_client):
        """Initialize consent manager.

        Args:
            redis_client: Redis client for caching
        """
        self.redis = redis_client

    def _get_cache_key(self, customer_id: str) -> str:
        """Generate Redis cache key for customer consent.

        Args:
            customer_id: Customer identifier

        Returns:
            Redis cache key
        """
        return f"{self.CACHE_KEY_PREFIX}{customer_id}"

    async def get_consent(
        self, customer_id: str, db: AsyncSession
    ) -> CustomerDataConsentContract:
        """Get customer consent from cache or database.

        Args:
            customer_id: Customer identifier
            db: Database session

        Returns:
            Customer consent contract (defaults to NONE if not found)
        """
        cache_key = self._get_cache_key(customer_id)

        # Try Redis cache first
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                logger.debug(f"Consent cache hit for customer {customer_id}")
                consent_dict = json.loads(cached)
                return CustomerDataConsentContract(**consent_dict)
        except Exception as e:
            logger.warning(f"Redis cache read failed: {e}")

        # Fall back to database
        try:
            result = await db.execute(
                select(CustomerDataConsent).where(
                    CustomerDataConsent.customer_id == UUID(customer_id)
                )
            )
            consent_record = result.scalar_one_or_none()

            if consent_record:
                consent = CustomerDataConsentContract(
                    customer_id=str(consent_record.customer_id),
                    consent_tier=ConsentTier(consent_record.consent_tier),
                    can_store_images=consent_record.can_store_images,
                    can_store_embeddings=consent_record.can_store_embeddings,
                    can_use_for_training=consent_record.can_use_for_training,
                    anonymization_level=AnonymizationLevel(
                        consent_record.anonymization_level
                    ),
                    consent_granted_at=consent_record.consent_granted_at,
                    consent_updated_at=consent_record.consent_updated_at,
                    expires_at=consent_record.expires_at,
                )

                # Cache for future requests
                try:
                    await self.redis.setex(
                        cache_key,
                        self.CACHE_TTL_SECONDS,
                        json.dumps(consent.model_dump(mode="json")),
                    )
                except Exception as e:
                    logger.warning(f"Redis cache write failed: {e}")

                return consent
            else:
                # No consent found, return default (NONE)
                logger.info(f"No consent found for customer {customer_id}, using default")
                return CustomerDataConsentContract(
                    customer_id=customer_id,
                    consent_tier=ConsentTier.NONE,
                )

        except Exception as e:
            logger.error(f"Failed to retrieve consent for customer {customer_id}: {e}")
            # Return safe default on error
            return CustomerDataConsentContract(
                customer_id=customer_id,
                consent_tier=ConsentTier.NONE,
            )

    async def can_store_images(self, customer_id: str, db: AsyncSession) -> bool:
        """Check if customer consent allows image storage.

        Args:
            customer_id: Customer identifier
            db: Database session

        Returns:
            True if images can be stored
        """
        consent = await self.get_consent(customer_id, db)
        return consent.can_store_images and not consent.is_expired

    async def can_store_embeddings(self, customer_id: str, db: AsyncSession) -> bool:
        """Check if customer consent allows embedding storage.

        Args:
            customer_id: Customer identifier
            db: Database session

        Returns:
            True if embeddings can be stored
        """
        consent = await self.get_consent(customer_id, db)
        # Embeddings require at least ANALYTICS tier
        return (
            consent.can_store_embeddings
            and consent.consent_tier
            in [ConsentTier.ANALYTICS, ConsentTier.RESEARCH]
            and not consent.is_expired
        )

    async def can_use_for_training(self, customer_id: str, db: AsyncSession) -> bool:
        """Check if customer consent allows using data for training.

        Args:
            customer_id: Customer identifier
            db: Database session

        Returns:
            True if data can be used for training
        """
        consent = await self.get_consent(customer_id, db)
        # Training requires RESEARCH tier
        return (
            consent.can_use_for_training
            and consent.consent_tier == ConsentTier.RESEARCH
            and not consent.is_expired
        )

    async def get_anonymization_level(
        self, customer_id: str, db: AsyncSession
    ) -> AnonymizationLevel:
        """Get anonymization level for customer data.

        Args:
            customer_id: Customer identifier
            db: Database session

        Returns:
            Anonymization level
        """
        consent = await self.get_consent(customer_id, db)
        return consent.anonymization_level

    async def update_consent(
        self,
        customer_id: str,
        db: AsyncSession,
        tier: ConsentTier,
        can_store_images: bool = False,
        can_store_embeddings: bool = False,
        can_use_for_training: bool = False,
        anonymization_level: AnonymizationLevel = AnonymizationLevel.FULL,
        expires_at: Optional[datetime] = None,
    ) -> CustomerDataConsentContract:
        """Update customer consent preferences.

        Args:
            customer_id: Customer identifier
            db: Database session
            tier: Consent tier
            can_store_images: Permission to store images
            can_store_embeddings: Permission to store embeddings
            can_use_for_training: Permission to use for training
            anonymization_level: Level of anonymization
            expires_at: Optional expiration date

        Returns:
            Updated consent contract

        Raises:
            ValueError: If consent tier and permissions are inconsistent
        """
        # Validate consent tier logic
        self._validate_consent_logic(
            tier,
            can_store_images,
            can_store_embeddings,
            can_use_for_training,
        )

        customer_uuid = UUID(customer_id)

        # Check if consent record exists
        result = await db.execute(
            select(CustomerDataConsent).where(
                CustomerDataConsent.customer_id == customer_uuid
            )
        )
        existing_consent = result.scalar_one_or_none()

        now = datetime.utcnow()

        if existing_consent:
            # Update existing consent
            await db.execute(
                update(CustomerDataConsent)
                .where(CustomerDataConsent.customer_id == customer_uuid)
                .values(
                    consent_tier=tier.value,
                    can_store_images=can_store_images,
                    can_store_embeddings=can_store_embeddings,
                    can_use_for_training=can_use_for_training,
                    anonymization_level=anonymization_level.value,
                    consent_updated_at=now,
                    expires_at=expires_at,
                )
            )
            logger.info(f"Updated consent for customer {customer_id} to tier {tier.value}")
        else:
            # Create new consent record
            new_consent = CustomerDataConsent(
                customer_id=customer_uuid,
                consent_tier=tier.value,
                can_store_images=can_store_images,
                can_store_embeddings=can_store_embeddings,
                can_use_for_training=can_use_for_training,
                anonymization_level=anonymization_level.value,
                consent_granted_at=now,
                consent_updated_at=now,
                expires_at=expires_at,
            )
            db.add(new_consent)
            logger.info(f"Created consent for customer {customer_id} with tier {tier.value}")

        await db.commit()

        # Invalidate cache
        cache_key = self._get_cache_key(customer_id)
        try:
            await self.redis.delete(cache_key)
            logger.debug(f"Invalidated consent cache for customer {customer_id}")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {e}")

        # Return updated consent
        return await self.get_consent(customer_id, db)

    def _validate_consent_logic(
        self,
        tier: ConsentTier,
        can_store_images: bool,
        can_store_embeddings: bool,
        can_use_for_training: bool,
    ) -> None:
        """Validate that consent permissions match tier level.

        Args:
            tier: Consent tier
            can_store_images: Image storage permission
            can_store_embeddings: Embedding storage permission
            can_use_for_training: Training usage permission

        Raises:
            ValueError: If permissions are inconsistent with tier
        """
        if tier == ConsentTier.NONE:
            if can_store_images or can_store_embeddings or can_use_for_training:
                raise ValueError("NONE tier cannot have any data permissions enabled")

        if tier == ConsentTier.BASIC:
            if can_use_for_training:
                raise ValueError("BASIC tier cannot allow training data usage")
            if can_store_embeddings:
                raise ValueError("BASIC tier cannot allow embedding storage")

        if tier == ConsentTier.ANALYTICS:
            if can_use_for_training:
                raise ValueError("ANALYTICS tier cannot allow training data usage")

        # RESEARCH tier allows all permissions
        if tier == ConsentTier.RESEARCH and can_use_for_training:
            if not (can_store_images or can_store_embeddings):
                raise ValueError(
                    "RESEARCH tier with training enabled requires image or embedding storage"
                )

    async def revoke_consent(self, customer_id: str, db: AsyncSession) -> None:
        """Revoke all customer data consent.

        Args:
            customer_id: Customer identifier
            db: Database session
        """
        await self.update_consent(
            customer_id=customer_id,
            db=db,
            tier=ConsentTier.NONE,
            can_store_images=False,
            can_store_embeddings=False,
            can_use_for_training=False,
            anonymization_level=AnonymizationLevel.FULL,
        )
        logger.info(f"Revoked consent for customer {customer_id}")


# Global consent manager (initialized with Redis client)
_consent_manager: Optional[ConsentManager] = None


def get_consent_manager(redis_client) -> ConsentManager:
    """Get or create consent manager instance.

    Args:
        redis_client: Redis client for caching

    Returns:
        ConsentManager instance
    """
    global _consent_manager
    if _consent_manager is None:
        _consent_manager = ConsentManager(redis_client)
    return _consent_manager
