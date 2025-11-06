"""Quality gates middleware for data validation and rejection.

This module implements hard rejection logic for invalid inference data
to ensure data quality for training datasets.
"""

import hashlib
import logging
from typing import Dict, List, Optional

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.redis_client import get_redis
from src.models.database import InferenceLog

logger = logging.getLogger(__name__)


class QualityGate:
    """Quality gate for validating inference data before storage."""

    def __init__(
        self,
        dedup_window_seconds: int = 300,
        min_safety_score: float = 0.7,
    ):
        """Initialize quality gate.

        Args:
            dedup_window_seconds: Time window for deduplication (seconds)
            min_safety_score: Minimum safety score threshold
        """
        self.dedup_window_seconds = dedup_window_seconds
        self.min_safety_score = min_safety_score

    async def validate_robot_type(self, robot_type: str) -> tuple[bool, Optional[str]]:
        """Validate robot type is not UNKNOWN.

        Args:
            robot_type: Robot type identifier

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not robot_type or robot_type.upper() == "UNKNOWN":
            return False, "Robot type cannot be UNKNOWN or empty"

        return True, None

    async def validate_action_bounds(
        self,
        action: List[float],
        robot_config: Optional[Dict] = None
    ) -> tuple[bool, Optional[str]]:
        """Validate action vector is within expected bounds.

        Args:
            action: Action vector
            robot_config: Optional robot configuration with limits

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not action or len(action) != 7:
            return False, "Action vector must have exactly 7 dimensions"

        # Check for NaN or Inf
        action_arr = np.array(action)
        if np.any(np.isnan(action_arr)) or np.any(np.isinf(action_arr)):
            return False, "Action vector contains NaN or Inf values"

        # Check bounds (-1 to 1 for normalized actions)
        if np.any(action_arr < -1.1) or np.any(action_arr > 1.1):
            return False, "Action vector values exceed expected bounds [-1, 1]"

        return True, None

    async def validate_safety_score(
        self,
        safety_score: float
    ) -> tuple[bool, Optional[str]]:
        """Validate safety score meets minimum threshold.

        Args:
            safety_score: Safety evaluation score (0-1)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if safety_score < self.min_safety_score:
            return (
                False,
                f"Safety score {safety_score:.2f} below minimum {self.min_safety_score:.2f}"
            )

        return True, None

    async def check_duplicate(
        self,
        instruction: str,
        image_hash: str,
        db: AsyncSession,
        redis=None
    ) -> tuple[bool, Optional[str]]:
        """Check if this inference is a duplicate within the time window.

        Args:
            instruction: Natural language instruction
            image_hash: Hash of the input image
            db: Database session
            redis: Redis client (optional, for caching)

        Returns:
            Tuple of (is_duplicate, error_message)
        """
        # Create composite hash
        composite_key = f"{instruction}:{image_hash}"
        composite_hash = hashlib.sha256(composite_key.encode()).hexdigest()

        # Check Redis cache first (fast path)
        if redis:
            cache_key = f"dedup:{composite_hash}"
            try:
                cached = await redis.get(cache_key)
                if cached:
                    return True, "Duplicate inference detected (cached)"

                # Cache this hash
                await redis.setex(cache_key, self.dedup_window_seconds, "1")
            except Exception as e:
                logger.warning(f"Redis deduplication check failed: {e}")

        # Fallback to database check
        try:
            from datetime import datetime, timedelta

            cutoff_time = datetime.utcnow() - timedelta(seconds=self.dedup_window_seconds)

            # Query for recent similar inferences
            query = select(InferenceLog).where(
                InferenceLog.instruction == instruction,
                InferenceLog.created_at >= cutoff_time
            ).limit(1)

            result = await db.execute(query)
            existing = result.scalar_one_or_none()

            if existing:
                return True, "Duplicate inference detected (database)"

        except Exception as e:
            logger.error(f"Database deduplication check failed: {e}")
            # Don't fail on dedup check errors

        return False, None

    async def validate_instruction(
        self,
        instruction: str
    ) -> tuple[bool, Optional[str]]:
        """Validate instruction text quality.

        Args:
            instruction: Natural language instruction

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not instruction or not instruction.strip():
            return False, "Instruction cannot be empty"

        # Check minimum length (at least 3 words)
        words = instruction.strip().split()
        if len(words) < 3:
            return False, "Instruction too short (minimum 3 words)"

        # Check maximum length
        if len(instruction) > 500:
            return False, "Instruction too long (maximum 500 characters)"

        return True, None

    async def validate_image_quality(
        self,
        image_shape: List[int],
        image_size_bytes: int
    ) -> tuple[bool, Optional[str]]:
        """Validate image quality metrics.

        Args:
            image_shape: Image shape [height, width, channels]
            image_size_bytes: Image file size in bytes

        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(image_shape) != 3:
            return False, "Invalid image shape"

        height, width, channels = image_shape

        # Check minimum resolution
        if height < 64 or width < 64:
            return False, "Image resolution too low (minimum 64x64)"

        # Check channels
        if channels not in [1, 3, 4]:
            return False, f"Invalid number of channels: {channels}"

        # Check file size (prevent extremely small images)
        if image_size_bytes < 1024:  # 1 KB
            return False, "Image file too small, likely corrupt"

        return True, None

    async def validate_all(
        self,
        robot_type: str,
        action: List[float],
        safety_score: float,
        instruction: str,
        image_hash: str,
        image_shape: List[int],
        image_size_bytes: int,
        db: AsyncSession,
        redis=None,
        robot_config: Optional[Dict] = None
    ) -> tuple[bool, List[str]]:
        """Run all quality gate validations.

        Args:
            robot_type: Robot type identifier
            action: Action vector
            safety_score: Safety evaluation score
            instruction: Natural language instruction
            image_hash: Hash of input image
            image_shape: Image dimensions
            image_size_bytes: Image file size
            db: Database session
            redis: Redis client (optional)
            robot_config: Optional robot configuration

        Returns:
            Tuple of (all_valid, list_of_errors)
        """
        errors = []

        # Run all validations
        valid, error = await self.validate_robot_type(robot_type)
        if not valid:
            errors.append(error)

        valid, error = await self.validate_action_bounds(action, robot_config)
        if not valid:
            errors.append(error)

        valid, error = await self.validate_safety_score(safety_score)
        if not valid:
            errors.append(error)

        valid, error = await self.validate_instruction(instruction)
        if not valid:
            errors.append(error)

        valid, error = await self.validate_image_quality(image_shape, image_size_bytes)
        if not valid:
            errors.append(error)

        # Deduplication check (non-blocking)
        is_dup, error = await self.check_duplicate(instruction, image_hash, db, redis)
        if is_dup:
            errors.append(error)

        return len(errors) == 0, errors


# Global quality gate instance
quality_gate = QualityGate(
    dedup_window_seconds=300,  # 5 minutes
    min_safety_score=0.7
)


async def validate_inference_quality(
    robot_type: str,
    action: List[float],
    safety_score: float,
    instruction: str,
    image_hash: str,
    image_shape: List[int],
    image_size_bytes: int,
    db: AsyncSession,
    redis=None,
    robot_config: Optional[Dict] = None
) -> tuple[bool, List[str]]:
    """Convenience function to validate inference quality.

    Args:
        robot_type: Robot type identifier
        action: Action vector
        safety_score: Safety evaluation score
        instruction: Natural language instruction
        image_hash: Hash of input image
        image_shape: Image dimensions
        image_size_bytes: Image file size
        db: Database session
        redis: Redis client (optional)
        robot_config: Optional robot configuration

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    return await quality_gate.validate_all(
        robot_type=robot_type,
        action=action,
        safety_score=safety_score,
        instruction=instruction,
        image_hash=image_hash,
        image_shape=image_shape,
        image_size_bytes=image_size_bytes,
        db=db,
        redis=redis,
        robot_config=robot_config
    )
