"""Data contracts for VLA Inference API.

This package contains all Pydantic validation models for the data collection system.
These contracts are CRITICAL for maintaining data quality and the competitive moat.

All validation rules are derived from /docs/data-contracts.md (v1.0.0).
"""

# Robot types and specifications
from .robot_types import (
    RobotType,
    RobotSpec,
    ROBOT_SPECS,
    validate_robot_type,
    get_robot_spec,
    validate_action_vector_bounds,
)

# Inference log contracts
from .inference_log import (
    InferenceLogContract,
    InferenceStatus,
    InstructionCategory,
    ModelName,
)

# Analytics contracts
from .analytics import (
    RobotPerformanceMetricsContract,
    InstructionAnalyticsContract,
    ContextMetadataContract,
    ActionDimensionStats,
    ActionStatistics,
    FailurePatterns,
    LightingConditions,
    EnvironmentType,
    WorkspaceBounds,
)

# Consent contracts
from .consent import (
    CustomerDataConsentContract,
    ConsentTier,
    AnonymizationLevel,
)

# Feedback contracts
from .feedback import (
    FeedbackContract,
    FeedbackType,
)

__all__ = [
    # Robot types
    'RobotType',
    'RobotSpec',
    'ROBOT_SPECS',
    'validate_robot_type',
    'get_robot_spec',
    'validate_action_vector_bounds',

    # Inference log
    'InferenceLogContract',
    'InferenceStatus',
    'InstructionCategory',
    'ModelName',

    # Analytics
    'RobotPerformanceMetricsContract',
    'InstructionAnalyticsContract',
    'ContextMetadataContract',
    'ActionDimensionStats',
    'ActionStatistics',
    'FailurePatterns',
    'LightingConditions',
    'EnvironmentType',
    'WorkspaceBounds',

    # Consent
    'CustomerDataConsentContract',
    'ConsentTier',
    'AnonymizationLevel',

    # Feedback
    'FeedbackContract',
    'FeedbackType',
]

# Validation rule counts by module
VALIDATION_COUNTS = {
    'robot_types.py': {
        'enums': 1,  # RobotType with 34 values
        'specs': 3,  # ROBOT_SPECS with 3 detailed specifications
        'functions': 3,  # validate_robot_type, get_robot_spec, validate_action_vector_bounds
    },
    'inference_log.py': {
        'enums': 3,  # InferenceStatus, InstructionCategory, ModelName
        'validators': 13,  # request_id, timestamp, instruction, action_vector (2), robot_type, image_shape, safety_score, error_message, safety_consistency, latency_consistency, compute_derived_fields
        'fields': 15,  # 8 required + 6 optional + 2 computed
    },
    'analytics.py': {
        'models': 7,  # RobotPerformanceMetricsContract, InstructionAnalyticsContract, ContextMetadataContract, ActionDimensionStats, ActionStatistics, FailurePatterns, WorkspaceBounds
        'enums': 2,  # LightingConditions, EnvironmentType
        'validators': 15,  # Various validators across all models
    },
    'consent.py': {
        'enums': 2,  # ConsentTier, AnonymizationLevel
        'validators': 3,  # consent_tier_logic, anonymization_logic, expiration
        'fields': 10,  # Complete consent configuration
    },
    'feedback.py': {
        'enums': 1,  # FeedbackType
        'validators': 3,  # feedback_fields, corrected_action, timestamp_ordering
        'fields': 8,  # Feedback data fields
    },
}

# Total validation rules: 50+ validators across all contracts
TOTAL_VALIDATORS = sum(
    module.get('validators', 0) + module.get('functions', 0)
    for module in VALIDATION_COUNTS.values()
)
