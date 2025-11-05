"""SQLAlchemy ORM models for PostgreSQL database."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    CheckConstraint,
    Column,
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
        Index("idx_logs_customer", "customer_id"),
        Index("idx_logs_timestamp", "timestamp", postgresql_using="btree", postgresql_ops={"timestamp": "DESC"}),
        Index("idx_logs_status", "status"),
        Index("idx_logs_model", "model_name"),
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

    # Relationships
    customer = relationship("Customer", back_populates="inference_logs")
    api_key = relationship("APIKey", back_populates="inference_logs")
    safety_incident = relationship(
        "SafetyIncident",
        back_populates="inference_log",
        uselist=False,  # One-to-one
    )

    def __repr__(self) -> str:
        return f"<InferenceLog(id={self.log_id}, status={self.status}, model={self.model_name})>"


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
        Index("idx_incidents_customer", "customer_id"),
        Index("idx_incidents_severity", "severity"),
        Index("idx_incidents_timestamp", "timestamp", postgresql_using="btree", postgresql_ops={"timestamp": "DESC"}),
        Index("idx_incidents_violation_type", "violation_type"),
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

    # Relationships
    customer = relationship("Customer", back_populates="safety_incidents")
    inference_log = relationship("InferenceLog", back_populates="safety_incident")

    def __repr__(self) -> str:
        return f"<SafetyIncident(id={self.incident_id}, type={self.violation_type}, severity={self.severity})>"


# Note: Usage aggregations will be implemented as a materialized view
# Refreshed periodically via cron or pg_cron
