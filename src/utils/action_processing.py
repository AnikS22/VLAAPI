"""Action processing utilities for VLA inference."""

from typing import Dict, List, Optional

import numpy as np

from src.core.constants import get_robot_config


def unnormalize_action(
    normalized_action: List[float],
    robot_type: str = "franka_panda",
    custom_stats: Optional[Dict[str, List[float]]] = None,
) -> List[float]:
    """Un-normalize action vector using robot-specific statistics.

    VLA models typically output normalized actions (mean=0, std=1).
    This function converts them back to real-world units.

    Args:
        normalized_action: Normalized action vector
        robot_type: Robot type (for default normalization stats)
        custom_stats: Custom normalization stats {mean: [...], std: [...]}

    Returns:
        Un-normalized action vector
    """
    action_array = np.array(normalized_action)

    # Get normalization statistics
    if custom_stats:
        mean = np.array(custom_stats["mean"])
        std = np.array(custom_stats["std"])
    else:
        robot_config = get_robot_config(robot_type)
        mean = np.array(robot_config["normalization_stats"]["mean"])
        std = np.array(robot_config["normalization_stats"]["std"])

    # Un-normalize: action = normalized_action * std + mean
    unnormalized = action_array * std + mean

    return unnormalized.tolist()


def normalize_action(
    action: List[float],
    robot_type: str = "franka_panda",
    custom_stats: Optional[Dict[str, List[float]]] = None,
) -> List[float]:
    """Normalize action vector using robot-specific statistics.

    Args:
        action: Real-world action vector
        robot_type: Robot type (for default normalization stats)
        custom_stats: Custom normalization stats {mean: [...], std: [...]}

    Returns:
        Normalized action vector
    """
    action_array = np.array(action)

    # Get normalization statistics
    if custom_stats:
        mean = np.array(custom_stats["mean"])
        std = np.array(custom_stats["std"])
    else:
        robot_config = get_robot_config(robot_type)
        mean = np.array(robot_config["normalization_stats"]["mean"])
        std = np.array(robot_config["normalization_stats"]["std"])

    # Normalize: normalized_action = (action - mean) / std
    normalized = (action_array - mean) / std

    return normalized.tolist()


def clip_action_to_limits(
    action: List[float],
    robot_type: str = "franka_panda",
    custom_limits: Optional[Dict[str, List[float]]] = None,
) -> List[float]:
    """Clip action to robot velocity/acceleration limits.

    Args:
        action: Action vector
        robot_type: Robot type (for default limits)
        custom_limits: Custom limits {velocity_limits: [...], acceleration_limits: [...]}

    Returns:
        Clipped action vector
    """
    action_array = np.array(action)

    # Get velocity limits
    if custom_limits and "velocity_limits" in custom_limits:
        limits = np.array(custom_limits["velocity_limits"])
    else:
        robot_config = get_robot_config(robot_type)
        limits = np.array(robot_config["velocity_limits"])

    # Clip action to [-limit, +limit] for each component
    clipped = np.clip(action_array, -limits, limits)

    return clipped.tolist()
