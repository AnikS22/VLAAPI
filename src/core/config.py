"""Configuration management using Pydantic Settings.

Loads environment variables from .env file and validates configuration.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=(),  # Allow model_* field names
    )

    # =========================================================================
    # APPLICATION SETTINGS
    # =========================================================================
    app_name: str = Field(default="VLA Inference API", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    environment: str = Field(
        default="development",
        description="Environment: development, staging, production",
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, ge=1, le=65535, description="API port")
    api_workers: int = Field(default=1, ge=1, le=32, description="Number of workers")

    # CORS Settings
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        description="Allowed CORS origins",
    )
    cors_allow_credentials: bool = Field(
        default=True, description="Allow credentials in CORS"
    )

    # =========================================================================
    # DATABASE SETTINGS
    # =========================================================================
    database_url: str = Field(
        default="postgresql+asyncpg://vlaapi:password@localhost:5432/vlaapi",
        description="PostgreSQL connection URL",
    )
    database_pool_size: int = Field(
        default=20, ge=1, le=100, description="Database connection pool size"
    )
    database_max_overflow: int = Field(
        default=10, ge=0, le=100, description="Database max overflow connections"
    )
    database_pool_timeout: int = Field(
        default=30, ge=1, description="Database pool timeout (seconds)"
    )
    database_pool_recycle: int = Field(
        default=3600, ge=0, description="Database connection recycle time (seconds)"
    )

    # =========================================================================
    # REDIS SETTINGS
    # =========================================================================
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    redis_max_connections: int = Field(
        default=50, ge=1, le=1000, description="Redis max connections"
    )
    redis_socket_timeout: int = Field(
        default=5, ge=1, description="Redis socket timeout (seconds)"
    )

    # =========================================================================
    # VLA MODEL SETTINGS
    # =========================================================================
    enabled_models: List[str] = Field(
        default_factory=lambda: ["openvla-7b"],
        description="Enabled VLA models (comma-separated)",
    )
    default_model: str = Field(
        default="openvla-7b", description="Default VLA model"
    )
    gpu_device: int = Field(default=0, ge=0, description="CUDA device ID")
    vla_model_dtype: str = Field(
        default="bfloat16", description="Model dtype: float32, float16, bfloat16"
    )
    low_cpu_mem_usage: bool = Field(
        default=True, description="Use low CPU memory during model loading"
    )
    trust_remote_code: bool = Field(
        default=True, description="Trust remote code from HuggingFace"
    )

    # HuggingFace Settings
    hf_home: Optional[str] = Field(
        default=None, description="HuggingFace cache directory"
    )
    hf_token: Optional[str] = Field(
        default=None, description="HuggingFace API token"
    )
    transformers_cache: Optional[str] = Field(
        default=None, description="Transformers model cache directory"
    )

    # Inference Queue Settings
    inference_queue_max_size: int = Field(
        default=100, ge=1, le=1000, description="Maximum inference queue size"
    )
    inference_batch_size: int = Field(
        default=4, ge=1, le=32, description="Inference batch size"
    )
    inference_batch_timeout_ms: int = Field(
        default=50, ge=1, le=1000, description="Batch formation timeout (ms)"
    )
    inference_max_workers: int = Field(
        default=2, ge=1, le=8, description="Number of inference workers"
    )

    # =========================================================================
    # SAFETY SETTINGS
    # =========================================================================
    safety_enable_workspace_check: bool = Field(
        default=True, description="Enable workspace boundary checking"
    )
    safety_enable_velocity_check: bool = Field(
        default=True, description="Enable velocity limit checking"
    )
    safety_enable_collision_check: bool = Field(
        default=True, description="Enable collision risk checking"
    )

    # Safety Thresholds
    safety_default_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Default minimum safety score",
    )
    safety_velocity_limit_linear: float = Field(
        default=0.5, ge=0.0, description="Linear velocity limit (m/s)"
    )
    safety_velocity_limit_angular: float = Field(
        default=1.0, ge=0.0, description="Angular velocity limit (rad/s)"
    )
    safety_acceleration_limit: float = Field(
        default=2.0, ge=0.0, description="Acceleration limit (m/s^2)"
    )

    # Workspace Bounds
    safety_workspace_x_min: float = Field(default=-0.5, description="Workspace X min")
    safety_workspace_x_max: float = Field(default=0.5, description="Workspace X max")
    safety_workspace_y_min: float = Field(default=-0.5, description="Workspace Y min")
    safety_workspace_y_max: float = Field(default=0.5, description="Workspace Y max")
    safety_workspace_z_min: float = Field(default=0.0, description="Workspace Z min")
    safety_workspace_z_max: float = Field(default=0.8, description="Workspace Z max")

    # ML Safety Classifier (pluggable for alignment research)
    safety_classifier_enabled: bool = Field(
        default=False, description="Enable ML safety classifier"
    )
    safety_classifier_path: Optional[str] = Field(
        default=None, description="Path to safety classifier model"
    )
    safety_classifier_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="ML classifier safety threshold",
    )

    # =========================================================================
    # AUTHENTICATION & SECURITY
    # =========================================================================
    api_key_prefix: str = Field(default="vla_live", description="API key prefix")
    api_key_length: int = Field(
        default=32, ge=16, le=64, description="API key length (bytes)"
    )
    api_key_hash_algorithm: str = Field(
        default="sha256", description="API key hash algorithm"
    )

    secret_key: str = Field(
        default="insecure-secret-key-change-in-production",
        description="Application secret key",
    )

    # JWT Settings (for future admin dashboard)
    jwt_secret_key: Optional[str] = Field(
        default=None, description="JWT secret key"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(
        default=30, ge=1, description="JWT access token expiry (minutes)"
    )

    # =========================================================================
    # RATE LIMITING
    # =========================================================================
    rate_limit_enabled: bool = Field(
        default=True, description="Enable rate limiting"
    )

    # Default tier limits
    rate_limit_free_rpm: int = Field(
        default=10, ge=1, description="Free tier requests per minute"
    )
    rate_limit_free_rpd: int = Field(
        default=1000, ge=1, description="Free tier requests per day"
    )
    rate_limit_free_monthly: int = Field(
        default=10000, ge=1, description="Free tier monthly quota"
    )

    rate_limit_pro_rpm: int = Field(
        default=100, ge=1, description="Pro tier requests per minute"
    )
    rate_limit_pro_rpd: int = Field(
        default=10000, ge=1, description="Pro tier requests per day"
    )
    rate_limit_pro_monthly: int = Field(
        default=100000, ge=1, description="Pro tier monthly quota"
    )

    rate_limit_enterprise_rpm: int = Field(
        default=1000, ge=1, description="Enterprise tier requests per minute"
    )
    rate_limit_enterprise_rpd: int = Field(
        default=100000, ge=1, description="Enterprise tier requests per day"
    )
    rate_limit_enterprise_monthly: Optional[int] = Field(
        default=None, description="Enterprise tier monthly quota (None = unlimited)"
    )

    # =========================================================================
    # MONITORING & OBSERVABILITY
    # =========================================================================
    metrics_enabled: bool = Field(
        default=True, description="Enable Prometheus metrics"
    )
    metrics_port: int = Field(
        default=9090, ge=1, le=65535, description="Metrics port"
    )

    log_format: str = Field(
        default="json", description="Log format: json or text"
    )

    sentry_dsn: Optional[str] = Field(
        default=None, description="Sentry DSN for error tracking"
    )
    sentry_environment: Optional[str] = Field(
        default=None, description="Sentry environment"
    )

    # =========================================================================
    # ROBOT CONFIGURATIONS
    # =========================================================================
    default_robot_type: str = Field(
        default="franka_panda", description="Default robot type"
    )
    robot_configs_dir: str = Field(
        default="config/robot_configs", description="Robot configs directory"
    )

    # =========================================================================
    # PERFORMANCE TUNING
    # =========================================================================
    request_timeout_seconds: int = Field(
        default=30, ge=1, description="Request timeout (seconds)"
    )
    inference_timeout_seconds: int = Field(
        default=10, ge=1, description="Inference timeout (seconds)"
    )
    max_concurrent_requests: int = Field(
        default=100, ge=1, description="Max concurrent requests"
    )

    # =========================================================================
    # MONITORING & GPU
    # =========================================================================
    enable_prometheus: bool = Field(
        default=True, description="Enable Prometheus metrics"
    )
    enable_gpu_monitoring: bool = Field(
        default=True, description="Enable GPU monitoring"
    )
    gpu_poll_interval: int = Field(
        default=5, ge=1, le=60, description="GPU polling interval (seconds)"
    )

    # =========================================================================
    # EMBEDDINGS
    # =========================================================================
    enable_embeddings: bool = Field(
        default=True, description="Enable embeddings generation"
    )
    instruction_embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Text embedding model"
    )
    image_embedding_model: str = Field(
        default="openai/clip-vit-base-patch32",
        description="Image embedding model (CLIP)"
    )
    embedding_cache_ttl: int = Field(
        default=300, ge=0, description="Embedding cache TTL (seconds)"
    )

    # =========================================================================
    # STORAGE (S3/MinIO)
    # =========================================================================
    s3_endpoint: str = Field(
        default="", description="S3/MinIO endpoint URL"
    )
    s3_bucket: str = Field(
        default="vla-training-data", description="S3 bucket name"
    )
    s3_access_key: str = Field(
        default="", description="S3 access key"
    )
    s3_secret_key: str = Field(
        default="", description="S3 secret key"
    )
    enable_s3_storage: bool = Field(
        default=False, description="Enable S3 storage"
    )
    s3_region: str = Field(
        default="us-east-1", description="S3 region"
    )

    # =========================================================================
    # DATA RETENTION
    # =========================================================================
    raw_data_retention_days: int = Field(
        default=90, ge=-1, description="Raw data retention days (-1 = forever)"
    )
    aggregated_data_retention_days: int = Field(
        default=365, ge=-1, description="Aggregated data retention days"
    )
    safety_data_retention_days: int = Field(
        default=-1, description="Safety incident data retention (-1 = forever)"
    )

    # =========================================================================
    # ETL & DATA PIPELINE
    # =========================================================================
    etl_schedule_hour: int = Field(
        default=2, ge=0, le=23, description="ETL daily schedule hour (UTC)"
    )
    etl_batch_size: int = Field(
        default=1000, ge=1, le=10000, description="ETL batch size"
    )
    etl_enabled: bool = Field(
        default=True, description="Enable ETL pipeline"
    )

    # =========================================================================
    # CONSENT & PRIVACY
    # =========================================================================
    default_consent_tier: str = Field(
        default="none", description="Default consent tier: none, basic, full"
    )
    consent_cache_ttl: int = Field(
        default=600, ge=0, description="Consent cache TTL (seconds)"
    )

    # =========================================================================
    # ANONYMIZATION
    # =========================================================================
    anonymization_level: str = Field(
        default="full", description="Anonymization level: none, partial, full"
    )
    anonymization_hash_salt: str = Field(
        default="change-in-production", description="Salt for anonymization hashing"
    )

    # =========================================================================
    # STRIPE BILLING SETTINGS
    # =========================================================================
    stripe_api_key: Optional[str] = Field(
        default=None, description="Stripe secret API key"
    )
    stripe_publishable_key: Optional[str] = Field(
        default=None, description="Stripe publishable key"
    )
    stripe_webhook_secret: Optional[str] = Field(
        default=None, description="Stripe webhook signing secret"
    )
    stripe_price_id_pro: Optional[str] = Field(
        default=None, description="Stripe Price ID for Pro tier ($499/mo)"
    )
    stripe_price_id_enterprise: Optional[str] = Field(
        default=None, description="Stripe Price ID for Enterprise tier (custom)"
    )
    enable_stripe: bool = Field(
        default=False, description="Enable Stripe billing integration"
    )

    # =========================================================================
    # DEVELOPMENT SETTINGS
    # =========================================================================
    auto_reload: bool = Field(
        default=False, description="Auto-reload on code changes"
    )
    use_mock_models: bool = Field(
        default=False, description="Use mock models for testing"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from JSON string or list."""
        if isinstance(v, str):
            import json
            try:
                # Try parsing as JSON array
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            # Fallback: treat as comma-separated
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("enabled_models", mode="before")
    @classmethod
    def parse_enabled_models(cls, v):
        """Parse comma-separated string to list."""
        if isinstance(v, str):
            return [model.strip() for model in v.split(",")]
        return v

    @field_validator("vla_model_dtype")
    @classmethod
    def validate_dtype(cls, v):
        """Validate model dtype."""
        valid_dtypes = ["float32", "float16", "bfloat16"]
        if v not in valid_dtypes:
            raise ValueError(f"Invalid dtype. Must be one of: {valid_dtypes}")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v_upper

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings: Application settings instance

    Note:
        This function is cached to ensure settings are loaded only once.
    """
    return Settings()


# Global settings instance
settings = get_settings()
