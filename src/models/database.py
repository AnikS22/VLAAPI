"""SQLAlchemy ORM models for PostgreSQL database."""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

# Import pgvector column type for embeddings
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None  # Will be handled in migration

Base = declarative_base()


class Customer(Base):
    """Customer/user account model."""

    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("tier IN ('free', 'pro', 'enterprise')", name="chk_tier"),
        Index("idx_customers_email", "email"),
        Index("idx_customers_tier", "tier"),
        {"schema": "vlaapi"},
    )

    customer_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    email = Column(String(255), unique=True, nullable=False, index=True)
    company_name = Column(String(255), nullable=True)
    tier = Column(String(50), nullable=False, default="free")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    # Rate limiting configuration per tier
    rate_limit_rpm = Column(Integer, nullable=False, default=60)  # requests per minute
    rate_limit_rpd = Column(Integer, nullable=False, default=1000)  # requests per day

    # Usage quotas
    monthly_quota = Column(Integer, nullable=True)  # NULL = unlimited
    monthly_usage = Column(Integer, nullable=False, default=0)

    # Metadata (flexible JSONB for custom fields)
    metadata = Column(JSONB, nullable=True)

    # Relationships
    api_keys = relationship("APIKey", back_populates="customer", cascade="all, delete-orphan")
    inference_logs = relationship("InferenceLog", back_populates="customer")
    safety_incidents = relationship("SafetyIncident", back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer(id={self.customer_id}, email={self.email}, tier={self.tier})>"


class APIKey(Base):
    """API key model for authentication."""

    __tablename__ = "api_keys"
    __table_args__ = (
        CheckConstraint(
            "key_prefix ~ '^vla_(test|live)_[a-z0-9]{4}$'",
            name="chk_key_prefix",
        ),
        Index("idx_api_keys_customer", "customer_id"),
        Index("idx_api_keys_hash", "key_hash", unique=True),
        Index("idx_api_keys_active", "is_active", postgresql_where=Column("is_active") == True),
        {"schema": "vlaapi"},
    )

    key_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vlaapi.customers.customer_id", ondelete="CASCADE"),
        nullable=False,
    )

    # Key storage (NEVER store plaintext!)
    key_prefix = Column(String(12), nullable=False)  # First 8 chars for display
    key_hash = Column(String(128), nullable=False, unique=True)  # SHA-256 hash

    # Key metadata
    key_name = Column(String(100), nullable=True)  # User-friendly name
    scopes = Column(ARRAY(Text), default=["inference"], nullable=False)

    # Lifecycle
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # NULL = never expires
    is_active = Column(Boolean, nullable=False, default=True)

    # Rate limiting overrides (per-key, overrides customer defaults)
    rate_limit_override_rpm = Column(Integer, nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="api_keys")
    inference_logs = relationship("InferenceLog", back_populates="api_key")

    def __repr__(self) -> str:
        return f"<APIKey(id={self.key_id}, prefix={self.key_prefix}, customer={self.customer_id})>"


