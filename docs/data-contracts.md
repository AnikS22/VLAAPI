# VLA Inference API Data Contracts

**Version:** 1.0.0
**Last Updated:** 2025-11-06
**Status:** SOURCE OF TRUTH - No implementation may contradict this document

---

## Table of Contents

1. [Overview](#overview)
2. [Robot Type Standardization](#robot-type-standardization)
3. [Inference Logs Data Contract](#inference-logs-data-contract)
4. [Robot Performance Metrics Data Contract](#robot-performance-metrics-data-contract)
5. [Instruction Analytics Data Contract](#instruction-analytics-data-contract)
6. [Context Metadata Data Contract](#context-metadata-data-contract)
7. [Customer Data Consent Data Contract](#customer-data-consent-data-contract)
8. [Safety Incidents Data Contract](#safety-incidents-data-contract)
9. [Feedback Data Contract](#feedback-data-contract)
10. [Deduplication Logic](#deduplication-logic)
11. [Quality Gates](#quality-gates)
12. [Validation Implementation](#validation-implementation)
13. [Data Quality Monitoring](#data-quality-monitoring)

---

## Overview

This document defines the complete data contracts for the VLA Inference API data collection system. These contracts are CRITICAL for:

- **Competitive Moat:** High-quality robot-specific data is our primary competitive advantage
- **Data Quality:** Bad data in Week 1 = broken competitive moat forever
- **System Reliability:** Clear contracts prevent cascading failures
- **Privacy Compliance:** Proper consent tracking and anonymization

**Guiding Principles:**

1. **Required fields MUST be present and non-null** - reject inference if missing
2. **Optional fields MUST validate if present** - partial data is okay, invalid data is not
3. **Quality gates protect data integrity** - reject bad data immediately
4. **Deduplication prevents data pollution** - handle retries and replays correctly
5. **Robot type is SACRED** - this field enables the entire competitive moat

---

## Robot Type Standardization

### Canonical Robot Type Enum

```python
from enum import Enum

class RobotType(str, Enum):
    """Standardized robot types for VLA Inference API.

    Format: manufacturer_model or manufacturer_family_model
    All lowercase, underscore-separated.
    """
    # Franka Emika
    FRANKA_PANDA = "franka_panda"
    FRANKA_FR3 = "franka_fr3"

    # Universal Robots
    UR3 = "universal_robots_ur3"
    UR3E = "universal_robots_ur3e"
    UR5 = "universal_robots_ur5"
    UR5E = "universal_robots_ur5e"
    UR10 = "universal_robots_ur10"
    UR10E = "universal_robots_ur10e"
    UR16E = "universal_robots_ur16e"

    # ABB
    ABB_YUMI = "abb_yumi"
    ABB_IRB_1200 = "abb_irb_1200"
    ABB_IRB_1600 = "abb_irb_1600"
    ABB_IRB_6700 = "abb_irb_6700"

    # KUKA
    KUKA_IIWA7 = "kuka_iiwa7"
    KUKA_IIWA14 = "kuka_iiwa14"
    KUKA_LBR_MED = "kuka_lbr_med"

    # Kinova
    KINOVA_GEN3 = "kinova_gen3"
    KINOVA_GEN3_LITE = "kinova_gen3_lite"
    KINOVA_JACO = "kinova_jaco"

    # Rethink Robotics
    SAWYER = "rethink_sawyer"
    BAXTER = "rethink_baxter"

    # UFACTORY
    XARM5 = "ufactory_xarm5"
    XARM6 = "ufactory_xarm6"
    XARM7 = "ufactory_xarm7"
    LITE6 = "ufactory_lite6"

    # Fetch Robotics
    FETCH = "fetch_robotics_fetch"
    FREIGHT = "fetch_robotics_freight"

    # Mobile Manipulators
    TRI_HSR = "toyota_hsr"
    WILLOW_PR2 = "willow_garage_pr2"
    PAL_TIAGO = "pal_robotics_tiago"

    # Research Platforms
    BERKELEY_BLUE = "berkeley_blue"
    STANFORD_PUPPER = "stanford_pupper"

    # Other/Custom
    CUSTOM = "custom"
    UNKNOWN = "unknown"  # Only for legacy data migration
```

### Robot Specifications

```python
from typing import TypedDict, List, Tuple

class RobotSpec(TypedDict):
    """Technical specifications for a robot type."""
    dof: int  # Degrees of freedom
    joint_limits: List[Tuple[float, float]]  # Min/max per joint (radians or meters)
    max_reach: float  # Maximum reach in meters
    payload: float  # Maximum payload in kg
    typical_workspace: dict  # Typical workspace bounds
    expected_latency_p50: float  # Expected p50 latency in ms
    expected_latency_p95: float  # Expected p95 latency in ms

ROBOT_SPECS: dict[RobotType, RobotSpec] = {
    RobotType.FRANKA_PANDA: {
        "dof": 7,
        "joint_limits": [
            (-2.8973, 2.8973),   # Joint 1
            (-1.7628, 1.7628),   # Joint 2
            (-2.8973, 2.8973),   # Joint 3
            (-3.0718, -0.0698),  # Joint 4
            (-2.8973, 2.8973),   # Joint 5
            (-0.0175, 3.7525),   # Joint 6
            (-2.8973, 2.8973),   # Joint 7
        ],
        "max_reach": 0.855,  # meters
        "payload": 3.0,  # kg
        "typical_workspace": {
            "x": (-0.8, 0.8),
            "y": (-0.8, 0.8),
            "z": (0.0, 1.2),
        },
        "expected_latency_p50": 120.0,  # ms
        "expected_latency_p95": 250.0,  # ms
    },

    RobotType.UR5E: {
        "dof": 6,
        "joint_limits": [
            (-6.2832, 6.2832),   # Joint 1 (±360°)
            (-6.2832, 6.2832),   # Joint 2
            (-6.2832, 6.2832),   # Joint 3
            (-6.2832, 6.2832),   # Joint 4
            (-6.2832, 6.2832),   # Joint 5
            (-6.2832, 6.2832),   # Joint 6
        ],
        "max_reach": 0.850,  # meters
        "payload": 5.0,  # kg
        "typical_workspace": {
            "x": (-0.85, 0.85),
            "y": (-0.85, 0.85),
            "z": (0.0, 1.3),
        },
        "expected_latency_p50": 110.0,
        "expected_latency_p95": 230.0,
    },

    RobotType.KINOVA_GEN3: {
        "dof": 7,
        "joint_limits": [
            (-6.2832, 6.2832),   # Continuous rotation
            (-2.41, 2.41),
            (-6.2832, 6.2832),
            (-2.66, 2.66),
            (-6.2832, 6.2832),
            (-2.23, 2.23),
            (-6.2832, 6.2832),
        ],
        "max_reach": 0.902,  # meters
        "payload": 4.0,  # kg
        "typical_workspace": {
            "x": (-0.9, 0.9),
            "y": (-0.9, 0.9),
            "z": (0.0, 1.3),
        },
        "expected_latency_p50": 130.0,
        "expected_latency_p95": 270.0,
    },

    # Add more robot specs as needed...
}
```

### Robot Type Validation Rules

1. **MUST be from canonical enum** - reject if not in `RobotType` enum
2. **MUST NOT be UNKNOWN** - only allowed for legacy data migration
3. **MUST have corresponding spec** - if not in `ROBOT_SPECS`, require manual approval
4. **Action vectors MUST respect joint limits** - validate against `joint_limits` for robot type
5. **Latency outliers MUST be flagged** - if >3σ from expected latency, investigate

---

## Inference Logs Data Contract

### Schema

```python
from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
import math

class InferenceStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    SAFETY_REJECTED = "safety_rejected"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"

class InstructionCategory(str, Enum):
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

    @root_validator
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

    @root_validator
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

    @root_validator
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
```

### Example Valid Data

```python
valid_inference_log = InferenceLogContract(
    request_id=UUID('550e8400-e29b-41d4-a716-446655440000'),
    customer_id=UUID('123e4567-e89b-12d3-a456-426614174000'),
    timestamp=datetime(2025, 11, 6, 14, 30, 0),
    model_name=ModelName.OPENVLA_7B,
    instruction="Pick up the red cube from the table",
    action_vector=[0.1, -0.2, 0.05, 0.3, -0.1, 0.15, 0.0],
    status=InferenceStatus.SUCCESS,
    robot_type=RobotType.FRANKA_PANDA,
    image_shape=[480, 640, 3],
    safety_score=0.95,
    inference_latency_ms=120.5,
    queue_wait_ms=10.2,
    gpu_compute_ms=110.3,
)
```

### Example Invalid Data

```python
# Invalid: action_vector has NaN
invalid_inference_1 = InferenceLogContract(
    request_id=UUID('550e8400-e29b-41d4-a716-446655440001'),
    customer_id=UUID('123e4567-e89b-12d3-a456-426614174000'),
    timestamp=datetime(2025, 11, 6, 14, 30, 0),
    model_name=ModelName.OPENVLA_7B,
    instruction="Pick up the red cube",
    action_vector=[0.1, float('nan'), 0.05, 0.3, -0.1, 0.15, 0.0],  # ❌ NaN value
    status=InferenceStatus.SUCCESS,
    robot_type=RobotType.FRANKA_PANDA,
)
# Error: "action_vector contains non-finite values at indices [1]. Values: [nan]"

# Invalid: safety_rejected but high safety_score
invalid_inference_2 = InferenceLogContract(
    request_id=UUID('550e8400-e29b-41d4-a716-446655440002'),
    customer_id=UUID('123e4567-e89b-12d3-a456-426614174000'),
    timestamp=datetime(2025, 11, 6, 14, 30, 0),
    model_name=ModelName.PI0,
    instruction="Push the button",
    action_vector=[0.1, -0.2, 0.05, 0.3, -0.1, 0.15, 0.0],
    status=InferenceStatus.SAFETY_REJECTED,  # ❌ Rejected
    safety_score=0.92,  # ❌ But score is high
    robot_type=RobotType.UR5E,
)
# Error: "status=safety_rejected but safety_score=0.92 >= 0.8. Safety rejected inferences must have safety_score < 0.8."

# Invalid: robot_type is UNKNOWN
invalid_inference_3 = InferenceLogContract(
    request_id=UUID('550e8400-e29b-41d4-a716-446655440003'),
    customer_id=UUID('123e4567-e89b-12d3-a456-426614174000'),
    timestamp=datetime(2025, 11, 6, 14, 30, 0),
    model_name=ModelName.PI0_FAST,
    instruction="Navigate to the charging station",
    action_vector=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    status=InferenceStatus.SUCCESS,
    robot_type=RobotType.UNKNOWN,  # ❌ Cannot be UNKNOWN
)
# Error: "robot_type cannot be UNKNOWN. This field is critical for moat analysis."
```

### Database Schema Extensions

```sql
-- Add new columns to existing inference_logs table
ALTER TABLE vlaapi.inference_logs
ADD COLUMN robot_type VARCHAR(100) NOT NULL DEFAULT 'unknown',
ADD COLUMN instruction_category VARCHAR(50),
ADD COLUMN action_magnitude FLOAT,
ADD CONSTRAINT chk_robot_type CHECK (robot_type IN (
    'franka_panda', 'franka_fr3', 'universal_robots_ur5', 'universal_robots_ur5e',
    'universal_robots_ur10', 'abb_yumi', 'kuka_iiwa7', 'kinova_gen3',
    'rethink_sawyer', 'ufactory_xarm7', 'fetch_robotics_fetch', 'custom', 'unknown'
)),
ADD CONSTRAINT chk_instruction_category CHECK (instruction_category IN (
    'pick', 'place', 'navigate', 'manipulate', 'inspect', 'measure',
    'open', 'close', 'push', 'pull', 'other'
)),
ADD CONSTRAINT chk_action_magnitude CHECK (action_magnitude >= 0.0);

-- Create index on robot_type for moat analysis queries
CREATE INDEX idx_logs_robot_type ON vlaapi.inference_logs(robot_type);
CREATE INDEX idx_logs_robot_model ON vlaapi.inference_logs(robot_type, model_name);
CREATE INDEX idx_logs_instruction_category ON vlaapi.inference_logs(instruction_category);

-- Add unique constraint on request_id for deduplication
CREATE UNIQUE INDEX idx_logs_request_id_unique ON vlaapi.inference_logs(request_id);
```

---

## Robot Performance Metrics Data Contract

### Schema

```python
from datetime import date

class RobotPerformanceMetricsContract(BaseModel):
    """Aggregated robot performance metrics.

    Computed daily per (customer_id, robot_type, model_name).
    Used for competitive moat analysis and customer insights.
    """

    # === PRIMARY KEY ===
    metric_id: int = Field(..., description="Auto-increment primary key")

    # === AGGREGATION DIMENSIONS (unique constraint) ===
    customer_id: UUID = Field(..., description="Customer UUID (FK)")
    robot_type: RobotType = Field(..., description="Robot type (critical for moat)")
    model_name: ModelName = Field(..., description="VLA model used")
    aggregation_date: date = Field(..., description="Date of aggregation (unique per customer+robot+model+date)")

    # === COUNTS ===
    total_inferences: int = Field(..., ge=1, description="Total inferences for this day")
    success_count: int = Field(..., ge=0, description="Number of successful inferences")

    # === COMPUTED METRICS ===
    success_rate: float = Field(..., ge=0.0, le=1.0, description="success_count / total_inferences")

    # === LATENCY METRICS ===
    avg_latency_ms: float = Field(..., gt=0.0, description="Average latency in ms")
    p50_latency_ms: float = Field(..., gt=0.0, description="Median latency (50th percentile)")
    p95_latency_ms: float = Field(..., gt=0.0, description="95th percentile latency")
    p99_latency_ms: float = Field(..., gt=0.0, description="99th percentile latency")

    # === SAFETY METRICS ===
    avg_safety_score: float = Field(..., ge=0.0, le=1.0, description="Average safety score")

    # === ACTION STATISTICS (JSONB) ===
    action_statistics: dict = Field(
        ...,
        description="Statistics for each action dimension and magnitude",
    )

    # === COMMON PATTERNS ===
    common_instructions: List[str] = Field(
        ...,
        max_items=10,
        description="Top 10 most common instructions (each 3-500 chars)",
    )

    # === FAILURE PATTERNS (JSONB) ===
    failure_patterns: dict = Field(
        ...,
        description="Analysis of failures (timeouts, safety rejections, errors)",
    )

    # === VALIDATORS ===

    @validator('success_count')
    def validate_success_count(cls, v, values):
        """Ensure success_count <= total_inferences."""
        total = values.get('total_inferences')
        if total is not None and v > total:
            raise ValueError(f"success_count ({v}) cannot exceed total_inferences ({total})")
        return v

    @validator('success_rate')
    def validate_success_rate(cls, v, values):
        """Ensure success_rate matches success_count/total_inferences."""
        success = values.get('success_count')
        total = values.get('total_inferences')

        if success is not None and total is not None and total > 0:
            expected_rate = success / total
            if abs(v - expected_rate) > 0.001:  # Tolerance for floating point
                raise ValueError(
                    f"success_rate ({v}) does not match success_count/total_inferences "
                    f"({success}/{total} = {expected_rate})"
                )

        return v

    @validator('aggregation_date')
    def validate_aggregation_date(cls, v):
        """Ensure aggregation_date is not in the future."""
        today = date.today()
        if v > today:
            raise ValueError(f"aggregation_date cannot be in future. Got {v}, today is {today}")
        return v

    @root_validator
    def validate_latency_ordering(cls, values):
        """Ensure latency percentiles are properly ordered: p50 <= p95 <= p99."""
        p50 = values.get('p50_latency_ms')
        p95 = values.get('p95_latency_ms')
        p99 = values.get('p99_latency_ms')

        if p50 is not None and p95 is not None and p99 is not None:
            if not (p50 <= p95 <= p99):
                raise ValueError(
                    f"Latency percentiles must be ordered: p50 <= p95 <= p99. "
                    f"Got p50={p50}, p95={p95}, p99={p99}"
                )

        return values

    @validator('action_statistics')
    def validate_action_statistics(cls, v):
        """Validate action_statistics JSONB structure."""
        required_keys = [f'dof_{i}' for i in range(7)] + ['magnitude']

        for key in required_keys:
            if key not in v:
                raise ValueError(f"action_statistics missing required key: {key}")

            stats = v[key]
            if not isinstance(stats, dict):
                raise ValueError(f"action_statistics[{key}] must be a dict, got {type(stats)}")

            required_stats = ['mean', 'std', 'min', 'max']
            for stat in required_stats:
                if stat not in stats:
                    raise ValueError(f"action_statistics[{key}] missing required stat: {stat}")

                val = stats[stat]
                if not isinstance(val, (int, float)) or not math.isfinite(val):
                    raise ValueError(
                        f"action_statistics[{key}][{stat}] must be finite number, got {val}"
                    )

        return v

    @validator('failure_patterns')
    def validate_failure_patterns(cls, v):
        """Validate failure_patterns JSONB structure."""
        required_keys = ['timeout_rate', 'safety_rejection_rate', 'error_types', 'common_error_messages']

        for key in required_keys:
            if key not in v:
                raise ValueError(f"failure_patterns missing required key: {key}")

        # Validate rates are in [0, 1]
        for rate_key in ['timeout_rate', 'safety_rejection_rate']:
            rate = v[rate_key]
            if not isinstance(rate, (int, float)) or not (0.0 <= rate <= 1.0):
                raise ValueError(f"failure_patterns[{rate_key}] must be in [0, 1], got {rate}")

        # Validate error_types is a dict
        if not isinstance(v['error_types'], dict):
            raise ValueError(f"failure_patterns[error_types] must be a dict, got {type(v['error_types'])}")

        # Validate common_error_messages is a list
        if not isinstance(v['common_error_messages'], list):
            raise ValueError(
                f"failure_patterns[common_error_messages] must be a list, "
                f"got {type(v['common_error_messages'])}"
            )

        return v

    @validator('common_instructions')
    def validate_common_instructions(cls, v):
        """Validate common_instructions list."""
        if len(v) > 10:
            raise ValueError(f"common_instructions must have max 10 items, got {len(v)}")

        for i, instruction in enumerate(v):
            if not isinstance(instruction, str):
                raise ValueError(f"common_instructions[{i}] must be string, got {type(instruction)}")
            if not (3 <= len(instruction) <= 500):
                raise ValueError(
                    f"common_instructions[{i}] must be 3-500 chars, got {len(instruction)} chars"
                )

        return v

    class Config:
        use_enum_values = True
```

### action_statistics JSONB Schema

```python
class ActionDimensionStats(BaseModel):
    """Statistics for a single action dimension."""
    mean: float = Field(..., description="Mean value")
    std: float = Field(..., description="Standard deviation")
    min: float = Field(..., description="Minimum value")
    max: float = Field(..., description="Maximum value")

    @validator('*', pre=True, always=True)
    def validate_finite(cls, v):
        if not math.isfinite(v):
            raise ValueError(f"All stats must be finite numbers, got {v}")
        return v

class ActionStatistics(BaseModel):
    """Complete action statistics structure."""
    dof_0: ActionDimensionStats
    dof_1: ActionDimensionStats
    dof_2: ActionDimensionStats
    dof_3: ActionDimensionStats
    dof_4: ActionDimensionStats
    dof_5: ActionDimensionStats
    dof_6: ActionDimensionStats
    magnitude: ActionDimensionStats

# Example valid action_statistics
action_stats_example = {
    "dof_0": {"mean": 0.05, "std": 0.12, "min": -0.3, "max": 0.4},
    "dof_1": {"mean": -0.02, "std": 0.08, "min": -0.25, "max": 0.2},
    "dof_2": {"mean": 0.01, "std": 0.05, "min": -0.15, "max": 0.18},
    "dof_3": {"mean": 0.08, "std": 0.15, "min": -0.4, "max": 0.5},
    "dof_4": {"mean": -0.03, "std": 0.09, "min": -0.3, "max": 0.25},
    "dof_5": {"mean": 0.04, "std": 0.11, "min": -0.35, "max": 0.4},
    "dof_6": {"mean": 0.0, "std": 0.02, "min": -0.05, "max": 0.05},
    "magnitude": {"mean": 0.25, "std": 0.12, "min": 0.0, "max": 0.85},
}
```

### failure_patterns JSONB Schema

```python
class FailurePatterns(BaseModel):
    """Failure pattern analysis structure."""
    timeout_rate: float = Field(..., ge=0.0, le=1.0, description="Proportion of timeouts")
    safety_rejection_rate: float = Field(..., ge=0.0, le=1.0, description="Proportion of safety rejections")
    error_types: dict[str, int] = Field(..., description="Error type counts")
    common_error_messages: List[str] = Field(..., max_items=10, description="Top 10 error messages")

# Example valid failure_patterns
failure_patterns_example = {
    "timeout_rate": 0.02,  # 2% of inferences timed out
    "safety_rejection_rate": 0.05,  # 5% were safety rejected
    "error_types": {
        "model_inference_error": 3,
        "invalid_input": 1,
        "gpu_oom": 2,
    },
    "common_error_messages": [
        "CUDA out of memory",
        "Invalid image format",
        "Model inference timeout",
    ],
}
```

### Database Schema

```sql
CREATE TABLE vlaapi.robot_performance_metrics (
    metric_id SERIAL PRIMARY KEY,

    -- Aggregation dimensions (unique constraint)
    customer_id UUID NOT NULL REFERENCES vlaapi.customers(customer_id),
    robot_type VARCHAR(100) NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    aggregation_date DATE NOT NULL,

    -- Counts
    total_inferences INT NOT NULL CHECK (total_inferences >= 1),
    success_count INT NOT NULL CHECK (success_count >= 0),

    -- Computed metrics
    success_rate FLOAT NOT NULL CHECK (success_rate >= 0.0 AND success_rate <= 1.0),

    -- Latency metrics
    avg_latency_ms FLOAT NOT NULL CHECK (avg_latency_ms > 0.0),
    p50_latency_ms FLOAT NOT NULL CHECK (p50_latency_ms > 0.0),
    p95_latency_ms FLOAT NOT NULL CHECK (p95_latency_ms > 0.0),
    p99_latency_ms FLOAT NOT NULL CHECK (p99_latency_ms > 0.0),

    -- Safety metrics
    avg_safety_score FLOAT NOT NULL CHECK (avg_safety_score >= 0.0 AND avg_safety_score <= 1.0),

    -- JSONB columns
    action_statistics JSONB NOT NULL,
    failure_patterns JSONB NOT NULL,

    -- Common patterns
    common_instructions TEXT[] NOT NULL,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

    -- Unique constraint: one row per customer+robot+model+date
    CONSTRAINT uq_robot_metrics UNIQUE (customer_id, robot_type, model_name, aggregation_date),

    -- Ensure success_count <= total_inferences
    CONSTRAINT chk_success_count CHECK (success_count <= total_inferences),

    -- Ensure percentiles are ordered
    CONSTRAINT chk_latency_ordering CHECK (
        p50_latency_ms <= p95_latency_ms AND
        p95_latency_ms <= p99_latency_ms
    )
);

-- Indexes for queries
CREATE INDEX idx_robot_metrics_customer ON vlaapi.robot_performance_metrics(customer_id);
CREATE INDEX idx_robot_metrics_robot_type ON vlaapi.robot_performance_metrics(robot_type);
CREATE INDEX idx_robot_metrics_date ON vlaapi.robot_performance_metrics(aggregation_date DESC);
CREATE INDEX idx_robot_metrics_robot_model ON vlaapi.robot_performance_metrics(robot_type, model_name);
```

---

## Instruction Analytics Data Contract

### Schema

```python
from pgvector.sqlalchemy import Vector  # For embedding storage

class InstructionAnalyticsContract(BaseModel):
    """Analytics for unique instructions (deduplicated by hash).

    Used for:
    - Understanding common instruction patterns
    - Identifying high-value instructions for training data
    - Detecting unusual/rare instructions
    """

    # === PRIMARY KEY ===
    analytics_id: int = Field(..., description="Auto-increment primary key")

    # === DEDUPLICATION ===
    instruction_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA256 hash of normalized instruction (64 hex chars, unique)",
    )

    # === CLASSIFICATION ===
    instruction_category: InstructionCategory = Field(
        ...,
        description="Auto-classified instruction category",
    )

    # === EMBEDDING (optional, if enabled) ===
    instruction_embedding: Optional[List[float]] = Field(
        None,
        min_items=384,
        max_items=384,
        description="Sentence embedding (384-dim). Required if embeddings enabled.",
    )

    # === USAGE METRICS ===
    total_uses: int = Field(..., ge=1, description="Number of times this instruction was used")
    success_rate: float = Field(..., ge=0.0, le=1.0, description="Success rate across all uses")
    avg_safety_score: float = Field(..., ge=0.0, le=1.0, description="Average safety score")

    # === ROBOT CONTEXT ===
    common_robots: List[str] = Field(
        ...,
        max_items=5,
        description="Top 5 robot types that use this instruction",
    )

    # === PERFORMANCE ===
    avg_latency_ms: float = Field(..., gt=0.0, description="Average latency for this instruction")

    # === TEMPORAL TRACKING ===
    first_seen: datetime = Field(..., description="First time this instruction was seen")
    last_seen: datetime = Field(..., description="Last time this instruction was seen")

    # === VALIDATORS ===

    @validator('instruction_hash')
    def validate_instruction_hash(cls, v):
        """Ensure instruction_hash is valid SHA256 (64 hex characters)."""
        if len(v) != 64:
            raise ValueError(f"instruction_hash must be 64 characters (SHA256), got {len(v)}")

        # Check if valid hex
        try:
            int(v, 16)
        except ValueError:
            raise ValueError(f"instruction_hash must be valid hexadecimal, got: {v}")

        return v.lower()  # Normalize to lowercase

    @validator('instruction_embedding')
    def validate_instruction_embedding(cls, v):
        """Validate embedding dimensions and values."""
        if v is None:
            return v

        if len(v) != 384:
            raise ValueError(f"instruction_embedding must be exactly 384 dimensions, got {len(v)}")

        # Check for non-finite values
        non_finite = [i for i, x in enumerate(v) if not math.isfinite(x)]
        if non_finite:
            raise ValueError(
                f"instruction_embedding contains non-finite values at indices {non_finite[:10]}"
                + (f" (and {len(non_finite) - 10} more)" if len(non_finite) > 10 else "")
            )

        return v

    @validator('common_robots')
    def validate_common_robots(cls, v):
        """Validate common_robots list."""
        if len(v) > 5:
            raise ValueError(f"common_robots must have max 5 items, got {len(v)}")

        # Each robot must be a valid RobotType
        for i, robot in enumerate(v):
            try:
                RobotType(robot)
            except ValueError:
                raise ValueError(
                    f"common_robots[{i}] is not a valid RobotType: {robot}. "
                    f"Valid types: {[rt.value for rt in RobotType]}"
                )

        return v

    @root_validator
    def validate_temporal_consistency(cls, values):
        """Ensure first_seen <= last_seen."""
        first_seen = values.get('first_seen')
        last_seen = values.get('last_seen')

        if first_seen is not None and last_seen is not None:
            if first_seen > last_seen:
                raise ValueError(
                    f"first_seen ({first_seen}) cannot be after last_seen ({last_seen})"
                )

        return values

    class Config:
        use_enum_values = True
```

### Instruction Normalization and Hashing

```python
import hashlib
import re

def normalize_instruction(instruction: str) -> str:
    """Normalize instruction for consistent hashing.

    Steps:
    1. Lowercase
    2. Strip leading/trailing whitespace
    3. Collapse multiple spaces to single space
    4. Remove punctuation (keep apostrophes)
    5. Remove extra whitespace
    """
    # Lowercase
    normalized = instruction.lower()

    # Strip whitespace
    normalized = normalized.strip()

    # Remove punctuation (keep apostrophes for contractions)
    normalized = re.sub(r"[^\w\s']", '', normalized)

    # Collapse multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized)

    return normalized

def hash_instruction(instruction: str) -> str:
    """Generate SHA256 hash of normalized instruction.

    Args:
        instruction: Raw instruction text

    Returns:
        64-character hex string (SHA256 hash)
    """
    normalized = normalize_instruction(instruction)
    hash_obj = hashlib.sha256(normalized.encode('utf-8'))
    return hash_obj.hexdigest()

# Examples
assert hash_instruction("Pick up the red cube.") == hash_instruction("pick up the red cube")
assert hash_instruction("Pick  up   the red cube!") == hash_instruction("pick up the red cube")
assert hash_instruction("Don't move") == hash_instruction("dont move")  # Apostrophe removed
```

### Database Schema

```sql
-- Requires pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE vlaapi.instruction_analytics (
    analytics_id SERIAL PRIMARY KEY,

    -- Deduplication
    instruction_hash CHAR(64) NOT NULL UNIQUE,

    -- Classification
    instruction_category VARCHAR(50) NOT NULL,

    -- Embedding (384-dimensional, nullable)
    instruction_embedding vector(384),

    -- Usage metrics
    total_uses INT NOT NULL CHECK (total_uses >= 1),
    success_rate FLOAT NOT NULL CHECK (success_rate >= 0.0 AND success_rate <= 1.0),
    avg_safety_score FLOAT NOT NULL CHECK (avg_safety_score >= 0.0 AND avg_safety_score <= 1.0),

    -- Robot context
    common_robots TEXT[] NOT NULL,

    -- Performance
    avg_latency_ms FLOAT NOT NULL CHECK (avg_latency_ms > 0.0),

    -- Temporal tracking
    first_seen TIMESTAMP WITH TIME ZONE NOT NULL,
    last_seen TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Temporal consistency
    CONSTRAINT chk_temporal_consistency CHECK (first_seen <= last_seen)
);

-- Indexes
CREATE INDEX idx_instruction_analytics_hash ON vlaapi.instruction_analytics(instruction_hash);
CREATE INDEX idx_instruction_analytics_category ON vlaapi.instruction_analytics(instruction_category);
CREATE INDEX idx_instruction_analytics_uses ON vlaapi.instruction_analytics(total_uses DESC);
CREATE INDEX idx_instruction_analytics_last_seen ON vlaapi.instruction_analytics(last_seen DESC);

-- Vector similarity search index (if embeddings enabled)
CREATE INDEX idx_instruction_analytics_embedding ON vlaapi.instruction_analytics
USING ivfflat (instruction_embedding vector_cosine_ops)
WITH (lists = 100);
```

---

## Context Metadata Data Contract

### Schema

```python
class LightingConditions(str, Enum):
    BRIGHT = "bright"
    NORMAL = "normal"
    DIM = "dim"
    DARK = "dark"
    UNKNOWN = "unknown"

class EnvironmentType(str, Enum):
    LAB = "lab"
    WAREHOUSE = "warehouse"
    FACTORY = "factory"
    OUTDOOR = "outdoor"
    HOME = "home"
    OFFICE = "office"
    HOSPITAL = "hospital"
    RETAIL = "retail"
    OTHER = "other"

class WorkspaceBounds(BaseModel):
    """Workspace bounds in meters."""
    x: dict = Field(..., description="X-axis bounds {min: float, max: float}")
    y: dict = Field(..., description="Y-axis bounds {min: float, max: float}")
    z: dict = Field(..., description="Z-axis bounds {min: float, max: float}")
    units: str = Field("meters", description="Units (always 'meters')")
    coordinate_frame: str = Field("robot_base", description="Coordinate frame reference")

    @validator('x', 'y', 'z')
    def validate_bounds(cls, v, field):
        """Ensure min < max for each axis."""
        if 'min' not in v or 'max' not in v:
            raise ValueError(f"{field.name} must have 'min' and 'max' keys")

        min_val = v['min']
        max_val = v['max']

        if not isinstance(min_val, (int, float)) or not isinstance(max_val, (int, float)):
            raise ValueError(f"{field.name} min/max must be numbers")

        if not (math.isfinite(min_val) and math.isfinite(max_val)):
            raise ValueError(f"{field.name} min/max must be finite numbers")

        if min_val >= max_val:
            raise ValueError(
                f"{field.name} min ({min_val}) must be less than max ({max_val})"
            )

        # Reasonable workspace bounds (most robots work within ±5m)
        if not (-5.0 <= min_val <= 5.0):
            raise ValueError(f"{field.name} min ({min_val}) outside reasonable range [-5, 5] meters")
        if not (-5.0 <= max_val <= 5.0):
            raise ValueError(f"{field.name} max ({max_val}) outside reasonable range [-5, 5] meters")

        return v

class ContextMetadataContract(BaseModel):
    """Contextual metadata for each inference.

    Used for:
    - Understanding deployment environments
    - Analyzing performance in different contexts
    - Building context-aware models
    """

    # === PRIMARY KEY ===
    context_id: int = Field(..., description="Auto-increment primary key")

    # === FOREIGN KEYS ===
    log_id: int = Field(..., description="FK to inference_logs (required, indexed)")
    customer_id: UUID = Field(..., description="FK to customers (required, indexed)")

    # === TEMPORAL ===
    timestamp: datetime = Field(..., description="Must match inference_logs.timestamp")
    time_of_day: str = Field(..., description="Time extracted from timestamp (HH:MM:SS)")

    # === ROBOT CONTEXT ===
    robot_type: RobotType = Field(..., description="Must match inference robot_type")

    # === SPATIAL CONTEXT ===
    workspace_bounds: WorkspaceBounds = Field(..., description="Workspace boundaries in meters")

    # === ENVIRONMENTAL CONTEXT ===
    lighting_conditions: Optional[LightingConditions] = Field(
        None,
        description="Lighting conditions (optional)",
    )
    environment_type: EnvironmentType = Field(
        ...,
        description="REQUIRED for moat analysis. Type of deployment environment.",
    )

    # === GROUND TRUTH (if available) ===
    success: Optional[bool] = Field(
        None,
        description="Ground truth success (nullable, only if feedback available)",
    )

    # === PRIVACY-AWARE DATA ===
    image_embedding: Optional[List[float]] = Field(
        None,
        min_items=512,
        max_items=512,
        description="Image embedding (512-dim). Only if consent given.",
    )

    # === VALIDATORS ===

    @validator('time_of_day')
    def validate_time_of_day(cls, v):
        """Ensure time_of_day is in HH:MM:SS format."""
        time_pattern = re.compile(r'^([01]\d|2[0-3]):([0-5]\d):([0-5]\d)$')
        if not time_pattern.match(v):
            raise ValueError(f"time_of_day must be in HH:MM:SS format, got: {v}")
        return v

    @validator('image_embedding')
    def validate_image_embedding(cls, v):
        """Validate image embedding dimensions and values."""
        if v is None:
            return v

        if len(v) != 512:
            raise ValueError(f"image_embedding must be exactly 512 dimensions, got {len(v)}")

        # Check for non-finite values
        non_finite = [i for i, x in enumerate(v) if not math.isfinite(x)]
        if non_finite:
            raise ValueError(
                f"image_embedding contains non-finite values at indices {non_finite[:10]}"
            )

        return v

    class Config:
        use_enum_values = True
```

### Database Schema

```sql
CREATE TABLE vlaapi.context_metadata (
    context_id SERIAL PRIMARY KEY,

    -- Foreign keys
    log_id INT NOT NULL REFERENCES vlaapi.inference_logs(log_id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES vlaapi.customers(customer_id),

    -- Temporal
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    time_of_day TIME NOT NULL,

    -- Robot context
    robot_type VARCHAR(100) NOT NULL,

    -- Spatial context (JSONB)
    workspace_bounds JSONB NOT NULL,

    -- Environmental context
    lighting_conditions VARCHAR(20),
    environment_type VARCHAR(50) NOT NULL,

    -- Ground truth
    success BOOLEAN,

    -- Privacy-aware data (512-dimensional embedding)
    image_embedding vector(512),

    -- Constraints
    CONSTRAINT chk_lighting_conditions CHECK (lighting_conditions IN (
        'bright', 'normal', 'dim', 'dark', 'unknown'
    )),
    CONSTRAINT chk_environment_type CHECK (environment_type IN (
        'lab', 'warehouse', 'factory', 'outdoor', 'home',
        'office', 'hospital', 'retail', 'other'
    ))
);

-- Indexes
CREATE INDEX idx_context_metadata_log ON vlaapi.context_metadata(log_id);
CREATE INDEX idx_context_metadata_customer ON vlaapi.context_metadata(customer_id);
CREATE INDEX idx_context_metadata_robot ON vlaapi.context_metadata(robot_type);
CREATE INDEX idx_context_metadata_environment ON vlaapi.context_metadata(environment_type);
CREATE INDEX idx_context_metadata_timestamp ON vlaapi.context_metadata(timestamp DESC);

-- Vector similarity index for image embeddings
CREATE INDEX idx_context_metadata_embedding ON vlaapi.context_metadata
USING ivfflat (image_embedding vector_cosine_ops)
WITH (lists = 100);
```

---

## Customer Data Consent Data Contract

### Schema

```python
class ConsentTier(str, Enum):
    NONE = "none"           # No data collection beyond required
    METADATA = "metadata"   # Collect metadata and embeddings
    FULL = "full"           # Full data collection including images

class AnonymizationLevel(str, Enum):
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

    @root_validator
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

    @root_validator
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
```

### Database Schema

```sql
CREATE TABLE vlaapi.customer_data_consent (
    consent_id SERIAL PRIMARY KEY,

    -- Customer (unique - one consent record per customer)
    customer_id UUID NOT NULL UNIQUE REFERENCES vlaapi.customers(customer_id),

    -- Consent configuration
    consent_tier VARCHAR(20) NOT NULL,
    consent_version INT NOT NULL CHECK (consent_version >= 1),

    -- Temporal
    consented_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,

    -- Granular permissions
    can_store_images BOOLEAN NOT NULL,
    can_store_embeddings BOOLEAN NOT NULL,
    can_use_for_training BOOLEAN NOT NULL,

    -- Anonymization
    anonymization_level VARCHAR(20) NOT NULL,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

    -- Constraints
    CONSTRAINT chk_consent_tier CHECK (consent_tier IN ('none', 'metadata', 'full')),
    CONSTRAINT chk_anonymization_level CHECK (anonymization_level IN ('none', 'partial', 'full')),
    CONSTRAINT chk_expiration CHECK (expires_at IS NULL OR expires_at > consented_at),

    -- Consent tier logic
    CONSTRAINT chk_none_tier CHECK (
        consent_tier != 'none' OR
        (can_store_images = false AND can_store_embeddings = false AND can_use_for_training = false)
    ),
    CONSTRAINT chk_metadata_tier CHECK (
        consent_tier != 'metadata' OR
        (can_store_images = false AND can_store_embeddings = true AND can_use_for_training = true)
    ),
    CONSTRAINT chk_full_tier CHECK (
        consent_tier != 'full' OR
        (can_store_images = true AND can_store_embeddings = true AND can_use_for_training = true)
    ),

    -- Anonymization logic
    CONSTRAINT chk_anonymization CHECK (
        can_store_images = false OR anonymization_level != 'none'
    )
);

-- Indexes
CREATE INDEX idx_consent_customer ON vlaapi.customer_data_consent(customer_id);
CREATE INDEX idx_consent_tier ON vlaapi.customer_data_consent(consent_tier);
CREATE INDEX idx_consent_expires ON vlaapi.customer_data_consent(expires_at)
WHERE expires_at IS NOT NULL;
```

---

## Safety Incidents Data Contract

### Schema Extensions

```python
class SafetyIncidentContract(BaseModel):
    """Extended safety incident model with robot and environment context.

    EXTENDS existing safety_incidents table with critical fields for moat analysis.
    """

    # === EXISTING FIELDS (from current schema) ===
    incident_id: int = Field(..., description="Auto-increment primary key")
    log_id: Optional[int] = Field(None, description="FK to inference_logs (nullable)")
    customer_id: UUID = Field(..., description="FK to customers")
    timestamp: datetime = Field(..., description="When incident occurred")
    severity: str = Field(..., description="low, medium, high, critical")
    violation_type: str = Field(..., description="collision, workspace, velocity, classifier")
    violation_details: dict = Field(..., description="JSONB details")
    action_taken: str = Field(..., description="logged, clamped, rejected, emergency_stop")
    original_action: Optional[List[float]] = Field(None, description="Original 7-DoF action")
    safe_action: Optional[List[float]] = Field(None, description="Clamped/modified action")

    # === NEW REQUIRED FIELDS ===
    robot_type: RobotType = Field(
        ...,
        description="CRITICAL: Robot type. Missing in current schema!",
    )
    environment_type: EnvironmentType = Field(
        ...,
        description="Deployment environment for contextual safety analysis",
    )
    instruction_category: InstructionCategory = Field(
        ...,
        description="Instruction category for pattern detection",
    )

    # === VALIDATORS ===

    @validator('severity')
    def validate_severity(cls, v, values):
        """Validate severity logic based on violation type."""
        violation_type = values.get('violation_type')

        if violation_type == 'collision' and v not in ['high', 'critical']:
            raise ValueError(
                f"Collision violations must have severity 'high' or 'critical', got '{v}'"
            )

        return v

    @validator('action_taken')
    def validate_action_taken(cls, v, values):
        """Validate action_taken based on severity."""
        severity = values.get('severity')

        if severity == 'critical' and v not in ['emergency_stop', 'rejected']:
            raise ValueError(
                f"Critical severity incidents must have action_taken 'emergency_stop' or "
                f"'rejected', got '{v}'"
            )

        return v

    @root_validator
    def validate_action_modification(cls, values):
        """Ensure original_action and safe_action are different if clamped."""
        action_taken = values.get('action_taken')
        original_action = values.get('original_action')
        safe_action = values.get('safe_action')

        if action_taken == 'clamped':
            if original_action is None or safe_action is None:
                raise ValueError(
                    "If action_taken='clamped', both original_action and safe_action must be provided"
                )

            if original_action == safe_action:
                raise ValueError(
                    "If action_taken='clamped', original_action and safe_action must be different"
                )

        return values
```

### Database Schema Migration

```sql
-- Add new columns to existing safety_incidents table
ALTER TABLE vlaapi.safety_incidents
ADD COLUMN robot_type VARCHAR(100) NOT NULL DEFAULT 'unknown',
ADD COLUMN environment_type VARCHAR(50) NOT NULL DEFAULT 'other',
ADD COLUMN instruction_category VARCHAR(50);

-- Add constraints
ALTER TABLE vlaapi.safety_incidents
ADD CONSTRAINT chk_robot_type CHECK (robot_type IN (
    'franka_panda', 'franka_fr3', 'universal_robots_ur5', 'universal_robots_ur5e',
    'universal_robots_ur10', 'abb_yumi', 'kuka_iiwa7', 'kinova_gen3',
    'rethink_sawyer', 'ufactory_xarm7', 'fetch_robotics_fetch', 'custom', 'unknown'
)),
ADD CONSTRAINT chk_environment_type CHECK (environment_type IN (
    'lab', 'warehouse', 'factory', 'outdoor', 'home',
    'office', 'hospital', 'retail', 'other'
)),
ADD CONSTRAINT chk_instruction_category CHECK (instruction_category IN (
    'pick', 'place', 'navigate', 'manipulate', 'inspect', 'measure',
    'open', 'close', 'push', 'pull', 'other'
));

-- Add severity/action_taken logic constraints
ALTER TABLE vlaapi.safety_incidents
ADD CONSTRAINT chk_collision_severity CHECK (
    violation_type != 'collision' OR severity IN ('high', 'critical')
),
ADD CONSTRAINT chk_critical_action CHECK (
    severity != 'critical' OR action_taken IN ('emergency_stop', 'rejected')
);

-- Add indexes for new fields
CREATE INDEX idx_incidents_robot_type ON vlaapi.safety_incidents(robot_type);
CREATE INDEX idx_incidents_environment ON vlaapi.safety_incidents(environment_type);
CREATE INDEX idx_incidents_category ON vlaapi.safety_incidents(instruction_category);
CREATE INDEX idx_incidents_robot_severity ON vlaapi.safety_incidents(robot_type, severity);
```

---

## Feedback Data Contract

### Schema

```python
class FeedbackType(str, Enum):
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
```

### Database Schema

```sql
CREATE TABLE vlaapi.feedback (
    feedback_id SERIAL PRIMARY KEY,

    -- Foreign keys
    log_id INT NOT NULL REFERENCES vlaapi.inference_logs(log_id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES vlaapi.customers(customer_id),

    -- Feedback type
    feedback_type VARCHAR(50) NOT NULL,

    -- Type-specific fields (nullable, validated by application)
    rating INT CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5)),
    corrected_action FLOAT[],
    failure_reason TEXT,

    -- Optional notes
    notes TEXT,

    -- Temporal
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

    -- Constraints
    CONSTRAINT chk_feedback_type CHECK (feedback_type IN (
        'success_rating', 'safety_rating', 'action_correction', 'failure_report'
    )),

    -- Ensure rating is provided for rating types
    CONSTRAINT chk_rating_required CHECK (
        (feedback_type NOT IN ('success_rating', 'safety_rating')) OR
        (rating IS NOT NULL)
    ),

    -- Ensure corrected_action is provided for correction type
    CONSTRAINT chk_corrected_action_required CHECK (
        feedback_type != 'action_correction' OR
        corrected_action IS NOT NULL
    ),

    -- Ensure failure_reason is provided for failure report
    CONSTRAINT chk_failure_reason_required CHECK (
        feedback_type != 'failure_report' OR
        failure_reason IS NOT NULL
    )
);

-- Indexes
CREATE INDEX idx_feedback_log ON vlaapi.feedback(log_id);
CREATE INDEX idx_feedback_customer ON vlaapi.feedback(customer_id);
CREATE INDEX idx_feedback_type ON vlaapi.feedback(feedback_type);
CREATE INDEX idx_feedback_timestamp ON vlaapi.feedback(timestamp DESC);
CREATE INDEX idx_feedback_rating ON vlaapi.feedback(rating) WHERE rating IS NOT NULL;
```

---

## Deduplication Logic

### 1. Inference Request Deduplication

**Primary Strategy:** UUID-based deduplication using `request_id`

**Implementation:**

```python
from datetime import timedelta
from typing import Optional
import redis

class InferenceDeduplicator:
    """Handle inference request deduplication."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.dedup_window_seconds = 60  # 60-second deduplication window
        self.cache_expiry_seconds = 300  # 5-minute response cache

    def check_duplicate(self, request_id: str) -> tuple[bool, Optional[dict]]:
        """Check if request_id is a duplicate.

        Returns:
            (is_duplicate, cached_response)
        """
        # Check if we've seen this request_id recently
        key = f"inference:dedup:{request_id}"

        # Try to get cached response
        cached = self.redis.get(key)

        if cached is not None:
            # This is a duplicate within the deduplication window
            import json
            cached_response = json.loads(cached)

            # Log deduplication event
            self._log_deduplication_event(request_id, cached_response)

            return True, cached_response

        return False, None

    def register_request(self, request_id: str, response: dict):
        """Register a new request and cache its response.

        Args:
            request_id: UUID of the inference request
            response: API response to cache for potential duplicates
        """
        import json

        key = f"inference:dedup:{request_id}"
        value = json.dumps(response)

        # Store with TTL (time to live)
        self.redis.setex(
            key,
            self.cache_expiry_seconds,
            value,
        )

    def _log_deduplication_event(self, request_id: str, cached_response: dict):
        """Log deduplication event for monitoring."""
        # Increment deduplication counter
        self.redis.incr("metrics:inference:duplicates:count")

        # Store in time-series for alerting
        import time
        timestamp = int(time.time())
        self.redis.zadd(
            "metrics:inference:duplicates:timeline",
            {request_id: timestamp},
        )

        # If deduplication rate is high, trigger alert
        self._check_deduplication_rate()

    def _check_deduplication_rate(self):
        """Check if deduplication rate exceeds threshold."""
        import time

        # Get duplicates in last hour
        one_hour_ago = int(time.time()) - 3600
        recent_duplicates = self.redis.zcount(
            "metrics:inference:duplicates:timeline",
            one_hour_ago,
            "+inf",
        )

        # Get total requests in last hour
        total_requests = self.redis.get("metrics:inference:total:last_hour")
        total_requests = int(total_requests) if total_requests else 0

        if total_requests > 0:
            dedup_rate = recent_duplicates / total_requests

            # Alert if >10% deduplication (indicates client bug)
            if dedup_rate > 0.10:
                # Send alert to monitoring system
                self._send_alert(
                    "HIGH_DEDUPLICATION_RATE",
                    f"Deduplication rate is {dedup_rate:.1%} (threshold: 10%)",
                )

    def _send_alert(self, alert_type: str, message: str):
        """Send alert to monitoring system."""
        # TODO: Implement alert sending (PagerDuty, Slack, etc.)
        print(f"ALERT [{alert_type}]: {message}")
```

**Usage in API:**

```python
@app.post("/v1/inference")
async def inference_endpoint(request: InferenceRequest):
    # Generate request_id if not provided
    request_id = request.request_id or uuid.uuid4()

    # Check for duplicates
    deduplicator = InferenceDeduplicator(redis_client)
    is_duplicate, cached_response = deduplicator.check_duplicate(str(request_id))

    if is_duplicate:
        # Return cached response, don't charge customer again
        return cached_response

    # Process new inference
    response = await process_inference(request)

    # Cache response for deduplication
    deduplicator.register_request(str(request_id), response)

    return response
```

### 2. Instruction Deduplication

**Primary Strategy:** SHA256 hash of normalized instruction text

**Implementation:**

```python
from typing import Optional
from datetime import datetime

class InstructionDeduplicator:
    """Handle instruction analytics deduplication."""

    def __init__(self, db_session):
        self.db = db_session

    async def deduplicate_instruction(
        self,
        instruction: str,
        robot_type: str,
        success: bool,
        safety_score: float,
        latency_ms: float,
        embedding: Optional[List[float]] = None,
    ) -> int:
        """Deduplicate instruction and update analytics.

        Returns:
            analytics_id of the instruction analytics record
        """
        # Generate hash
        instruction_hash = hash_instruction(instruction)
        instruction_category = classify_instruction(instruction)

        # Try to find existing analytics record
        existing = await self.db.execute(
            "SELECT analytics_id, total_uses, success_rate, avg_safety_score, avg_latency_ms "
            "FROM vlaapi.instruction_analytics WHERE instruction_hash = %s",
            (instruction_hash,),
        )

        now = datetime.utcnow()

        if existing:
            # Update existing record
            analytics_id, total_uses, success_rate, avg_safety_score, avg_latency_ms = existing[0]

            # Compute new metrics (exponential moving average)
            new_total_uses = total_uses + 1
            new_success_rate = (success_rate * total_uses + (1.0 if success else 0.0)) / new_total_uses
            new_avg_safety_score = (avg_safety_score * total_uses + safety_score) / new_total_uses
            new_avg_latency_ms = (avg_latency_ms * total_uses + latency_ms) / new_total_uses

            # Update common_robots list
            await self._update_common_robots(analytics_id, robot_type)

            # Update record
            await self.db.execute(
                """
                UPDATE vlaapi.instruction_analytics
                SET total_uses = %s,
                    success_rate = %s,
                    avg_safety_score = %s,
                    avg_latency_ms = %s,
                    last_seen = %s
                WHERE analytics_id = %s
                """,
                (
                    new_total_uses,
                    new_success_rate,
                    new_avg_safety_score,
                    new_avg_latency_ms,
                    now,
                    analytics_id,
                ),
            )

            return analytics_id

        else:
            # Create new record
            result = await self.db.execute(
                """
                INSERT INTO vlaapi.instruction_analytics (
                    instruction_hash, instruction_category, instruction_embedding,
                    total_uses, success_rate, avg_safety_score, common_robots,
                    avg_latency_ms, first_seen, last_seen
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING analytics_id
                """,
                (
                    instruction_hash,
                    instruction_category,
                    embedding,
                    1,  # total_uses
                    1.0 if success else 0.0,  # success_rate
                    safety_score,
                    [robot_type],  # common_robots
                    latency_ms,
                    now,
                    now,
                ),
            )

            return result[0][0]

    async def check_semantic_duplicate(
        self,
        embedding: List[float],
        similarity_threshold: float = 0.95,
    ) -> Optional[int]:
        """Check for semantically similar instructions using embeddings.

        Returns:
            analytics_id of similar instruction if found, None otherwise
        """
        if embedding is None:
            return None

        # Query for similar embeddings using cosine similarity
        result = await self.db.execute(
            """
            SELECT analytics_id, instruction_embedding <=> %s::vector AS distance
            FROM vlaapi.instruction_analytics
            WHERE instruction_embedding IS NOT NULL
            ORDER BY instruction_embedding <=> %s::vector
            LIMIT 1
            """,
            (embedding, embedding),
        )

        if result and len(result) > 0:
            analytics_id, distance = result[0]

            # Convert distance to similarity (cosine distance: 0 = identical, 2 = opposite)
            similarity = 1.0 - (distance / 2.0)

            if similarity >= similarity_threshold:
                # Flag as potential semantic duplicate
                await self._flag_semantic_duplicate(analytics_id)
                return analytics_id

        return None

    async def _update_common_robots(self, analytics_id: int, robot_type: str):
        """Update the common_robots list for an instruction."""
        # Get current common_robots
        result = await self.db.execute(
            "SELECT common_robots FROM vlaapi.instruction_analytics WHERE analytics_id = %s",
            (analytics_id,),
        )

        if result:
            common_robots = result[0][0] or []

            # Add robot_type if not already in list
            if robot_type not in common_robots:
                common_robots.append(robot_type)

                # Keep only top 5 (TODO: implement frequency-based ranking)
                common_robots = common_robots[:5]

                # Update database
                await self.db.execute(
                    "UPDATE vlaapi.instruction_analytics SET common_robots = %s WHERE analytics_id = %s",
                    (common_robots, analytics_id),
                )

    async def _flag_semantic_duplicate(self, analytics_id: int):
        """Flag potential semantic duplicate for manual review."""
        # TODO: Implement flagging system (e.g., add to review queue)
        pass
```

### 3. Robot Performance Deduplication

**Primary Strategy:** Unique constraint on (customer_id, robot_type, model_name, aggregation_date)

**Implementation:**

```python
class RobotPerformanceDeduplicator:
    """Handle robot performance metrics deduplication."""

    def __init__(self, db_session):
        self.db = db_session

    async def upsert_daily_metrics(
        self,
        customer_id: str,
        robot_type: str,
        model_name: str,
        aggregation_date: date,
        metrics: dict,
    ):
        """Insert or update daily metrics for a customer+robot+model combination.

        Uses PostgreSQL's ON CONFLICT to handle deduplication.
        """
        await self.db.execute(
            """
            INSERT INTO vlaapi.robot_performance_metrics (
                customer_id, robot_type, model_name, aggregation_date,
                total_inferences, success_count, success_rate,
                avg_latency_ms, p50_latency_ms, p95_latency_ms, p99_latency_ms,
                avg_safety_score, action_statistics, failure_patterns, common_instructions
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (customer_id, robot_type, model_name, aggregation_date)
            DO UPDATE SET
                total_inferences = EXCLUDED.total_inferences,
                success_count = EXCLUDED.success_count,
                success_rate = EXCLUDED.success_rate,
                avg_latency_ms = EXCLUDED.avg_latency_ms,
                p50_latency_ms = EXCLUDED.p50_latency_ms,
                p95_latency_ms = EXCLUDED.p95_latency_ms,
                p99_latency_ms = EXCLUDED.p99_latency_ms,
                avg_safety_score = EXCLUDED.avg_safety_score,
                action_statistics = EXCLUDED.action_statistics,
                failure_patterns = EXCLUDED.failure_patterns,
                common_instructions = EXCLUDED.common_instructions
            """,
            (
                customer_id,
                robot_type,
                model_name,
                aggregation_date,
                metrics['total_inferences'],
                metrics['success_count'],
                metrics['success_rate'],
                metrics['avg_latency_ms'],
                metrics['p50_latency_ms'],
                metrics['p95_latency_ms'],
                metrics['p99_latency_ms'],
                metrics['avg_safety_score'],
                metrics['action_statistics'],
                metrics['failure_patterns'],
                metrics['common_instructions'],
            ),
        )
```

---

## Quality Gates

### Hard Rejections (Don't Store, Don't Charge)

```python
class InferenceQualityGate:
    """Quality gate for inference requests."""

    @staticmethod
    def validate_inference(inference: InferenceLogContract) -> tuple[bool, Optional[str]]:
        """Validate inference against quality gates.

        Returns:
            (is_valid, rejection_reason)
        """
        # 1. Missing required fields
        if not all([
            inference.request_id,
            inference.customer_id,
            inference.model_name,
            inference.instruction,
            inference.action_vector,
            inference.robot_type,
        ]):
            return False, "MISSING_REQUIRED_FIELDS: One or more required fields are missing"

        # 2. Invalid action_vector (already validated by Pydantic, but double-check)
        if len(inference.action_vector) != 7:
            return False, f"INVALID_ACTION_VECTOR: Wrong dimensions ({len(inference.action_vector)}, expected 7)"

        if any(not math.isfinite(x) for x in inference.action_vector):
            return False, "INVALID_ACTION_VECTOR: Contains non-finite values (NaN/inf)"

        # 3. Invalid robot_type (CRITICAL for moat)
        if inference.robot_type == RobotType.UNKNOWN:
            return False, "INVALID_ROBOT_TYPE: robot_type cannot be UNKNOWN (critical for moat analysis)"

        # 4. Invalid timestamps
        now = datetime.utcnow()
        if inference.timestamp > now:
            return False, f"INVALID_TIMESTAMP: Timestamp in future ({inference.timestamp} > {now})"

        # 5. Duplicate request_id (check in deduplicator)
        # This is handled by InferenceDeduplicator.check_duplicate()

        # 6. Action vector out of bounds for robot type
        if inference.robot_type in ROBOT_SPECS:
            spec = ROBOT_SPECS[inference.robot_type]
            joint_limits = spec['joint_limits']

            for i, (action_val, (min_val, max_val)) in enumerate(
                zip(inference.action_vector[:spec['dof']], joint_limits)
            ):
                if not (min_val <= action_val <= max_val):
                    return False, (
                        f"INVALID_ACTION_BOUNDS: Joint {i} value {action_val} "
                        f"outside limits [{min_val}, {max_val}] for {inference.robot_type}"
                    )

        return True, None

# Usage in API
@app.post("/v1/inference")
async def inference_endpoint(request: InferenceRequest):
    try:
        # Validate request
        inference = InferenceLogContract(**request.dict())
    except ValidationError as e:
        # Pydantic validation failed
        return JSONResponse(
            status_code=400,
            content={"error": "VALIDATION_FAILED", "details": str(e)},
        )

    # Quality gate check
    is_valid, rejection_reason = InferenceQualityGate.validate_inference(inference)

    if not is_valid:
        # HARD REJECTION: Don't store, don't charge, return error immediately
        logger.error(f"Inference rejected: {rejection_reason}", extra={"request_id": inference.request_id})

        # Increment rejection metrics
        metrics.increment("inference.rejections.hard", tags={"reason": rejection_reason.split(":")[0]})

        return JSONResponse(
            status_code=400,
            content={"error": rejection_reason},
        )

    # Process inference...
```

### Soft Rejections (Store with Warnings)

```python
class InferenceWarningChecker:
    """Check for warning conditions in inference data."""

    @staticmethod
    def check_warnings(inference: InferenceLogContract) -> List[str]:
        """Check for soft issues that should trigger warnings.

        Returns:
            List of warning messages
        """
        warnings = []

        # 1. Missing optional fields
        if inference.image_shape is None:
            warnings.append("MISSING_OPTIONAL: image_shape not provided")

        if inference.queue_wait_ms is None:
            warnings.append("MISSING_OPTIONAL: queue_wait_ms not provided")

        # 2. Outlier latencies (>p99.9)
        if inference.robot_type in ROBOT_SPECS:
            spec = ROBOT_SPECS[inference.robot_type]
            expected_p95 = spec['expected_latency_p95']

            if inference.inference_latency_ms is not None:
                # 3 standard deviations above p95 is ~p99.9
                outlier_threshold = expected_p95 * 2.0

                if inference.inference_latency_ms > outlier_threshold:
                    warnings.append(
                        f"LATENCY_OUTLIER: {inference.inference_latency_ms}ms "
                        f"(expected p95: {expected_p95}ms, threshold: {outlier_threshold}ms)"
                    )

        # 3. Extreme action values (beyond typical robot ranges)
        if inference.action_magnitude is not None and inference.action_magnitude > 2.0:
            warnings.append(
                f"EXTREME_ACTION: action_magnitude={inference.action_magnitude} (typical: <1.0)"
            )

        # 4. Low safety score
        if inference.safety_score is not None and inference.safety_score < 0.3:
            warnings.append(
                f"LOW_SAFETY_SCORE: {inference.safety_score} (investigate failure modes)"
            )

        return warnings

# Usage in data collection
async def store_inference(inference: InferenceLogContract):
    # Check for warnings
    warnings = InferenceWarningChecker.check_warnings(inference)

    if warnings:
        # Log warnings for investigation
        logger.warning(
            f"Inference has warnings: {', '.join(warnings)}",
            extra={"request_id": inference.request_id, "warnings": warnings},
        )

        # Increment warning metrics
        for warning in warnings:
            warning_type = warning.split(":")[0]
            metrics.increment("inference.warnings", tags={"type": warning_type})

    # Store inference (even with warnings)
    await db.store_inference(inference)
```

### Alerting Thresholds

```python
class InferenceAlerts:
    """Monitor inference quality metrics and send alerts."""

    def __init__(self, metrics_client, alert_client):
        self.metrics = metrics_client
        self.alerts = alert_client

    async def check_quality_metrics(self):
        """Check quality metrics and trigger alerts if thresholds exceeded."""
        # Get metrics for last hour
        time_window = 3600  # 1 hour

        # 1. Hard rejection rate >1% → page on-call engineer
        hard_rejection_rate = await self.metrics.get_rate(
            "inference.rejections.hard",
            time_window,
        )

        if hard_rejection_rate > 0.01:  # 1%
            await self.alerts.page(
                severity="critical",
                title="High Hard Rejection Rate",
                description=f"Inference hard rejection rate is {hard_rejection_rate:.2%} (threshold: 1%)",
                tags={"component": "inference", "metric": "hard_rejection_rate"},
            )

        # 2. Missing robot_type rate >5% → data quality alert
        missing_robot_type_rate = await self.metrics.get_rate(
            "inference.warnings",
            time_window,
            tags={"type": "MISSING_ROBOT_TYPE"},
        )

        if missing_robot_type_rate > 0.05:  # 5%
            await self.alerts.send(
                severity="warning",
                title="High Missing Robot Type Rate",
                description=f"Missing robot_type rate is {missing_robot_type_rate:.2%} (threshold: 5%)",
                tags={"component": "data_quality", "metric": "missing_robot_type"},
            )

        # 3. NaN action_vector rate >0.1% → model health alert
        nan_action_rate = await self.metrics.get_rate(
            "inference.rejections.hard",
            time_window,
            tags={"reason": "INVALID_ACTION_VECTOR"},
        )

        if nan_action_rate > 0.001:  # 0.1%
            await self.alerts.send(
                severity="critical",
                title="High NaN Action Vector Rate",
                description=f"NaN action_vector rate is {nan_action_rate:.2%} (threshold: 0.1%)",
                tags={"component": "model", "metric": "nan_action_rate"},
            )

        # 4. Deduplication rate >10% → client bug alert
        dedup_rate = await self.metrics.get_rate(
            "metrics:inference:duplicates:count",
            time_window,
        )

        if dedup_rate > 0.10:  # 10%
            await self.alerts.send(
                severity="warning",
                title="High Deduplication Rate",
                description=f"Deduplication rate is {dedup_rate:.2%} (threshold: 10%) - possible client bug",
                tags={"component": "api", "metric": "dedup_rate"},
            )
```

---

## Validation Implementation

All Pydantic models are defined inline in each contract section above. To use them:

```python
# In your application code
from pydantic import ValidationError

# Example: Validate inference data
try:
    inference = InferenceLogContract(**raw_data)

    # If validation passes, data is guaranteed to be correct
    await store_inference(inference)

except ValidationError as e:
    # Validation failed - reject request
    logger.error(f"Validation failed: {e}")
    return {"error": "VALIDATION_FAILED", "details": e.errors()}
```

---

## Data Quality Monitoring

### Dashboard Metrics

Track these metrics in your monitoring dashboard (Grafana, Datadog, etc.):

#### Inference Quality

```
1. Hard Rejection Rate (target: <1%)
   - Total hard rejections / Total requests
   - Breakdown by rejection reason

2. Soft Warning Rate (target: <5%)
   - Total warnings / Total requests
   - Breakdown by warning type

3. Missing Robot Type Rate (target: 0%)
   - Inferences with robot_type=unknown / Total inferences

4. NaN Action Vector Rate (target: <0.1%)
   - Inferences with NaN in action_vector / Total inferences

5. Deduplication Rate (target: <10%)
   - Duplicate requests / Total requests
```

#### Latency Monitoring

```
6. Latency Outlier Rate (target: <0.1%)
   - Inferences with latency >p99.9 / Total inferences

7. Latency by Robot Type
   - p50, p95, p99 latency per robot type
   - Compare against expected latency

8. Queue Wait Time Trends
   - Track queue_wait_ms over time
   - Alert if >30 seconds
```

#### Safety Monitoring

```
9. Safety Rejection Rate (target: <2%)
   - status=safety_rejected / Total inferences

10. Low Safety Score Rate (target: <5%)
    - Inferences with safety_score <0.3 / Total inferences

11. Safety Incident Rate by Robot Type
    - Track safety incidents per robot type
    - Identify problematic robot models
```

#### Data Completeness

```
12. Optional Field Completeness
    - % of inferences with image_shape
    - % of inferences with safety_score
    - % of inferences with latency metrics

13. Feedback Rate (target: >1%)
    - Feedback entries / Total inferences
    - Track feedback by type

14. Context Metadata Completeness (target: >90%)
    - Context records / Total inferences
    - Track environment_type distribution
```

### SQL Queries for Monitoring

```sql
-- Daily quality metrics
CREATE MATERIALIZED VIEW vlaapi.daily_quality_metrics AS
SELECT
    DATE(timestamp) AS metric_date,
    COUNT(*) AS total_inferences,

    -- Hard rejections (status=error)
    COUNT(*) FILTER (WHERE status = 'error') AS hard_rejections,
    ROUND(COUNT(*) FILTER (WHERE status = 'error')::NUMERIC / COUNT(*) * 100, 2) AS hard_rejection_rate,

    -- Missing robot_type
    COUNT(*) FILTER (WHERE robot_type = 'unknown') AS missing_robot_type,
    ROUND(COUNT(*) FILTER (WHERE robot_type = 'unknown')::NUMERIC / COUNT(*) * 100, 2) AS missing_robot_type_rate,

    -- Safety rejections
    COUNT(*) FILTER (WHERE status = 'safety_rejected') AS safety_rejections,
    ROUND(COUNT(*) FILTER (WHERE status = 'safety_rejected')::NUMERIC / COUNT(*) * 100, 2) AS safety_rejection_rate,

    -- Low safety scores
    COUNT(*) FILTER (WHERE safety_score < 0.3) AS low_safety_scores,
    ROUND(COUNT(*) FILTER (WHERE safety_score < 0.3)::NUMERIC / COUNT(*) * 100, 2) AS low_safety_score_rate,

    -- Latency outliers (>5 seconds)
    COUNT(*) FILTER (WHERE inference_latency_ms > 5000) AS latency_outliers,
    ROUND(COUNT(*) FILTER (WHERE inference_latency_ms > 5000)::NUMERIC / COUNT(*) * 100, 2) AS latency_outlier_rate,

    -- Completeness
    COUNT(*) FILTER (WHERE image_shape IS NOT NULL) AS has_image_shape,
    ROUND(COUNT(*) FILTER (WHERE image_shape IS NOT NULL)::NUMERIC / COUNT(*) * 100, 2) AS image_shape_completeness,

    COUNT(*) FILTER (WHERE safety_score IS NOT NULL) AS has_safety_score,
    ROUND(COUNT(*) FILTER (WHERE safety_score IS NOT NULL)::NUMERIC / COUNT(*) * 100, 2) AS safety_score_completeness

FROM vlaapi.inference_logs
GROUP BY DATE(timestamp)
ORDER BY metric_date DESC;

-- Refresh daily
CREATE INDEX idx_daily_quality_metrics_date ON vlaapi.daily_quality_metrics(metric_date DESC);
```

---

## Summary

This document defines the complete data contracts for the VLA Inference API data collection system. Key takeaways:

### Critical Fields for Competitive Moat

1. **robot_type** - MUST be present and valid (cannot be UNKNOWN)
2. **environment_type** - Required for contextual analysis
3. **instruction_category** - Auto-classified for pattern detection
4. **action_vector** - MUST be 7-DoF, all finite, within robot bounds
5. **safety_score** - Critical for safety analysis

### Quality Gates Summary

**Hard Rejections (don't store, don't charge):**
- Missing required fields
- Invalid action_vector (NaN, inf, wrong dims)
- Invalid robot_type (UNKNOWN)
- Future timestamps
- Duplicate request_id (within 60s)

**Soft Warnings (store with investigation):**
- Missing optional fields
- Latency outliers (>p99.9)
- Extreme action values
- Low safety scores (<0.3)

### Alerting Thresholds

- Hard rejection rate >1% → Page on-call engineer
- Missing robot_type rate >5% → Data quality alert
- NaN action_vector rate >0.1% → Model health alert
- Deduplication rate >10% → Client bug alert

### Implementation Priority

**Week 1:**
1. Extend `inference_logs` table with `robot_type`, `instruction_category`, `action_magnitude`
2. Implement Pydantic validation for `InferenceLogContract`
3. Add hard rejection quality gates
4. Implement request deduplication

**Week 2:**
5. Create `robot_performance_metrics` table and aggregation pipeline
6. Create `instruction_analytics` table with deduplication
7. Implement soft warning checks
8. Set up monitoring dashboard

**Week 3:**
9. Create `context_metadata` table
10. Create `customer_data_consent` table
11. Extend `safety_incidents` table with new fields
12. Create `feedback` table

**Week 4:**
13. Implement alerting thresholds
14. Set up automated data quality reports
15. Test end-to-end data collection pipeline
16. Document data collection best practices for customers

---

**Document Status:** ✅ COMPLETE - Ready for implementation

**Next Steps:**
1. Review with engineering team
2. Implement database migrations
3. Update API validation layer
4. Deploy monitoring dashboard
5. Test with synthetic data
6. Gradual rollout to production

**Questions or clarifications:** Contact architecture team
