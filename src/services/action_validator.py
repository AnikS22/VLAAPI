"""Rule-based safety validation for VLA actions."""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.core.config import settings
from src.core.constants import (
    SafetyAction,
    SafetySeverity,
    SafetyViolationType,
    get_robot_config,
)

logger = logging.getLogger(__name__)


class SafetyViolation:
    """Represents a safety violation."""

    def __init__(
        self,
        violation_type: SafetyViolationType,
        severity: SafetySeverity,
        details: Dict,
        suggested_action: SafetyAction,
    ):
        """Initialize safety violation.

        Args:
            violation_type: Type of violation
            severity: Severity level
            details: Violation details
            suggested_action: Suggested action to take
        """
        self.violation_type = violation_type
        self.severity = severity
        self.details = details
        self.suggested_action = suggested_action


class ActionValidator:
    """Rule-based safety validator for robot actions."""

    def __init__(self):
        """Initialize action validator."""
        self.enable_workspace_check = settings.safety_enable_workspace_check
        self.enable_velocity_check = settings.safety_enable_velocity_check
        self.enable_collision_check = settings.safety_enable_collision_check

    def validate_action(
        self,
        action: List[float],
        robot_type: str = "franka_panda",
        robot_config: Optional[Dict] = None,
        current_pose: Optional[List[float]] = None,
    ) -> Tuple[bool, float, List[SafetyViolation]]:
        """Validate action against safety rules.

        Args:
            action: Action vector to validate
            robot_type: Robot type
            robot_config: Optional robot configuration
            current_pose: Current robot pose (for workspace checking)

        Returns:
            Tuple of (is_safe, safety_score, violations)
        """
        violations: List[SafetyViolation] = []
        checks_passed = 0
        total_checks = 0

        # Get robot configuration
        if robot_config:
            workspace_bounds = robot_config.get("workspace_bounds")
            velocity_limits = robot_config.get("velocity_limits")
        else:
            config = get_robot_config(robot_type)
            workspace_bounds = config["workspace_bounds"]
            velocity_limits = config["velocity_limits"]

        # 1. Workspace boundary check
        if self.enable_workspace_check and current_pose is not None:
            total_checks += 1
            violation = self._check_workspace(
                action, current_pose, workspace_bounds
            )
            if violation:
                violations.append(violation)
            else:
                checks_passed += 1

        # 2. Velocity limit check
        if self.enable_velocity_check:
            total_checks += 1
            violation = self._check_velocity_limits(action, velocity_limits)
            if violation:
                violations.append(violation)
            else:
                checks_passed += 1

        # 3. Collision risk check (simplified - distance-based)
        if self.enable_collision_check:
            total_checks += 1
            violation = self._check_collision_risk(action, robot_config)
            if violation:
                violations.append(violation)
            else:
                checks_passed += 1

        # Calculate safety score
        if total_checks == 0:
            safety_score = 1.0  # All checks disabled
        else:
            safety_score = checks_passed / total_checks

        # Determine if safe
        is_safe = len(violations) == 0

        return is_safe, safety_score, violations

    def _check_workspace(
        self,
        action: List[float],
        current_pose: List[float],
        workspace_bounds: List[List[float]],
    ) -> Optional[SafetyViolation]:
        """Check if action would move end-effector outside workspace.

        Args:
            action: Delta action (assumed to be position deltas)
            current_pose: Current end-effector pose [x, y, z, ...]
            workspace_bounds: [[x_min, y_min, z_min], [x_max, y_max, z_max]]

        Returns:
            SafetyViolation if violated, None otherwise
        """
        # Predict next position (current + delta)
        next_position = np.array(current_pose[:3]) + np.array(action[:3])

        # Check bounds
        bounds_min = np.array(workspace_bounds[0])
        bounds_max = np.array(workspace_bounds[1])

        # Add safety margin
        margin = settings.safety_workspace_z_min  # Reuse as margin
        bounds_min += margin
        bounds_max -= margin

        violations = []
        for i, (pos, min_val, max_val) in enumerate(
            zip(next_position, bounds_min, bounds_max)
        ):
            if pos < min_val or pos > max_val:
                violations.append(
                    {
                        "axis": ["x", "y", "z"][i],
                        "position": float(pos),
                        "min_bound": float(min_val),
                        "max_bound": float(max_val),
                    }
                )

        if violations:
            # Determine severity based on distance outside bounds
            max_violation_dist = max(
                max(0, v["position"] - v["max_bound"])
                + max(0, v["min_bound"] - v["position"])
                for v in violations
            )

            if max_violation_dist > 0.2:  # 20cm
                severity = SafetySeverity.CRITICAL
            elif max_violation_dist > 0.1:  # 10cm
                severity = SafetySeverity.HIGH
            elif max_violation_dist > 0.05:  # 5cm
                severity = SafetySeverity.MEDIUM
            else:
                severity = SafetySeverity.LOW

            return SafetyViolation(
                violation_type=SafetyViolationType.WORKSPACE,
                severity=severity,
                details={
                    "violations": violations,
                    "next_position": next_position.tolist(),
                    "workspace_bounds": workspace_bounds,
                },
                suggested_action=SafetyAction.CLAMPED,
            )

        return None

    def _check_velocity_limits(
        self,
        action: List[float],
        velocity_limits: List[float],
    ) -> Optional[SafetyViolation]:
        """Check if action exceeds velocity limits.

        Args:
            action: Action vector (velocities or position deltas)
            velocity_limits: Maximum velocity for each DoF

        Returns:
            SafetyViolation if violated, None otherwise
        """
        action_array = np.abs(np.array(action))
        limits_array = np.array(velocity_limits)

        violations = []
        for i, (vel, limit) in enumerate(zip(action_array, limits_array)):
            if vel > limit:
                violations.append(
                    {
                        "dof": i,
                        "velocity": float(vel),
                        "limit": float(limit),
                        "excess_percent": float((vel - limit) / limit * 100),
                    }
                )

        if violations:
            # Determine severity based on excess
            max_excess_percent = max(v["excess_percent"] for v in violations)

            if max_excess_percent > 100:  # >2x limit
                severity = SafetySeverity.CRITICAL
            elif max_excess_percent > 50:  # >1.5x limit
                severity = SafetySeverity.HIGH
            elif max_excess_percent > 20:  # >1.2x limit
                severity = SafetySeverity.MEDIUM
            else:
                severity = SafetySeverity.LOW

            return SafetyViolation(
                violation_type=SafetyViolationType.VELOCITY,
                severity=severity,
                details={
                    "violations": violations,
                    "action": action,
                    "limits": velocity_limits,
                },
                suggested_action=SafetyAction.CLAMPED,
            )

        return None

    def _check_collision_risk(
        self,
        action: List[float],
        robot_config: Optional[Dict],
    ) -> Optional[SafetyViolation]:
        """Check for collision risk (simplified placeholder).

        Args:
            action: Action vector
            robot_config: Robot configuration (may include obstacle positions)

        Returns:
            SafetyViolation if collision risk detected, None otherwise

        Note:
            This is a simplified check. Real implementation would use:
            - Robot kinematics
            - Obstacle detection from sensors
            - Swept volume collision checking
        """
        # Placeholder: check if action magnitude is suspiciously large
        # (real implementation would use proper collision detection)

        action_magnitude = np.linalg.norm(action[:3])  # Position component

        # If action is very large, flag as potential collision risk
        if action_magnitude > 0.5:  # 50cm movement in one step
            return SafetyViolation(
                violation_type=SafetyViolationType.COLLISION,
                severity=SafetySeverity.MEDIUM,
                details={
                    "action_magnitude": float(action_magnitude),
                    "threshold": 0.5,
                    "reason": "Large action magnitude may indicate collision risk",
                },
                suggested_action=SafetyAction.LOGGED,
            )

        return None

    def clamp_action_to_safe(
        self,
        action: List[float],
        violations: List[SafetyViolation],
        robot_type: str = "franka_panda",
        robot_config: Optional[Dict] = None,
    ) -> List[float]:
        """Clamp action to safe bounds based on violations.

        Args:
            action: Original action
            violations: List of safety violations
            robot_type: Robot type
            robot_config: Optional robot configuration

        Returns:
            Clamped safe action
        """
        safe_action = np.array(action).copy()

        # Get velocity limits
        if robot_config and "velocity_limits" in robot_config:
            velocity_limits = np.array(robot_config["velocity_limits"])
        else:
            config = get_robot_config(robot_type)
            velocity_limits = np.array(config["velocity_limits"])

        # Clamp velocity violations
        for violation in violations:
            if violation.violation_type == SafetyViolationType.VELOCITY:
                # Clamp to limits
                safe_action = np.clip(safe_action, -velocity_limits, velocity_limits)

        # For workspace violations, scale down action
        for violation in violations:
            if violation.violation_type == SafetyViolationType.WORKSPACE:
                # Scale down by 50%
                safe_action[:3] *= 0.5

        return safe_action.tolist()
