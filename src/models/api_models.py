"""Pydantic models for API request/response validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.constants import (
    ACTION_SPACE_COMPONENTS,
    ACTION_SPACE_DIM,
    ACTION_SPACE_UNITS,
    CustomerTier,
    InferenceStatus,
)


# =============================================================================
# INFERENCE API MODELS
# =============================================================================

class RobotConfig(BaseModel):
    """Robot configuration for inference."""

    type: str = Field(
        default="franka_panda",
        description="Robot type (franka_panda, ur5, xarm7, custom)",
    )
    workspace_bounds: Optional[List[List[float]]] = Field(
        default=None,
        description="Workspace bounds [[x_min, y_min, z_min], [x_max, y_max, z_max]]",
    )
    velocity_limits: Optional[List[float]] = Field(
        default=None,
        description="Velocity limits for each DoF (m/s or rad/s)",
    )
    normalization_stats: Optional[Dict[str, List[float]]] = Field(
        default=None,
        description="Action normalization statistics {mean: [...], std: [...]}",
    )

    @field_validator("workspace_bounds")
    @classmethod
    def validate_workspace_bounds(cls, v):
        """Validate workspace bounds format."""
        if v is not None:
            if len(v) != 2 or any(len(bound) != 3 for bound in v):
                raise ValueError(
                    "workspace_bounds must be [[x_min, y_min, z_min], [x_max, y_max, z_max]]"
                )
        return v


class SafetyConfig(BaseModel):
    """Safety configuration for inference."""

    enable_classifier: bool = Field(
        default=True,
        description="Enable ML safety classifier",
    )
    enable_collision_check: bool = Field(
        default=True,
        description="Enable collision risk checking",
    )
    enable_workspace_check: bool = Field(
        default=True,
        description="Enable workspace boundary checking",
    )
    safety_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum safety score (0.0-1.0)",
    )


class InferenceOptions(BaseModel):
    """Additional inference options."""

    return_visualization: bool = Field(
        default=False,
        description="Return annotated image with action overlay",
    )
    return_raw_logits: bool = Field(
        default=False,
        description="Return raw model logits (debugging)",
    )


class InferenceRequest(BaseModel):
    """Request model for VLA inference."""

    model: str = Field(
        default="openvla-7b",
        description="VLA model to use (openvla-7b, pi0, pi0-fast)",
    )
    image: str = Field(
        ...,
        description="Base64-encoded image or image URL",
    )
    instruction: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural language instruction for the robot",
    )
    robot_config: Optional[RobotConfig] = Field(
        default=None,
        description="Robot configuration (optional)",
    )
    safety: Optional[SafetyConfig] = Field(
        default=None,
        description="Safety configuration (optional)",
    )
    options: Optional[InferenceOptions] = Field(
        default=None,
        description="Additional inference options (optional)",
    )

    @field_validator("image")
    @classmethod
    def validate_image(cls, v):
        """Validate image format (basic check)."""
        if not v or len(v) < 100:  # Minimum base64 size
            raise ValueError("Image must be a valid base64-encoded string or URL")
        return v

    @field_validator("model")
    @classmethod
    def validate_model(cls, v):
        """Validate model name."""
        valid_models = ["openvla-7b", "pi0", "pi0-fast"]
        if v not in valid_models:
            raise ValueError(f"Invalid model. Must be one of: {valid_models}")
        return v


class ActionResponse(BaseModel):
    """Action vector response."""

    type: str = Field(
        default="end_effector_delta",
        description="Action space type",
    )
    dimensions: int = Field(
        default=ACTION_SPACE_DIM,
        description="Action vector dimensions",
    )
    values: List[float] = Field(
        ...,
        min_length=ACTION_SPACE_DIM,
        max_length=ACTION_SPACE_DIM,
        description="Action values",
    )
    units: List[str] = Field(
        default=ACTION_SPACE_UNITS,
        description="Units for each action component",
    )
    description: List[str] = Field(
        default=ACTION_SPACE_COMPONENTS,
        description="Description of each action component",
    )


class SafetyCheckResult(BaseModel):
    """Individual safety check result."""

    passed: bool = Field(..., description="Whether check passed")
    score: float = Field(..., ge=0.0, le=1.0, description="Safety score")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional details about the check",
    )


class SafetyResponse(BaseModel):
    """Safety evaluation response."""

    overall_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall safety score",
    )
    checks_passed: List[str] = Field(
        ...,
        description="List of passed safety checks",
    )
    flags: Dict[str, bool] = Field(
        ...,
        description="Safety flags {workspace_violation, velocity_violation, ...}",
    )
    classifier_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="ML classifier confidence (if enabled)",
    )
    modifications_applied: bool = Field(
        default=False,
        description="Whether action was modified for safety",
    )
    checks: Optional[Dict[str, SafetyCheckResult]] = Field(
        default=None,
        description="Detailed results for each safety check",
    )


class PerformanceMetrics(BaseModel):
    """Performance metrics for inference."""

    total_latency_ms: int = Field(..., ge=0, description="Total latency (ms)")
    queue_wait_ms: int = Field(..., ge=0, description="Time spent in queue (ms)")
    inference_ms: int = Field(..., ge=0, description="Model inference time (ms)")
    safety_check_ms: int = Field(..., ge=0, description="Safety check time (ms)")
    postprocess_ms: int = Field(..., ge=0, description="Post-processing time (ms)")


class UsageInfo(BaseModel):
    """Usage information for rate limiting."""

    requests_remaining_minute: int = Field(
        ...,
        ge=0,
        description="Requests remaining this minute",
    )
    requests_remaining_day: int = Field(
        ...,
        ge=0,
        description="Requests remaining today",
    )
    monthly_quota_remaining: Optional[int] = Field(
        default=None,
        description="Monthly quota remaining (None = unlimited)",
    )


class InferenceResponse(BaseModel):
    """Response model for VLA inference."""

    request_id: UUID = Field(..., description="Unique request identifier")
    timestamp: datetime = Field(..., description="Request timestamp (ISO 8601)")
    model: str = Field(..., description="VLA model used")
    action: ActionResponse = Field(..., description="Predicted robot action")
    safety: SafetyResponse = Field(..., description="Safety evaluation results")
    performance: PerformanceMetrics = Field(..., description="Performance metrics")
    usage: UsageInfo = Field(..., description="Usage and rate limit info")


# =============================================================================
# SAFETY API MODELS
# =============================================================================

class SafetyEvaluateRequest(BaseModel):
    """Request model for standalone safety evaluation."""

    action: List[float] = Field(
        ...,
        min_length=ACTION_SPACE_DIM,
        max_length=ACTION_SPACE_DIM,
        description="Action vector to evaluate",
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context (current_pose, workspace_bounds, obstacles)",
    )


class SafetyEvaluateResponse(BaseModel):
    """Response model for safety evaluation."""

    is_safe: bool = Field(..., description="Whether action is safe")
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall safety score")
    checks: Dict[str, SafetyCheckResult] = Field(
        ...,
        description="Individual safety check results",
    )
    safe_alternative: Optional[List[float]] = Field(
        default=None,
        description="Safe alternative action (if original unsafe)",
    )


# =============================================================================
# MODEL API MODELS
# =============================================================================

class ModelInfo(BaseModel):
    """Information about a VLA model."""

    id: str = Field(..., description="Model identifier")
    name: str = Field(..., description="Human-readable model name")
    description: str = Field(..., description="Model description")
    version: str = Field(..., description="Model version")
    action_space: Dict[str, Any] = Field(..., description="Action space specification")
    input_requirements: Dict[str, Any] = Field(..., description="Input requirements")
    available: bool = Field(..., description="Whether model is currently available")
    avg_latency_ms: int = Field(..., ge=0, description="Average inference latency (ms)")


class ModelListResponse(BaseModel):
    """Response model for listing available models."""

    models: List[ModelInfo] = Field(..., description="List of available models")


# =============================================================================
# ADMIN API MODELS
# =============================================================================

class CustomerCreate(BaseModel):
    """Request model for creating a customer."""

    email: str = Field(..., description="Customer email address")
    company_name: Optional[str] = Field(default=None, description="Company name")
    tier: CustomerTier = Field(default=CustomerTier.FREE, description="Subscription tier")
    rate_limit_rpm: Optional[int] = Field(default=None, ge=1, description="Requests per minute")
    monthly_quota: Optional[int] = Field(default=None, ge=1, description="Monthly quota")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        """Basic email validation."""
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email address")
        return v.lower()


class CustomerResponse(BaseModel):
    """Response model for customer information."""

    customer_id: UUID = Field(..., description="Customer ID")
    email: str = Field(..., description="Customer email")
    company_name: Optional[str] = Field(default=None, description="Company name")
    tier: str = Field(..., description="Subscription tier")
    created_at: datetime = Field(..., description="Account creation timestamp")
    is_active: bool = Field(..., description="Account status")
    rate_limit_rpm: int = Field(..., description="Requests per minute limit")
    monthly_quota: Optional[int] = Field(default=None, description="Monthly quota")
    monthly_usage: int = Field(..., description="Current month usage")


class APIKeyCreate(BaseModel):
    """Request model for creating an API key."""

    key_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="User-friendly key name",
    )
    scopes: List[str] = Field(
        default=["inference"],
        description="API key scopes",
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Expiration timestamp (optional)",
    )
    rate_limit_override_rpm: Optional[int] = Field(
        default=None,
        ge=1,
        description="Per-key rate limit override",
    )


class APIKeyResponse(BaseModel):
    """Response model for API key (includes plaintext key ONLY on creation)."""

    key_id: UUID = Field(..., description="API key ID")
    key: Optional[str] = Field(
        default=None,
        description="Full API key (ONLY shown on creation)",
    )
    key_prefix: str = Field(..., description="Key prefix for identification")
    key_name: Optional[str] = Field(default=None, description="Key name")
    scopes: List[str] = Field(..., description="API key scopes")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration timestamp")
    last_used_at: Optional[datetime] = Field(default=None, description="Last usage timestamp")
    is_active: bool = Field(..., description="Key status")


class UsageSummary(BaseModel):
    """Usage summary statistics."""

    total_requests: int = Field(..., ge=0, description="Total requests")
    successful_requests: int = Field(..., ge=0, description="Successful requests")
    error_requests: int = Field(..., ge=0, description="Error requests")
    safety_rejected_requests: int = Field(..., ge=0, description="Safety-rejected requests")
    avg_latency_ms: float = Field(..., ge=0, description="Average latency (ms)")


class UsageResponse(BaseModel):
    """Response model for customer usage statistics."""

    customer_id: UUID = Field(..., description="Customer ID")
    period: Dict[str, datetime] = Field(..., description="Time period {start, end}")
    summary: UsageSummary = Field(..., description="Usage summary")
    by_model: Dict[str, int] = Field(..., description="Usage breakdown by model")
    daily_breakdown: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Daily usage breakdown",
    )


class SafetyIncidentResponse(BaseModel):
    """Response model for safety incidents."""

    incident_id: int = Field(..., description="Incident ID")
    customer_id: UUID = Field(..., description="Customer ID")
    timestamp: datetime = Field(..., description="Incident timestamp")
    severity: str = Field(..., description="Incident severity")
    violation_type: str = Field(..., description="Type of violation")
    details: Dict[str, Any] = Field(..., description="Violation details")
    action_taken: str = Field(..., description="Action taken")


class SafetyIncidentsResponse(BaseModel):
    """Response model for listing safety incidents."""

    incidents: List[SafetyIncidentResponse] = Field(..., description="List of incidents")
    total_count: int = Field(..., ge=0, description="Total incident count")
    page: int = Field(..., ge=1, description="Current page")
    per_page: int = Field(..., ge=1, description="Items per page")


# =============================================================================
# MONITORING API MODELS
# =============================================================================

class ServiceHealth(BaseModel):
    """Health status for a service component."""

    status: str = Field(..., description="Health status (healthy, degraded, unhealthy)")
    latency_ms: Optional[int] = Field(default=None, description="Service latency (ms)")
    details: Optional[str] = Field(default=None, description="Additional details")


class GPUInfo(BaseModel):
    """GPU information."""

    device_name: str = Field(..., description="GPU device name")
    memory_used_gb: float = Field(..., ge=0, description="GPU memory used (GB)")
    memory_total_gb: float = Field(..., ge=0, description="Total GPU memory (GB)")
    utilization_percent: int = Field(..., ge=0, le=100, description="GPU utilization (%)")


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Overall status (healthy, degraded, unhealthy)")
    timestamp: datetime = Field(..., description="Health check timestamp")
    services: Dict[str, ServiceHealth] = Field(..., description="Individual service health")
    gpu_info: Optional[GPUInfo] = Field(default=None, description="GPU information")
    queue_depth: int = Field(..., ge=0, description="Current inference queue depth")
    models_loaded: List[str] = Field(..., description="Loaded VLA models")


# =============================================================================
# ERROR RESPONSE MODELS
# =============================================================================

class ErrorDetail(BaseModel):
    """Detailed error information."""

    loc: Optional[List[str]] = Field(default=None, description="Error location")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    request_id: Optional[UUID] = Field(default=None, description="Request ID for tracing")


class RateLimitErrorResponse(ErrorResponse):
    """Rate limit error response."""

    retry_after_seconds: int = Field(..., ge=0, description="Seconds until retry allowed")
    limits: Dict[str, int] = Field(..., description="Current rate limits")


class ValidationErrorResponse(ErrorResponse):
    """Validation error response."""

    validation_errors: List[ErrorDetail] = Field(..., description="Detailed validation errors")
