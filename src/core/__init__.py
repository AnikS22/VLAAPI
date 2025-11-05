"""Core module for VLA Inference API Platform.

This module provides fundamental utilities including:
- Configuration management
- Database connections
- Redis client
- Security utilities
- Constants and action space definitions
"""

from src.core.config import settings
from src.core.constants import (
    ACTION_SPACE_DIM,
    SUPPORTED_ROBOT_TYPES,
    SUPPORTED_VLA_MODELS,
)

__all__ = [
    "settings",
    "ACTION_SPACE_DIM",
    "SUPPORTED_ROBOT_TYPES",
    "SUPPORTED_VLA_MODELS",
]
