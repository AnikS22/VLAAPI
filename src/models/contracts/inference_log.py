"""Inference log data contract.

Complete Pydantic validation model for inference_logs table.
This is PRIMARY MOAT DATA - every field is critical.
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum
import math

from .robot_types import RobotType, ROBOT_SPECS


class InferenceStatus(str, Enum):
    """Status of inference request."""
    SUCCESS = "success"
    ERROR = "error"
    SAFETY_REJECTED = "safety_rejected"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"


class InstructionCategory(str, Enum):
    """Auto-classified instruction categories."""
    PICK = "pick"
    PLACE = "place"
    NAVIGATE = "navigate"
    MANIPULATE = "manipulate"
    INSPECT = "inspect"
    MEASURE = "measure"
    OPEN = "open"
    CLOSE = "close"
    PUSH = "push"
    PULL = "pull"
    OTHER = "other"


class ModelName(str, Enum):
    """Available VLA models."""
    OPENVLA_7B = "openvla-7b"
    PI0 = "pi0"
    PI0_FAST = "pi0-fast"


class InferenceLogContract(BaseModel):
    """Complete data contract for inference_logs table.

    This is PRIMARY MOAT DATA - every field is critical.
    """

    # === REQUIRED FIELDS (must be present, non-null) ===

    request_id: UUID = Field(
        ...,
        description="Unique inference request ID. Must be globally unique UUID v4.",
    )

    customer_id: UUID = Field(
        ...,
        description="Customer UUID. Must exist in customers table.",
    )

    timestamp: datetime = Field(
        ...,
        description="Request timestamp in UTC. Cannot be in future. Must be >= customer.created_at.",
    )

    model_name: ModelName = Field(
        ...,
        description="VLA model used for inference. Must be exact match from enum.",
    )

    instruction: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Natural language instruction. Min 3 chars, max 1000 chars.",
    )

    action_vector: List[float] = Field(
        ...,
        min_items=7,
        max_items=7,
        description="7-DoF robot action vector. Must be exactly 7 dimensions, all finite.",
    )

    status: InferenceStatus = Field(
        ...,
        description="Inference status. Determines if customer is charged.",
    )

    robot_type: RobotType = Field(
        ...,
        description="CRITICAL: Robot type. Required for moat analysis. Cannot be UNKNOWN.",
    )

    # === OPTIONAL FIELDS (can be null, but if present must validate) ===

    image_shape: Optional[List[int]] = Field(
        None,
        min_items=3,
        max_items=3,
        description="Image dimensions [height, width, channels]. If present: height/width 64-2048, channels=3.",
    )

    safety_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Safety confidence score 0.0-1.0. Decimal precision 3.",
    )

    inference_latency_ms: Optional[float] = Field(
        None,
        ge=0.0,
        le=60000.0,
        description="Total inference time in ms. Must be 0-60000ms (reject >60s).",
    )

    queue_wait_ms: Optional[float] = Field(
        None,
        ge=0.0,
        le=300000.0,
        description="Time spent in queue in ms. Must be 0-300000ms (5 min max).",
    )

    gpu_compute_ms: Optional[float] = Field(
        None,
        ge=0.0,
        le=60000.0,
        description="GPU computation time in ms. Must be 0-60000ms.",
    )

    error_message: Optional[str] = Field(
        None,
        max_length=2000,
        description="Error message. Required if status=error.",
    )

    # === COMPUTED/DERIVED FIELDS ===

    instruction_category: InstructionCategory = Field(
        InstructionCategory.OTHER,
        description="Auto-classified instruction category. Computed from instruction text.",
    )

    action_magnitude: Optional[float] = Field(
        None,
        ge=0.0,
        description="L2 norm of action_vector. Computed for safety analysis.",
    )

    # === VALIDATION RULES ===

    @validator('request_id')
    def validate_request_id(cls, v):
        """Ensure request_id is a valid UUID v4."""
        if v.version != 4:
            raise ValueError(f"request_id must be UUID v4, got version {v.version}")
        return v

    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Ensure timestamp is not in the future."""
        now = datetime.utcnow()
        if v > now:
            raise ValueError(f"timestamp cannot be in future. Got {v}, now is {now}")
        return v

    @validator('instruction')
    def validate_instruction(cls, v):
        """Ensure instruction is meaningful."""
        v = v.strip()
        if len(v) < 3:
            raise ValueError(f"instruction too short (min 3 chars): '{v}'")
        if len(v) > 1000:
            raise ValueError(f"instruction too long (max 1000 chars): {len(v)} chars")
        # Check for valid UTF-8
        try:
            v.encode('utf-8')
        except UnicodeEncodeError as e:
            raise ValueError(f"instruction contains invalid UTF-8: {e}")
        return v

    @validator('action_vector')
    def validate_action_vector(cls, v):
        """Ensure action_vector is valid 7-DoF with finite values."""
        if len(v) != 7:
            raise ValueError(f"action_vector must have exactly 7 dimensions, got {len(v)}")

        # Check for non-finite values (NaN, inf, -inf)
        non_finite = [i for i, x in enumerate(v) if not math.isfinite(x)]
        if non_finite:
            raise ValueError(
                f"action_vector contains non-finite values at indices {non_finite}. "
                f"Values: {[v[i] for i in non_finite]}"
            )

        return v

    @validator('action_vector')
    def validate_action_bounds(cls, v, values):
        """Validate action_vector against robot-specific joint limits."""
        robot_type = values.get('robot_type')
        if not robot_type or robot_type not in ROBOT_SPECS:
            # If robot type not available yet or no spec, skip bounds check
            # Will be caught by robot_type validator
            return v

        spec = ROBOT_SPECS[robot_type]
        joint_limits = spec['joint_limits']

        # For 6-DoF robots, check first 6 values
        # For 7-DoF robots, check all 7 values
        dof = spec['dof']
        if len(v) > dof:
            # Extra dimensions should be zero or very small
            extra_dims = v[dof:]
            if any(abs(x) > 0.001 for x in extra_dims):
                raise ValueError(
                    f"Robot {robot_type} has {dof} DoF, but action_vector has "
                    f"non-zero values in extra dimensions: {extra_dims}"
                )

        # Check joint limits
        violations = []
        for i, (action_val, (min_val, max_val)) in enumerate(zip(v[:dof], joint_limits)):
            if not (min_val <= action_val <= max_val):
                violations.append({
                    'joint': i,
                    'value': action_val,
                    'limits': (min_val, max_val),
                })

        if violations:
            raise ValueError(
                f"action_vector violates joint limits for {robot_type}: {violations}"
            )

        return v

    @validator('robot_type')
    def validate_robot_type(cls, v):
        """Ensure robot_type is valid and not UNKNOWN."""
        if v == RobotType.UNKNOWN:
            raise ValueError(
                "robot_type cannot be UNKNOWN. This field is critical for moat analysis. "
                "If robot type is genuinely unknown, use RobotType.CUSTOM and provide "
                "robot specifications in metadata."
            )
        return v

    @validator('image_shape')
    def validate_image_shape(cls, v):
        """Validate image dimensions if provided."""
        if v is None:
            return v

        if len(v) != 3:
            raise ValueError(f"image_shape must have exactly 3 elements [H, W, C], got {len(v)}")

        height, width, channels = v

        # Reasonable image size bounds
        if not (64 <= height <= 2048):
            raise ValueError(f"image height must be 64-2048 pixels, got {height}")
        if not (64 <= width <= 2048):
            raise ValueError(f"image width must be 64-2048 pixels, got {width}")
        if channels != 3:
            raise ValueError(f"image channels must be 3 (RGB), got {channels}")

        # Prevent memory attacks: max 10M pixels
        total_pixels = height * width
        if total_pixels > 10_000_000:
            raise ValueError(
                f"image too large: {total_pixels:,} pixels (max 10M). "
                f"Dimensions: {height}x{width}"
            )

        return v

    @validator('safety_score')
    def validate_safety_score(cls, v):
        """Validate safety score range and precision."""
        if v is None:
            return v

        if not (0.0 <= v <= 1.0):
            raise ValueError(f"safety_score must be in range [0.0, 1.0], got {v}")

        # Round to 3 decimal places
        return round(v, 3)

    @validator('error_message')
    def validate_error_message(cls, v, values):
        """Ensure error_message is present if status=error."""
        status = values.get('status')
        if status == InferenceStatus.ERROR and not v:
            raise ValueError("error_message is required when status=error")
        return v

    @root_validator(skip_on_failure=True)
    def validate_safety_consistency(cls, values):
        """Ensure safety_score and status are consistent."""
        status = values.get('status')
        safety_score = values.get('safety_score')

        if status == InferenceStatus.SAFETY_REJECTED:
            if safety_score is None:
                raise ValueError("safety_score is required when status=safety_rejected")
            if safety_score >= 0.8:
                raise ValueError(
                    f"status=safety_rejected but safety_score={safety_score} >= 0.8. "
                    f"Safety rejected inferences must have safety_score < 0.8."
                )

        return values

    @root_validator(skip_on_failure=True)
    def validate_latency_consistency(cls, values):
        """Ensure latency metrics are consistent."""
        inference_latency = values.get('inference_latency_ms')
        gpu_compute = values.get('gpu_compute_ms')
        queue_wait = values.get('queue_wait_ms')

        if inference_latency is not None and gpu_compute is not None and queue_wait is not None:
            # Total latency should be >= sum of components (allowing small overhead)
            min_expected = gpu_compute + queue_wait
            if inference_latency < min_expected - 1.0:  # 1ms tolerance
                raise ValueError(
                    f"Latency inconsistency: inference_latency_ms={inference_latency} < "
                    f"gpu_compute_ms={gpu_compute} + queue_wait_ms={queue_wait} = {min_expected}"
                )

        return values

    @root_validator(skip_on_failure=True)
    def compute_derived_fields(cls, values):
        """Compute derived fields from input data."""
        # Compute action magnitude (L2 norm)
        action_vector = values.get('action_vector')
        if action_vector:
            values['action_magnitude'] = math.sqrt(sum(x**2 for x in action_vector))

        # Auto-classify instruction category
        instruction = values.get('instruction', '').lower()
        if instruction:
            # Simple keyword-based classification (can be improved with ML)
            if any(word in instruction for word in ['pick', 'grasp', 'grab', 'lift']):
                values['instruction_category'] = InstructionCategory.PICK
            elif any(word in instruction for word in ['place', 'put', 'set', 'drop']):
                values['instruction_category'] = InstructionCategory.PLACE
            elif any(word in instruction for word in ['move', 'go', 'navigate', 'drive']):
                values['instruction_category'] = InstructionCategory.NAVIGATE
            elif any(word in instruction for word in ['open', 'unlock', 'uncap']):
                values['instruction_category'] = InstructionCategory.OPEN
            elif any(word in instruction for word in ['close', 'lock', 'cap', 'shut']):
                values['instruction_category'] = InstructionCategory.CLOSE
            elif any(word in instruction for word in ['push', 'press', 'slide']):
                values['instruction_category'] = InstructionCategory.PUSH
            elif any(word in instruction for word in ['pull', 'drag', 'yank']):
                values['instruction_category'] = InstructionCategory.PULL
            elif any(word in instruction for word in ['inspect', 'check', 'examine', 'look']):
                values['instruction_category'] = InstructionCategory.INSPECT
            elif any(word in instruction for word in ['measure', 'gauge', 'assess']):
                values['instruction_category'] = InstructionCategory.MEASURE
            elif any(word in instruction for word in ['rotate', 'turn', 'twist', 'spin']):
                values['instruction_category'] = InstructionCategory.MANIPULATE

        return values

    class Config:
        use_enum_values = True
        validate_assignment = True
