"""Pluggable safety monitoring system for VLA actions.

This module provides a flexible interface for integrating safety and alignment
research. The SafetyMonitor class can be extended with custom alignment checks.
"""

import logging
from typing import Dict, List, Optional, Tuple

from src.core.config import settings
from src.core.constants import SafetySeverity, SafetyViolationType
from src.services.action_validator import ActionValidator, SafetyViolation

logger = logging.getLogger(__name__)


class AlignmentCheck:
    """Base class for custom alignment checks.

    Extend this class to implement your own safety/alignment measures.

    Example:
        ```python
        class MyAlignmentCheck(AlignmentCheck):
            def check(self, action, context):
                # Your custom alignment logic
                if is_unsafe(action):
                    return False, 0.5, "Action violates alignment constraint"
                return True, 1.0, "Action is aligned"
        ```
    """

    def __init__(self, name: str):
        """Initialize alignment check.

        Args:
            name: Name of the alignment check
        """
        self.name = name

    def check(
        self,
        action: List[float],
        context: Dict,
    ) -> Tuple[bool, float, str]:
        """Perform alignment check on action.

        Args:
            action: Action vector to check
            context: Additional context (image, instruction, robot state, etc.)

        Returns:
            Tuple of (is_aligned, confidence_score, explanation)

        Note:
            Implement this method in your subclass.
        """
        raise NotImplementedError("Subclasses must implement check()")


class SafeVLAAlignmentCheck(AlignmentCheck):
    """Placeholder for SafeVLA alignment checking.

    This is where you would integrate your alignment research.
    """

    def __init__(self):
        """Initialize SafeVLA alignment check."""
        super().__init__("SafeVLA")
        # TODO: Load your trained alignment model here
        # self.model = load_your_model()

    def check(
        self,
        action: List[float],
        context: Dict,
    ) -> Tuple[bool, float, str]:
        """Check action alignment using SafeVLA methodology.

        Args:
            action: Action vector
            context: Context including image, instruction, etc.

        Returns:
            Tuple of (is_aligned, confidence_score, explanation)
        """
        # TODO: Implement your alignment checking logic
        # This is a placeholder implementation

        # Example: Use your trained classifier to predict safety
        # is_safe, confidence = self.model.predict(action, context)

        # Placeholder: Simple heuristic
        import numpy as np

        action_magnitude = np.linalg.norm(action[:3])

        if action_magnitude > 0.8:
            # Large actions might be risky
            return False, 0.6, "Large action magnitude indicates potential risk"

        # Action seems reasonable
        return True, 0.9, "Action within expected bounds"


class SafetyMonitor:
    """Main safety monitoring system with pluggable alignment checks.

    This class combines rule-based safety validation with custom alignment checks.
    """

    def __init__(self):
        """Initialize safety monitor."""
        self.rule_validator = ActionValidator()
        self.alignment_checks: List[AlignmentCheck] = []

        # Add default alignment check (placeholder for your research)
        if settings.safety_classifier_enabled:
            self.add_alignment_check(SafeVLAAlignmentCheck())

        logger.info(
            f"Safety monitor initialized with {len(self.alignment_checks)} alignment checks"
        )

    def add_alignment_check(self, check: AlignmentCheck) -> None:
        """Add custom alignment check to the monitor.

        Args:
            check: Alignment check instance

        Example:
            ```python
            safety_monitor = SafetyMonitor()
            safety_monitor.add_alignment_check(MyCustomAlignmentCheck())
            ```
        """
        self.alignment_checks.append(check)
        logger.info(f"Added alignment check: {check.name}")

    def remove_alignment_check(self, name: str) -> None:
        """Remove alignment check by name.

        Args:
            name: Name of alignment check to remove
        """
        self.alignment_checks = [c for c in self.alignment_checks if c.name != name]
        logger.info(f"Removed alignment check: {name}")

    def evaluate_action(
        self,
        action: List[float],
        robot_type: str = "franka_panda",
        robot_config: Optional[Dict] = None,
        current_pose: Optional[List[float]] = None,
        context: Optional[Dict] = None,
    ) -> Dict:
        """Evaluate action safety using all checks.

        Args:
            action: Action vector to evaluate
            robot_type: Robot type
            robot_config: Optional robot configuration
            current_pose: Current robot pose
            context: Additional context for alignment checks

        Returns:
            Dictionary with evaluation results
        """
        context = context or {}

        # 1. Rule-based safety validation
        is_safe_rules, rule_score, violations = self.rule_validator.validate_action(
            action, robot_type, robot_config, current_pose
        )

        # 2. Alignment checks
        alignment_results = []
        alignment_scores = []

        for check in self.alignment_checks:
            try:
                is_aligned, confidence, explanation = check.check(action, context)
                alignment_results.append(
                    {
                        "check_name": check.name,
                        "is_aligned": is_aligned,
                        "confidence": confidence,
                        "explanation": explanation,
                    }
                )
                alignment_scores.append(confidence if is_aligned else 0.0)
            except Exception as e:
                logger.error(f"Alignment check {check.name} failed: {e}", exc_info=True)
                alignment_results.append(
                    {
                        "check_name": check.name,
                        "is_aligned": False,
                        "confidence": 0.0,
                        "explanation": f"Check failed: {e}",
                    }
                )
                alignment_scores.append(0.0)

        # Calculate overall alignment score
        if alignment_scores:
            avg_alignment_score = sum(alignment_scores) / len(alignment_scores)
        else:
            avg_alignment_score = 1.0  # No alignment checks, assume safe

        # 3. Combine scores
        # Weight: 60% rule-based, 40% alignment
        overall_score = 0.6 * rule_score + 0.4 * avg_alignment_score

        # Determine if action is safe overall
        is_safe_overall = (
            is_safe_rules
            and overall_score >= settings.safety_default_threshold
        )

        # Prepare checks passed list
        checks_passed = []
        if is_safe_rules:
            if self.rule_validator.enable_workspace_check:
                checks_passed.append("workspace")
            if self.rule_validator.enable_velocity_check:
                checks_passed.append("velocity")
            if self.rule_validator.enable_collision_check:
                checks_passed.append("collision")

        if all(r["is_aligned"] for r in alignment_results):
            checks_passed.append("alignment")

        # Prepare flags
        flags = {
            "workspace_violation": any(
                v.violation_type == SafetyViolationType.WORKSPACE
                for v in violations
            ),
            "velocity_violation": any(
                v.violation_type == SafetyViolationType.VELOCITY for v in violations
            ),
            "collision_risk": any(
                v.violation_type == SafetyViolationType.COLLISION
                for v in violations
            ),
            "alignment_violation": not all(r["is_aligned"] for r in alignment_results),
        }

        # Determine if action should be modified
        modifications_applied = False
        modified_action = action

        if not is_safe_overall and any(flags.values()):
            # Clamp action to safe bounds
            modified_action = self.rule_validator.clamp_action_to_safe(
                action, violations, robot_type, robot_config
            )
            modifications_applied = True

        return {
            "is_safe": is_safe_overall,
            "overall_score": overall_score,
            "checks_passed": checks_passed,
            "flags": flags,
            "rule_based": {
                "score": rule_score,
                "violations": [
                    {
                        "type": v.violation_type.value,
                        "severity": v.severity.value,
                        "details": v.details,
                    }
                    for v in violations
                ],
            },
            "alignment": {
                "score": avg_alignment_score,
                "results": alignment_results,
            },
            "modifications_applied": modifications_applied,
            "original_action": action,
            "safe_action": modified_action,
        }


# Global safety monitor instance
safety_monitor = SafetyMonitor()
