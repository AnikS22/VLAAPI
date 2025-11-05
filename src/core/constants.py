"""Constants and action space definitions for VLA models."""

from enum import Enum
from typing import Dict, List, Tuple

# =============================================================================
# VLA MODEL CONSTANTS
# =============================================================================

# Supported VLA models
SUPPORTED_VLA_MODELS = {
    "openvla-7b": {
        "name": "OpenVLA 7B",
        "model_id": "openvla/openvla-7b",
        "description": "Open-source VLA trained on 970K robot episodes (Open X-Embodiment)",
        "action_space_dim": 7,
        "action_space_type": "end_effector_delta",
        "image_size": (224, 224),
        "supports_batch": True,
        "avg_latency_ms": 120,
        "memory_gb": 16,
    },
    "pi0": {
        "name": "π₀ (Physical Intelligence)",
        "model_id": "physical-intelligence/pi0",
        "description": "Flow-based VLA with 50Hz real-time capability",
        "action_space_dim": 7,  # Can vary based on robot
        "action_space_type": "trajectory_chunk",
        "image_size": (224, 224),  # May vary
        "supports_batch": True,
        "avg_latency_ms": 85,
        "memory_gb": 12,
    },
    "pi0-fast": {
        "name": "π₀-FAST",
        "model_id": "physical-intelligence/pi0-fast",
        "description": "Autoregressive π₀ variant with FAST tokenizer",
        "action_space_dim": 7,
        "action_space_type": "discrete_tokens",
        "image_size": (224, 224),
        "supports_batch": True,
        "avg_latency_ms": 95,
        "memory_gb": 12,
    },
}

# Default action space dimension (7-DoF end-effector control)
ACTION_SPACE_DIM = 7

# Action space component names
ACTION_SPACE_COMPONENTS = [
    "delta_x",
    "delta_y",
    "delta_z",
    "delta_roll",
    "delta_pitch",
    "delta_yaw",
    "gripper",
]

# Action space units
ACTION_SPACE_UNITS = [
    "m",  # meters
    "m",
    "m",
    "rad",  # radians
    "rad",
    "rad",
    "binary",  # 0 = closed, 1 = open
]

# =============================================================================
# ROBOT CONFIGURATIONS
# =============================================================================

class RobotType(str, Enum):
    """Supported robot types."""

    FRANKA_PANDA = "franka_panda"
    UR5 = "ur5"
    UR10 = "ur10"
    XARM7 = "xarm7"
    CUSTOM = "custom"


# Pre-defined robot configurations
SUPPORTED_ROBOT_TYPES: Dict[str, Dict] = {
    "franka_panda": {
        "name": "Franka Emika Panda",
        "dof": 7,
        "workspace_bounds": [
            [-0.6, -0.6, 0.0],  # [x_min, y_min, z_min]
            [0.6, 0.6, 0.8],    # [x_max, y_max, z_max]
        ],
        "velocity_limits": [0.5, 0.5, 0.5, 1.0, 1.0, 1.0, 1.0],  # m/s or rad/s
        "acceleration_limits": [2.0, 2.0, 2.0, 3.0, 3.0, 3.0, 2.0],  # m/s^2 or rad/s^2
        "force_limits": [50.0, 50.0, 50.0, 20.0, 20.0, 20.0, 50.0],  # N or Nm
        "normalization_stats": {
            "mean": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5],
            "std": [0.1, 0.1, 0.1, 0.5, 0.5, 0.5, 0.25],
        },
    },
    "ur5": {
        "name": "Universal Robots UR5",
        "dof": 6,
        "workspace_bounds": [
            [-0.85, -0.85, 0.0],
            [0.85, 0.85, 1.0],
        ],
        "velocity_limits": [0.6, 0.6, 0.6, 1.5, 1.5, 1.5, 1.0],
        "acceleration_limits": [2.5, 2.5, 2.5, 4.0, 4.0, 4.0, 2.0],
        "force_limits": [100.0, 100.0, 100.0, 30.0, 30.0, 30.0, 50.0],
        "normalization_stats": {
            "mean": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5],
            "std": [0.12, 0.12, 0.12, 0.6, 0.6, 0.6, 0.25],
        },
    },
    "xarm7": {
        "name": "UFACTORY xArm7",
        "dof": 7,
        "workspace_bounds": [
            [-0.7, -0.7, 0.0],
            [0.7, 0.7, 0.9],
        ],
        "velocity_limits": [0.5, 0.5, 0.5, 1.2, 1.2, 1.2, 1.0],
        "acceleration_limits": [2.0, 2.0, 2.0, 3.5, 3.5, 3.5, 2.0],
        "force_limits": [80.0, 80.0, 80.0, 25.0, 25.0, 25.0, 50.0],
        "normalization_stats": {
            "mean": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5],
            "std": [0.11, 0.11, 0.11, 0.55, 0.55, 0.55, 0.25],
        },
    },
}

