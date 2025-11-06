"""Analytics data contracts.

Pydantic models for robot performance metrics, instruction analytics,
and context metadata.
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
from enum import Enum
import math
import re

from .robot_types import RobotType
from .inference_log import ModelName, InstructionCategory


# === ROBOT PERFORMANCE METRICS ===

class ActionDimensionStats(BaseModel):
    """Statistics for a single action dimension."""
    mean: float = Field(..., description="Mean value")
    std: float = Field(..., description="Standard deviation")
    min: float = Field(..., description="Minimum value")
    max: float = Field(..., description="Maximum value")

    @validator('*', pre=True, always=True)
    def validate_finite(cls, v):
        """Ensure all stats are finite numbers."""
        if not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"All stats must be finite numbers, got {v}")
        return v


class ActionStatistics(BaseModel):
    """Complete action statistics structure for JSONB."""
    dof_0: ActionDimensionStats
    dof_1: ActionDimensionStats
    dof_2: ActionDimensionStats
    dof_3: ActionDimensionStats
    dof_4: ActionDimensionStats
    dof_5: ActionDimensionStats
    dof_6: ActionDimensionStats
    magnitude: ActionDimensionStats


class FailurePatterns(BaseModel):
    """Failure pattern analysis structure for JSONB."""
    timeout_rate: float = Field(..., ge=0.0, le=1.0, description="Proportion of timeouts")
    safety_rejection_rate: float = Field(..., ge=0.0, le=1.0, description="Proportion of safety rejections")
    error_types: dict[str, int] = Field(..., description="Error type counts")
    common_error_messages: List[str] = Field(..., max_items=10, description="Top 10 error messages")


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


# === INSTRUCTION ANALYTICS ===

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


# === CONTEXT METADATA ===

class LightingConditions(str, Enum):
    """Lighting condition classifications."""
    BRIGHT = "bright"
    NORMAL = "normal"
    DIM = "dim"
    DARK = "dark"
    UNKNOWN = "unknown"


class EnvironmentType(str, Enum):
    """Deployment environment types."""
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