class InferenceLog(Base):
    """Log of inference requests for analytics and billing."""

    __tablename__ = "inference_logs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'error', 'safety_rejected', 'timeout', 'rate_limited')",
            name="chk_status",
        ),
        CheckConstraint(
            "instruction_category IN ('pick', 'place', 'navigate', 'manipulate', 'inspect', 'measure', 'open', 'close', 'push', 'pull', 'other')",
            name="chk_instruction_category",
        ),
        Index("idx_logs_customer", "customer_id"),
        Index("idx_logs_timestamp", "timestamp", postgresql_using="btree", postgresql_ops={"timestamp": "DESC"}),
        Index("idx_logs_status", "status"),
        Index("idx_logs_model", "model_name"),
        Index("idx_logs_customer_robot_timestamp", "customer_id", "robot_type", "timestamp"),
        {
            "schema": "vlaapi",
            "postgresql_partition_by": "RANGE (timestamp)",  # Monthly partitioning
        },
    )

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vlaapi.customers.customer_id"),
        nullable=False,
    )
    key_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vlaapi.api_keys.key_id"),
        nullable=False,
    )

    # Request details
    request_id = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    model_name = Column(String(50), nullable=False)

    # Input metadata (NOT storing actual images for privacy/space)
    instruction = Column(Text, nullable=False)
    image_shape = Column(ARRAY(Integer), nullable=True)  # [height, width, channels]

    # Output
    action_vector = Column(ARRAY(Float), nullable=True)  # 7-DoF action
    safety_score = Column(Float, nullable=True)  # 0.0 - 1.0
    safety_flags = Column(JSONB, nullable=True)  # {collision: false, workspace: true, ...}

    # Performance metrics
    inference_latency_ms = Column(Integer, nullable=True)  # Total time
    queue_wait_ms = Column(Integer, nullable=True)
    gpu_compute_ms = Column(Integer, nullable=True)

    # Status
    status = Column(String(20), nullable=False)  # success, error, safety_rejected, timeout
    error_message = Column(Text, nullable=True)

    # NEW: Robot and instruction analytics (added for moat analysis)
    robot_type = Column(String(100), nullable=False)  # CRITICAL for competitive moat
    instruction_category = Column(String(50), nullable=True)  # Auto-classified category
    action_magnitude = Column(Float, nullable=True)  # L2 norm of action_vector

    # Relationships
    customer = relationship("Customer", back_populates="inference_logs")
    api_key = relationship("APIKey", back_populates="inference_logs")
    safety_incident = relationship(
        "SafetyIncident",
        back_populates="inference_log",
        uselist=False,  # One-to-one
    )
    context_metadata = relationship(
        "ContextMetadata",
        back_populates="inference_log",
        uselist=False,
    )
    feedback_items = relationship("Feedback", back_populates="inference_log", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<InferenceLog(id={self.log_id}, status={self.status}, model={self.model_name}, robot={self.robot_type})>"


class SafetyIncident(Base):
    """Safety violation incidents for monitoring."""

    __tablename__ = "safety_incidents"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="chk_severity",
        ),
        CheckConstraint(
            "action_taken IN ('logged', 'clamped', 'rejected', 'emergency_stop')",
            name="chk_action_taken",
        ),
        CheckConstraint(
            "environment_type IN ('lab', 'warehouse', 'factory', 'outdoor', 'home', 'office', 'hospital', 'retail', 'other')",
            name="chk_environment_type",
        ),
        CheckConstraint(
            "instruction_category IN ('pick', 'place', 'navigate', 'manipulate', 'inspect', 'measure', 'open', 'close', 'push', 'pull', 'other')",
            name="chk_incident_instruction_category",
        ),
        CheckConstraint(
            "violation_type != 'collision' OR severity IN ('high', 'critical')",
            name="chk_collision_severity",
        ),
        CheckConstraint(
            "severity != 'critical' OR action_taken IN ('emergency_stop', 'rejected')",
            name="chk_critical_action",
        ),
        Index("idx_incidents_customer", "customer_id"),
        Index("idx_incidents_severity", "severity"),
        Index("idx_incidents_timestamp", "timestamp", postgresql_using="btree", postgresql_ops={"timestamp": "DESC"}),
        Index("idx_incidents_violation_type", "violation_type"),
        Index("idx_incidents_robot_type", "robot_type"),
        Index("idx_incidents_environment", "environment_type"),
        Index("idx_incidents_category", "instruction_category"),
        Index("idx_incidents_robot_severity", "robot_type", "severity"),
        {"schema": "vlaapi"},
    )

    incident_id = Column(Integer, primary_key=True, autoincrement=True)
    log_id = Column(
        Integer,
        ForeignKey("vlaapi.inference_logs.log_id"),
        nullable=True,  # May not be linked to a specific log
    )
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vlaapi.customers.customer_id"),
        nullable=False,
    )

    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    severity = Column(String(20), nullable=False)  # low, medium, high, critical

    # Violation details
    violation_type = Column(String(50), nullable=False)  # collision, workspace, velocity, classifier
    violation_details = Column(JSONB, nullable=False)  # Flexible details about the violation

    # Action taken
    action_taken = Column(String(50), nullable=False)  # rejected, clamped, logged, emergency_stop
    original_action = Column(ARRAY(Float), nullable=True)
    safe_action = Column(ARRAY(Float), nullable=True)  # Clamped/modified action

    # NEW: Context for safety analysis
    robot_type = Column(String(100), nullable=False)  # Robot type for incident analysis
    environment_type = Column(String(50), nullable=False, default="other")  # Deployment environment
    instruction_category = Column(String(50), nullable=True)  # Instruction category

    # Relationships
    customer = relationship("Customer", back_populates="safety_incidents")
    inference_log = relationship("InferenceLog", back_populates="safety_incident")

    def __repr__(self) -> str:
        return f"<SafetyIncident(id={self.incident_id}, type={self.violation_type}, severity={self.severity}, robot={self.robot_type})>"


