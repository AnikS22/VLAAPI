"""Feedback data contracts.

Pydantic models for customer feedback on inference quality.
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import Dict, Optional, List
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


class FeedbackBaseRequest(BaseModel):
    """Base fields shared by feedback requests."""

    log_id: int = Field(..., ge=1, description="Inference log identifier")
    notes: Optional[str] = Field(
        None,
        max_length=2000,
        description="Optional notes from customer (max 2000 chars)",
    )


class SuccessRatingRequest(FeedbackBaseRequest):
    """Request payload for success rating submission."""

    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Success rating between 1 (failure) and 5 (perfect)",
    )


class SafetyRatingRequest(FeedbackBaseRequest):
    """Request payload for safety rating submission."""

    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Safety rating between 1 (unsafe) and 5 (fully safe)",
    )


class ActionCorrectionRequest(FeedbackBaseRequest):
    """Request payload for action correction submission."""

    corrected_action: List[float] = Field(
        ...,
        min_items=7,
        max_items=7,
        description="Corrected 7-DoF action vector provided by human",
    )

    @validator('corrected_action')
    def validate_corrected_action(cls, value):
        """Ensure corrected action has valid dimensions and values."""
        if len(value) != 7:
            raise ValueError(
                f"corrected_action must have exactly 7 dimensions, got {len(value)}"
            )

        non_finite = [i for i, component in enumerate(value) if not math.isfinite(component)]
        if non_finite:
            raise ValueError(
                f"corrected_action contains non-finite values at indices {non_finite}"
            )

        gripper_position = value[-1]
        if gripper_position < 0.0 or gripper_position > 1.0:
            raise ValueError(
                "corrected_action gripper value (index 6) must be between 0.0 and 1.0"
            )

        return value


class FailureReportRequest(FeedbackBaseRequest):
    """Request payload for failure report submission."""

    failure_reason: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Short description of failure reason",
    )


class FeedbackResponse(BaseModel):
    """Standard response returned when feedback is created."""

    feedback_id: int = Field(..., description="Created feedback identifier")
    log_id: int = Field(..., description="Associated inference log identifier")
    feedback_type: FeedbackType = Field(..., description="Created feedback type")
    customer_id: UUID = Field(..., description="Customer who created the feedback")
    timestamp: datetime = Field(..., description="Creation timestamp")
    message: str = Field(..., description="Human readable acknowledgement")


class FeedbackDetailResponse(BaseModel):
    """Detailed feedback record returned in listings."""

    feedback_id: int
    log_id: int
    feedback_type: FeedbackType
    customer_id: UUID
    timestamp: datetime
    rating: Optional[int] = None
    corrected_action: Optional[List[float]] = None
    original_action: Optional[List[float]] = None
    correction_delta: Optional[List[float]] = None
    correction_magnitude: Optional[float] = None
    failure_reason: Optional[str] = None
    notes: Optional[str] = None


class FeedbackStatsPeriod(BaseModel):
    """Time period for aggregated feedback statistics."""

    start: datetime = Field(..., description="Start of aggregation window")
    end: datetime = Field(..., description="End of aggregation window")


class FailureReasonCount(BaseModel):
    """Top failure reason entry."""

    reason: Optional[str] = Field(None, description="Failure reason string")
    count: int = Field(..., ge=0, description="Occurrences for this reason")


class FeedbackStatsResponse(BaseModel):
    """Aggregated statistics about customer feedback."""

    customer_id: UUID
    total_feedback_count: int = Field(..., ge=0)
    total_inference_count: int = Field(..., ge=0)
    feedback_rate: float = Field(..., ge=0.0)
    feedback_by_type: Dict[str, int] = Field(default_factory=dict)
    average_success_rating: Optional[float] = Field(None, ge=1.0, le=5.0)
    average_safety_rating: Optional[float] = Field(None, ge=1.0, le=5.0)
    correction_count: int = Field(..., ge=0)
    average_correction_magnitude: Optional[float] = Field(None, ge=0.0)
    failure_count: int = Field(..., ge=0)
    top_failure_reasons: List[FailureReasonCount] = Field(default_factory=list)
    period: FeedbackStatsPeriod


class FeedbackListResponse(BaseModel):
    """Paginated list of feedback records."""

    feedback: List[FeedbackDetailResponse]
    total_count: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    per_page: int = Field(..., ge=1)
    has_next: bool = Field(..., description="True if another page of results exists")


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

    @root_validator(skip_on_failure=True)
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