# =============================================================================
# SAFETY CONSTANTS
# =============================================================================

class SafetyViolationType(str, Enum):
    """Types of safety violations."""

    WORKSPACE = "workspace"
    VELOCITY = "velocity"
    ACCELERATION = "acceleration"
    COLLISION = "collision"
    FORCE = "force"
    CLASSIFIER = "classifier"
    UNKNOWN = "unknown"


class SafetySeverity(str, Enum):
    """Safety incident severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SafetyAction(str, Enum):
    """Actions taken for safety violations."""

    LOGGED = "logged"
    CLAMPED = "clamped"
    REJECTED = "rejected"
    EMERGENCY_STOP = "emergency_stop"


# Safety check types
SAFETY_CHECK_TYPES = [
    "workspace",
    "velocity",
    "acceleration",
    "collision",
    "classifier",
]

# Default safety thresholds (can be overridden by config)
DEFAULT_SAFETY_THRESHOLDS = {
    "overall_min_score": 0.8,
    "classifier_min_score": 0.85,
    "collision_min_clearance_m": 0.05,
    "workspace_margin_m": 0.02,
}

# =============================================================================
# API CONSTANTS
# =============================================================================

class CustomerTier(str, Enum):
    """Customer subscription tiers."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class APIKeyScope(str, Enum):
    """API key permission scopes."""

    INFERENCE = "inference"
    ADMIN = "admin"
    READONLY = "readonly"


class InferenceStatus(str, Enum):
    """Inference request status."""

    SUCCESS = "success"
    ERROR = "error"
    SAFETY_REJECTED = "safety_rejected"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"


# API Version
API_VERSION = "v1"
API_PREFIX = f"/v1"

# Request/Response Limits
MAX_IMAGE_SIZE_MB = 10
MAX_IMAGE_DIMENSION = 2048
MIN_IMAGE_DIMENSION = 64

# OpenAPI Tags
API_TAGS = [
    {
        "name": "inference",
        "description": "VLA model inference endpoints",
    },
    {
        "name": "models",
        "description": "Model information and management",
    },
    {
        "name": "safety",
        "description": "Safety evaluation and monitoring",
    },
    {
        "name": "admin",
        "description": "Administrative endpoints (requires admin scope)",
    },
    {
        "name": "monitoring",
        "description": "Health checks and metrics",
    },
]

# =============================================================================
# HTTP STATUS CODES
# =============================================================================

# Success codes
HTTP_200_OK = 200
HTTP_201_CREATED = 201

# Client error codes
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404
HTTP_422_UNPROCESSABLE_ENTITY = 422
HTTP_429_TOO_MANY_REQUESTS = 429

# Server error codes
HTTP_500_INTERNAL_SERVER_ERROR = 500
HTTP_503_SERVICE_UNAVAILABLE = 503

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_robot_config(robot_type: str) -> Dict:
    """Get robot configuration by type.

    Args:
        robot_type: Robot type identifier

    Returns:
        Robot configuration dictionary

    Raises:
        ValueError: If robot type not found
    """
    if robot_type not in SUPPORTED_ROBOT_TYPES:
        raise ValueError(
            f"Unsupported robot type: {robot_type}. "
            f"Supported types: {list(SUPPORTED_ROBOT_TYPES.keys())}"
        )
    return SUPPORTED_ROBOT_TYPES[robot_type]


def get_model_config(model_id: str) -> Dict:
    """Get VLA model configuration.

    Args:
        model_id: Model identifier

    Returns:
        Model configuration dictionary

    Raises:
        ValueError: If model ID not found
    """
    if model_id not in SUPPORTED_VLA_MODELS:
        raise ValueError(
            f"Unsupported model: {model_id}. "
            f"Supported models: {list(SUPPORTED_VLA_MODELS.keys())}"
        )
    return SUPPORTED_VLA_MODELS[model_id]


def get_tier_rate_limits(tier: CustomerTier) -> Tuple[int, int, int]:
    """Get rate limits for customer tier.

    Args:
        tier: Customer tier

    Returns:
        Tuple of (rpm, rpd, monthly_quota)

    Note:
        This returns default values. Actual limits should be fetched
        from the database for each customer.
    """
    from src.core.config import settings

    if tier == CustomerTier.FREE:
        return (
            settings.rate_limit_free_rpm,
            settings.rate_limit_free_rpd,
            settings.rate_limit_free_monthly,
        )
    elif tier == CustomerTier.PRO:
        return (
            settings.rate_limit_pro_rpm,
            settings.rate_limit_pro_rpd,
            settings.rate_limit_pro_monthly,
        )
    elif tier == CustomerTier.ENTERPRISE:
        return (
            settings.rate_limit_enterprise_rpm,
            settings.rate_limit_enterprise_rpd,
            settings.rate_limit_enterprise_monthly or 999999999,  # Unlimited
        )
    else:
        raise ValueError(f"Unknown tier: {tier}")
