"""Validation utility functions for VLA Inference API.

This module provides helper functions for validating action vectors,
workspace bounds, and normalizing instructions.
"""

import hashlib
import re
import math
from typing import List, Tuple, Optional

from ..models.contracts.robot_types import RobotType, ROBOT_SPECS, get_robot_spec


def validate_action_vector_bounds(
    action: List[float],
    robot_type: RobotType
) -> Tuple[bool, Optional[str]]:
    """Validate action vector against robot-specific joint limits.

    Args:
        action: 7-DoF action vector
        robot_type: Robot type to validate against

    Returns:
        (is_valid, error_message)

    Example:
        >>> is_valid, error = validate_action_vector_bounds(
        ...     [0.1, -0.2, 0.05, 0.3, -0.1, 0.15, 0.0],
        ...     RobotType.FRANKA_PANDA
        ... )
        >>> assert is_valid
    """
    spec = get_robot_spec(robot_type)
    if spec is None:
        return True, None  # No spec available, skip validation

    joint_limits = spec['joint_limits']
    dof = spec['dof']

    # Check if action vector has correct dimensions
    if len(action) != 7:
        return False, f"action vector must have exactly 7 dimensions, got {len(action)}"

    # Check for non-finite values
    non_finite = [i for i, x in enumerate(action) if not math.isfinite(x)]
    if non_finite:
        return False, f"action vector contains non-finite values at indices {non_finite}"

    # For 6-DoF robots, extra dimensions should be zero or very small
    if len(action) > dof:
        extra_dims = action[dof:]
        if any(abs(x) > 0.001 for x in extra_dims):
            return False, (
                f"Robot {robot_type.value} has {dof} DoF, but action vector has "
                f"non-zero values in extra dimensions: {extra_dims}"
            )

    # Check joint limits
    violations = []
    for i, (action_val, (min_val, max_val)) in enumerate(zip(action[:dof], joint_limits)):
        if not (min_val <= action_val <= max_val):
            violations.append({
                'joint': i,
                'value': action_val,
                'limits': (min_val, max_val),
            })

    if violations:
        return False, (
            f"action vector violates joint limits for {robot_type.value}: {violations}"
        )

    return True, None


def validate_workspace_bounds(bounds: dict) -> Tuple[bool, Optional[str]]:
    """Validate workspace bounds structure and values.

    Args:
        bounds: Dictionary with x, y, z bounds

    Returns:
        (is_valid, error_message)

    Example:
        >>> bounds = {
        ...     "x": {"min": -0.8, "max": 0.8},
        ...     "y": {"min": -0.8, "max": 0.8},
        ...     "z": {"min": 0.0, "max": 1.2}
        ... }
        >>> is_valid, error = validate_workspace_bounds(bounds)
        >>> assert is_valid
    """
    required_axes = ['x', 'y', 'z']

    # Check all axes are present
    for axis in required_axes:
        if axis not in bounds:
            return False, f"missing required axis: {axis}"

        axis_bounds = bounds[axis]

        # Check min/max keys
        if 'min' not in axis_bounds or 'max' not in axis_bounds:
            return False, f"{axis} bounds must have 'min' and 'max' keys"

        min_val = axis_bounds['min']
        max_val = axis_bounds['max']

        # Check types
        if not isinstance(min_val, (int, float)) or not isinstance(max_val, (int, float)):
            return False, f"{axis} min/max must be numbers"

        # Check finite
        if not (math.isfinite(min_val) and math.isfinite(max_val)):
            return False, f"{axis} min/max must be finite numbers"

        # Check ordering
        if min_val >= max_val:
            return False, f"{axis} min ({min_val}) must be less than max ({max_val})"

        # Check reasonable bounds (most robots work within ±5m)
        if not (-5.0 <= min_val <= 5.0):
            return False, f"{axis} min ({min_val}) outside reasonable range [-5, 5] meters"
        if not (-5.0 <= max_val <= 5.0):
            return False, f"{axis} max ({max_val}) outside reasonable range [-5, 5] meters"

    return True, None


def normalize_instruction(text: str) -> str:
    """Normalize instruction for consistent hashing and deduplication.

    Steps:
    1. Lowercase
    2. Strip leading/trailing whitespace
    3. Remove punctuation (keep apostrophes)
    4. Collapse multiple spaces to single space

    Args:
        text: Raw instruction text

    Returns:
        Normalized instruction string

    Example:
        >>> normalize_instruction("Pick up the red cube.")
        'pick up the red cube'
        >>> normalize_instruction("Pick  up   the red cube!")
        'pick up the red cube'
    """
    # Lowercase
    normalized = text.lower()

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

    Example:
        >>> hash1 = hash_instruction("Pick up the red cube.")
        >>> hash2 = hash_instruction("pick up the red cube")
        >>> assert hash1 == hash2
    """
    normalized = normalize_instruction(instruction)
    hash_obj = hashlib.sha256(normalized.encode('utf-8'))
    return hash_obj.hexdigest()


def compute_action_magnitude(action_vector: List[float]) -> float:
    """Compute L2 norm (magnitude) of action vector.

    Args:
        action_vector: 7-DoF action vector

    Returns:
        L2 norm of the vector

    Example:
        >>> action = [0.1, -0.2, 0.05, 0.3, -0.1, 0.15, 0.0]
        >>> magnitude = compute_action_magnitude(action)
        >>> assert 0.4 < magnitude < 0.5
    """
    return math.sqrt(sum(x**2 for x in action_vector))


def validate_image_dimensions(height: int, width: int, channels: int) -> Tuple[bool, Optional[str]]:
    """Validate image dimensions for safety and memory constraints.

    Args:
        height: Image height in pixels
        width: Image width in pixels
        channels: Number of channels (should be 3 for RGB)

    Returns:
        (is_valid, error_message)

    Example:
        >>> is_valid, error = validate_image_dimensions(480, 640, 3)
        >>> assert is_valid
    """
    # Reasonable image size bounds
    if not (64 <= height <= 2048):
        return False, f"image height must be 64-2048 pixels, got {height}"

    if not (64 <= width <= 2048):
        return False, f"image width must be 64-2048 pixels, got {width}"

    if channels != 3:
        return False, f"image channels must be 3 (RGB), got {channels}"

    # Prevent memory attacks: max 10M pixels
    total_pixels = height * width
    if total_pixels > 10_000_000:
        return False, (
            f"image too large: {total_pixels:,} pixels (max 10M). "
            f"Dimensions: {height}x{width}"
        )

    return True, None
