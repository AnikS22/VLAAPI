"""Customer data consent contracts.

Pydantic models for customer consent management and privacy compliance.
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum


class ConsentTier(str, Enum):
    """Consent tier levels."""
    NONE = "none"           # No data collection beyond required
    METADATA = "metadata"   # Collect metadata and embeddings
    FULL = "full"           # Full data collection including images


class AnonymizationLevel(str, Enum):
    """Anonymization levels for data protection."""
    NONE = "none"           # No anonymization
    PARTIAL = "partial"     # Remove PII, keep robot-specific data
    FULL = "full"           # Full anonymization


class CustomerDataConsentContract(BaseModel):
    """Customer consent for data collection and usage.

    CRITICAL for privacy compliance and legal protection.
    """

    # === PRIMARY KEY ===
    consent_id: int = Field(..., description="Auto-increment primary key")

    # === CUSTOMER (unique) ===
    customer_id: UUID = Field(..., description="FK to customers (unique)")

    # === CONSENT CONFIGURATION ===
    consent_tier: ConsentTier = Field(..., description="Consent tier")
    consent_version: int = Field(..., ge=1, description="Policy version (tracks changes)")

    # === TEMPORAL ===
    consented_at: datetime = Field(..., description="When consent was given")
    expires_at: Optional[datetime] = Field(
        None,
        description="Optional expiration (if set, must be >consented_at and <10 years)",
    )

    # === GRANULAR PERMISSIONS ===
    can_store_images: bool = Field(..., description="Permission to store raw images")
    can_store_embeddings: bool = Field(..., description="Permission to store embeddings")
    can_use_for_training: bool = Field(..., description="Permission to use data for model training")

    # === ANONYMIZATION ===
    anonymization_level: AnonymizationLevel = Field(
        ...,
        description="Required if can_store_images=true",
    )

    # === VALIDATORS ===

    @root_validator(skip_on_failure=True)
    def validate_consent_tier_logic(cls, values):
        """Ensure consent tier permissions are consistent."""
        tier = values.get('consent_tier')
        can_store_images = values.get('can_store_images')
        can_store_embeddings = values.get('can_store_embeddings')
        can_use_for_training = values.get('can_use_for_training')

        if tier == ConsentTier.NONE:
            if can_store_images or can_store_embeddings or can_use_for_training:
                raise ValueError(
                    "consent_tier=none requires all permissions to be false. "
                    f"Got: images={can_store_images}, embeddings={can_store_embeddings}, "
                    f"training={can_use_for_training}"
                )

        elif tier == ConsentTier.METADATA:
            if can_store_images:
                raise ValueError("consent_tier=metadata does not allow storing images")
            if not (can_store_embeddings and can_use_for_training):
                raise ValueError(
                    "consent_tier=metadata requires can_store_embeddings=true and "
                    "can_use_for_training=true"
                )

        elif tier == ConsentTier.FULL:
            if not (can_store_images and can_store_embeddings and can_use_for_training):
                raise ValueError(
                    "consent_tier=full requires all permissions to be true. "
                    f"Got: images={can_store_images}, embeddings={can_store_embeddings}, "
                    f"training={can_use_for_training}"
                )

        return values

    @root_validator(skip_on_failure=True)
    def validate_anonymization_logic(cls, values):
        """Ensure anonymization is configured correctly."""
        can_store_images = values.get('can_store_images')
        anonymization_level = values.get('anonymization_level')

        if can_store_images and anonymization_level == AnonymizationLevel.NONE:
            raise ValueError(
                "If can_store_images=true, anonymization_level cannot be 'none'. "
                "Must be 'partial' or 'full' to protect privacy."
            )

        return values

    @validator('expires_at')
    def validate_expiration(cls, v, values):
        """Validate expiration timestamp."""
        if v is None:
            return v

        consented_at = values.get('consented_at')
        if consented_at is not None:
            # Expiration must be after consent
            if v <= consented_at:
                raise ValueError(
                    f"expires_at ({v}) must be after consented_at ({consented_at})"
                )

            # Prevent extremely long consent periods (max 10 years)
            max_expiration = consented_at.replace(year=consented_at.year + 10)
            if v > max_expiration:
                raise ValueError(
                    f"expires_at ({v}) cannot be more than 10 years after consented_at ({consented_at})"
                )

        return v

    class Config:
        use_enum_values = True
