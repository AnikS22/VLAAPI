"""Robot type specifications and validation.

This module defines the canonical robot types, their specifications,
and validation functions for the VLA Inference API.
"""

from enum import Enum
from typing import TypedDict, List, Tuple, Optional


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
}


def validate_robot_type(robot_type: str) -> bool:
    """Validate if robot type is in canonical enum.

    Args:
        robot_type: Robot type string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        RobotType(robot_type)
        return True
    except ValueError:
        return False


def get_robot_spec(robot_type: RobotType) -> Optional[RobotSpec]:
    """Get specifications for a robot type.

    Args:
        robot_type: Robot type enum value

    Returns:
        Robot specification dict if available, None otherwise
    """
    return ROBOT_SPECS.get(robot_type)


def validate_action_vector_bounds(
    action_vector: List[float],
    robot_type: RobotType
) -> tuple[bool, Optional[str]]:
    """Validate action vector against robot-specific joint limits.

    Args:
        action_vector: 7-DoF action vector
        robot_type: Robot type to validate against

    Returns:
        (is_valid, error_message)
    """
    if robot_type not in ROBOT_SPECS:
        return True, None  # No spec available, skip validation

    spec = ROBOT_SPECS[robot_type]
    joint_limits = spec['joint_limits']
    dof = spec['dof']

    # For 6-DoF robots, check first 6 values
    # For 7-DoF robots, check all 7 values
    if len(action_vector) > dof:
        # Extra dimensions should be zero or very small
        extra_dims = action_vector[dof:]
        if any(abs(x) > 0.001 for x in extra_dims):
            return False, (
                f"Robot {robot_type.value} has {dof} DoF, but action_vector has "
                f"non-zero values in extra dimensions: {extra_dims}"
            )

    # Check joint limits
    violations = []
    for i, (action_val, (min_val, max_val)) in enumerate(zip(action_vector[:dof], joint_limits)):
        if not (min_val <= action_val <= max_val):
            violations.append({
                'joint': i,
                'value': action_val,
                'limits': (min_val, max_val),
            })

    if violations:
        return False, (
            f"action_vector violates joint limits for {robot_type.value}: {violations}"
        )

    return True, None
