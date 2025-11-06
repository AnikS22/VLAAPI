"""Feedback data contracts.

Pydantic models for customer feedback on inference quality.
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum
import math


class FeedbackType(str, Enum):
    """Types of customer feedback."""
    SUCCESS_RATING = "success_rating"
    SAFETY_RATING = "safety_rating"
    ACTION_CORRECTION = "action_correction"
    FAILURE_REPORT = "failure_report"


class FeedbackContract(BaseModel):
    """Customer feedback for inference quality.

    HIGH-VALUE DATA for model improvement and customer insights.
    """

    # === PRIMARY KEY ===
    feedback_id: int = Field(..., description="Auto-increment primary key")

    # === FOREIGN KEYS ===
    log_id: int = Field(..., description="FK to inference_logs (required, indexed)")
    customer_id: UUID = Field(..., description="FK to customers")

    # === FEEDBACK TYPE ===
    feedback_type: FeedbackType = Field(..., description="Type of feedback")

    # === TYPE-SPECIFIC FIELDS ===
    rating: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="1-5 stars rating. Required for success_rating/safety_rating.",
    )

    corrected_action: Optional[List[float]] = Field(
        None,
        min_items=7,
        max_items=7,
        description="Corrected 7-DoF action. Required for action_correction.",
    )

    failure_reason: Optional[str] = Field(
        None,
        max_length=1000,
        description="Failure description. Required for failure_report.",
    )

    # === OPTIONAL NOTES ===
    notes: Optional[str] = Field(
        None,
        max_length=2000,
        description="Additional customer notes (optional)",
    )

    # === TEMPORAL ===
    timestamp: datetime = Field(..., description="When feedback was provided")

    # === VALIDATORS ===

    @root_validator
    def validate_feedback_fields(cls, values):
        """Ensure required fields are present based on feedback_type."""
        feedback_type = values.get('feedback_type')
        rating = values.get('rating')
        corrected_action = values.get('corrected_action')
        failure_reason = values.get('failure_reason')

        if feedback_type in [FeedbackType.SUCCESS_RATING, FeedbackType.SAFETY_RATING]:
            if rating is None:
                raise ValueError(f"rating is required for feedback_type={feedback_type}")

        if feedback_type == FeedbackType.ACTION_CORRECTION:
            if corrected_action is None:
                raise ValueError("corrected_action is required for feedback_type=action_correction")

        if feedback_type == FeedbackType.FAILURE_REPORT:
            if not failure_reason:
                raise ValueError("failure_reason is required for feedback_type=failure_report")

        return values

    @validator('corrected_action')
    def validate_corrected_action(cls, v):
        """Validate corrected action vector."""
        if v is None:
            return v

        if len(v) != 7:
            raise ValueError(f"corrected_action must have exactly 7 dimensions, got {len(v)}")

        # Check for non-finite values
        non_finite = [i for i, x in enumerate(v) if not math.isfinite(x)]
        if non_finite:
            raise ValueError(
                f"corrected_action contains non-finite values at indices {non_finite}"
            )

        return v

    @validator('timestamp')
    def validate_timestamp_ordering(cls, v):
        """Ensure feedback timestamp is not in future."""
        now = datetime.utcnow()
        if v > now:
            raise ValueError(f"timestamp cannot be in future. Got {v}, now is {now}")
        return v

    class Config:
        use_enum_values = True