class RobotPerformanceMetrics(Base):
    """Aggregated performance metrics per robot type."""

    __tablename__ = "robot_performance_metrics"
    __table_args__ = (
        CheckConstraint("total_inferences > 0", name="chk_total_inferences_positive"),
        CheckConstraint("success_count <= total_inferences", name="chk_success_count_valid"),
        CheckConstraint("success_rate >= 0.0 AND success_rate <= 1.0", name="chk_success_rate_range"),
        CheckConstraint("avg_safety_score >= 0.0 AND avg_safety_score <= 1.0", name="chk_avg_safety_score_range"),
        CheckConstraint("p50_latency_ms <= p95_latency_ms", name="chk_latency_p50_p95"),
        CheckConstraint("p95_latency_ms <= p99_latency_ms", name="chk_latency_p95_p99"),
        Index("idx_robot_metrics_customer", "customer_id"),
        Index("idx_robot_metrics_robot_type", "robot_type"),
        Index("idx_robot_metrics_date", "aggregation_date", postgresql_using="btree", postgresql_ops={"aggregation_date": "DESC"}),
        Index("idx_robot_metrics_robot_model", "robot_type", "model_name"),
        Index("idx_robot_metrics_customer_robot_date", "customer_id", "robot_type", "aggregation_date", unique=True),
        {"schema": "vlaapi"},
    )

    metric_id = Column(Integer, primary_key=True, autoincrement=True)

    # Aggregation dimensions (unique constraint)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("vlaapi.customers.customer_id"), nullable=False)
    robot_type = Column(String(100), nullable=False)
    model_name = Column(String(50), nullable=False)
    aggregation_date = Column(Date, nullable=False)

    # Counts
    total_inferences = Column(Integer, nullable=False)
    success_count = Column(Integer, nullable=False)
    success_rate = Column(Float, nullable=False)

    # Latency metrics (in milliseconds)
    avg_latency_ms = Column(Float, nullable=False)
    p50_latency_ms = Column(Float, nullable=False)
    p95_latency_ms = Column(Float, nullable=False)
    p99_latency_ms = Column(Float, nullable=False)

    # Safety metrics
    avg_safety_score = Column(Float, nullable=False)

    # Action statistics (JSONB with stats for each DoF and magnitude)
    action_statistics = Column(JSONB, nullable=False)

    # Common patterns
    common_instructions = Column(ARRAY(Text), nullable=False)

    # Failure patterns (JSONB)
    failure_patterns = Column(JSONB, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    customer = relationship("Customer")

    def __repr__(self) -> str:
        return f"<RobotPerformanceMetrics(robot={self.robot_type}, date={self.aggregation_date}, inferences={self.total_inferences})>"


class InstructionAnalytics(Base):
    """Deduplicated instruction analytics with semantic embeddings."""

    __tablename__ = "instruction_analytics"
    __table_args__ = (
        CheckConstraint("total_uses > 0", name="chk_total_uses_positive"),
        CheckConstraint("unique_customers > 0", name="chk_unique_customers_positive"),
        CheckConstraint("success_rate >= 0.0 AND success_rate <= 1.0", name="chk_instruction_success_rate_range"),
        CheckConstraint("first_seen <= last_seen", name="chk_temporal_consistency"),
        Index("idx_instruction_analytics_hash", "instruction_hash", unique=True),
        Index("idx_instruction_analytics_category", "instruction_category"),
        Index("idx_instruction_analytics_uses", "total_uses", postgresql_using="btree", postgresql_ops={"total_uses": "DESC"}),
        Index("idx_instruction_analytics_last_seen", "last_seen", postgresql_using="btree", postgresql_ops={"last_seen": "DESC"}),
        # Note: Vector index will be added in migration with proper HNSW or IVFFlat parameters
        {"schema": "vlaapi"},
    )

    analytics_id = Column(Integer, primary_key=True, autoincrement=True)

    # Deduplication
    instruction_hash = Column(String(64), nullable=False, unique=True)  # SHA-256 hash
    instruction_text = Column(Text, nullable=False)
    instruction_category = Column(String(50), nullable=False)

    # Usage statistics
    total_uses = Column(Integer, nullable=False)
    unique_customers = Column(Integer, nullable=False)
    success_rate = Column(Float, nullable=False)

    # Performance
    avg_latency_ms = Column(Float, nullable=False)
    avg_safety_score = Column(Float, nullable=False)

    # Robot affinity (JSONB: {robot_type: count})
    robot_type_distribution = Column(JSONB, nullable=False)

    # Temporal
    first_seen = Column(DateTime(timezone=True), nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=False)

    # Semantic embeddings (pgvector) - nullable for gradual rollout
    instruction_embedding = Column(Vector(512) if Vector else ARRAY(Float), nullable=True)

    def __repr__(self) -> str:
        return f"<InstructionAnalytics(hash={self.instruction_hash[:8]}..., uses={self.total_uses}, category={self.instruction_category})>"


class ContextMetadata(Base):
    """Context metadata for inference requests (privacy-aware)."""

    __tablename__ = "context_metadata"
    __table_args__ = (
        CheckConstraint(
            "environment_type IN ('lab', 'warehouse', 'factory', 'outdoor', 'home', 'office', 'hospital', 'retail', 'other')",
            name="chk_context_environment_type",
        ),
        Index("idx_context_metadata_log", "log_id", unique=True),
        Index("idx_context_metadata_customer", "customer_id"),
        Index("idx_context_metadata_environment", "environment_type"),
        # Note: Vector index will be added in migration
        {"schema": "vlaapi"},
    )

    context_id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    log_id = Column(Integer, ForeignKey("vlaapi.inference_logs.log_id", ondelete="CASCADE"), nullable=False, unique=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("vlaapi.customers.customer_id"), nullable=False)

    # Environment context
    environment_type = Column(String(50), nullable=False)
    lighting_condition = Column(String(50), nullable=True)  # bright, dim, dark, mixed
    object_count = Column(Integer, nullable=True)  # Number of objects in scene

    # Ground truth (if available from feedback)
    success = Column(Boolean, nullable=True)

    # Privacy-aware image embedding (NOT raw images)
    image_embedding = Column(Vector(512) if Vector else ARRAY(Float), nullable=True)

    # Additional metadata (flexible JSONB)
    additional_metadata = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    inference_log = relationship("InferenceLog", back_populates="context_metadata")
    customer = relationship("Customer")

    def __repr__(self) -> str:
        return f"<ContextMetadata(log_id={self.log_id}, env={self.environment_type})>"


class CustomerDataConsent(Base):
    """Customer data consent and privacy preferences."""

    __tablename__ = "customer_data_consent"
    __table_args__ = (
        CheckConstraint("consent_tier IN ('none', 'metadata', 'full')", name="chk_consent_tier"),
        CheckConstraint("anonymization_level IN ('none', 'partial', 'full')", name="chk_anonymization_level"),
        CheckConstraint("consent_version >= 1", name="chk_consent_version_positive"),
        CheckConstraint("expires_at IS NULL OR expires_at > consented_at", name="chk_expiration"),
        # Consent tier logic
        CheckConstraint(
            "consent_tier != 'none' OR (can_store_images = false AND can_store_embeddings = false AND can_use_for_training = false)",
            name="chk_none_tier",
        ),
        CheckConstraint(
            "consent_tier != 'metadata' OR (can_store_images = false AND can_store_embeddings = true AND can_use_for_training = true)",
            name="chk_metadata_tier",
        ),
        CheckConstraint(
            "consent_tier != 'full' OR (can_store_images = true AND can_store_embeddings = true AND can_use_for_training = true)",
            name="chk_full_tier",
        ),
        # Anonymization logic
        CheckConstraint(
            "can_store_images = false OR anonymization_level != 'none'",
            name="chk_anonymization",
        ),
        Index("idx_consent_customer", "customer_id", unique=True),
        Index("idx_consent_tier", "consent_tier"),
        Index("idx_consent_expires", "expires_at", postgresql_where=Column("expires_at").isnot(None)),
        {"schema": "vlaapi"},
    )

    consent_id = Column(Integer, primary_key=True, autoincrement=True)

    # Customer (unique - one consent record per customer)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("vlaapi.customers.customer_id"), nullable=False, unique=True)

    # Consent configuration
    consent_tier = Column(String(20), nullable=False)  # none, metadata, full
    consent_version = Column(Integer, nullable=False)  # Increments with policy changes

    # Temporal
    consented_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Granular permissions
    can_store_images = Column(Boolean, nullable=False)
    can_store_embeddings = Column(Boolean, nullable=False)
    can_use_for_training = Column(Boolean, nullable=False)

    # Anonymization
    anonymization_level = Column(String(20), nullable=False)  # none, partial, full

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    customer = relationship("Customer")

    def __repr__(self) -> str:
        return f"<CustomerDataConsent(customer_id={self.customer_id}, tier={self.consent_tier})>"


class Feedback(Base):
    """Customer feedback for inference quality."""

    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint(
            "feedback_type IN ('success_rating', 'safety_rating', 'action_correction', 'failure_report')",
            name="chk_feedback_type",
        ),
        CheckConstraint("rating IS NULL OR (rating >= 1 AND rating <= 5)", name="chk_rating_range"),
        # Ensure rating is provided for rating types
        CheckConstraint(
            "(feedback_type NOT IN ('success_rating', 'safety_rating')) OR (rating IS NOT NULL)",
            name="chk_rating_required",
        ),
        # Ensure corrected_action is provided for correction type
        CheckConstraint(
            "feedback_type != 'action_correction' OR corrected_action IS NOT NULL",
            name="chk_corrected_action_required",
        ),
        # Ensure failure_reason is provided for failure report
        CheckConstraint(
            "feedback_type != 'failure_report' OR failure_reason IS NOT NULL",
            name="chk_failure_reason_required",
        ),
        Index("idx_feedback_log", "log_id"),
        Index("idx_feedback_customer", "customer_id"),
        Index("idx_feedback_type", "feedback_type"),
        Index("idx_feedback_timestamp", "timestamp", postgresql_using="btree", postgresql_ops={"timestamp": "DESC"}),
        Index("idx_feedback_rating", "rating", postgresql_where=Column("rating").isnot(None)),
        {"schema": "vlaapi"},
    )

    feedback_id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    log_id = Column(Integer, ForeignKey("vlaapi.inference_logs.log_id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("vlaapi.customers.customer_id"), nullable=False)

    # Feedback type
    feedback_type = Column(String(50), nullable=False)

    # Type-specific fields (nullable, validated by constraints)
    rating = Column(Integer, nullable=True)  # 1-5 stars
    corrected_action = Column(ARRAY(Float), nullable=True)  # 7-DoF corrected action
    failure_reason = Column(Text, nullable=True)

    # Optional notes
    notes = Column(Text, nullable=True)

    # Temporal
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    inference_log = relationship("InferenceLog", back_populates="feedback_items")
    customer = relationship("Customer")

    def __repr__(self) -> str:
        return f"<Feedback(id={self.feedback_id}, type={self.feedback_type}, log_id={self.log_id})>"


# Note: Usage aggregations will be implemented as materialized views
# Refreshed periodically via cron or pg_cron
