"""Add analytics tables and extend existing tables

Revision ID: 001
Revises: base
Create Date: 2025-11-06

This migration adds:
1. New analytics tables (robot_performance_metrics, instruction_analytics, context_metadata, customer_data_consent)
2. Extensions to existing tables (inference_logs, safety_incidents)
3. Materialized views for aggregated reporting
4. Performance indexes and constraints
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""

    # ========================================================================
    # 1. Enable pgvector extension for embeddings
    # ========================================================================
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ========================================================================
    # 2. Add new columns to inference_logs table
    # ========================================================================
    op.add_column(
        'inference_logs',
        sa.Column('robot_type', sa.String(length=100), nullable=False, server_default='unknown'),
        schema='vlaapi'
    )
    op.add_column(
        'inference_logs',
        sa.Column('instruction_category', sa.String(length=50), nullable=True),
        schema='vlaapi'
    )
    op.add_column(
        'inference_logs',
        sa.Column('action_magnitude', sa.Float(), nullable=True),
        schema='vlaapi'
    )

    # Add check constraint for instruction_category
    op.create_check_constraint(
        'chk_instruction_category',
        'inference_logs',
        "instruction_category IN ('pick', 'place', 'navigate', 'manipulate', 'inspect', 'measure', 'open', 'close', 'push', 'pull', 'other')",
        schema='vlaapi'
    )

    # Add composite index for analytics queries
    op.create_index(
        'idx_logs_customer_robot_timestamp',
        'inference_logs',
        ['customer_id', 'robot_type', 'timestamp'],
        schema='vlaapi'
    )

    # ========================================================================
    # 3. Add new columns to safety_incidents table
    # ========================================================================
    op.add_column(
        'safety_incidents',
        sa.Column('robot_type', sa.String(length=100), nullable=False, server_default='unknown'),
        schema='vlaapi'
    )
    op.add_column(
        'safety_incidents',
        sa.Column('environment_type', sa.String(length=50), nullable=False, server_default='other'),
        schema='vlaapi'
    )
    op.add_column(
        'safety_incidents',
        sa.Column('instruction_category', sa.String(length=50), nullable=True),
        schema='vlaapi'
    )

    # Add check constraints
    op.create_check_constraint(
        'chk_environment_type',
        'safety_incidents',
        "environment_type IN ('lab', 'warehouse', 'factory', 'outdoor', 'home', 'office', 'hospital', 'retail', 'other')",
        schema='vlaapi'
    )
    op.create_check_constraint(
        'chk_incident_instruction_category',
        'safety_incidents',
        "instruction_category IN ('pick', 'place', 'navigate', 'manipulate', 'inspect', 'measure', 'open', 'close', 'push', 'pull', 'other')",
        schema='vlaapi'
    )
    op.create_check_constraint(
        'chk_collision_severity',
        'safety_incidents',
        "violation_type != 'collision' OR severity IN ('high', 'critical')",
        schema='vlaapi'
    )
    op.create_check_constraint(
        'chk_critical_action',
        'safety_incidents',
        "severity != 'critical' OR action_taken IN ('emergency_stop', 'rejected')",
        schema='vlaapi'
    )

    # Add indexes for new columns
    op.create_index('idx_incidents_robot_type', 'safety_incidents', ['robot_type'], schema='vlaapi')
    op.create_index('idx_incidents_environment', 'safety_incidents', ['environment_type'], schema='vlaapi')
    op.create_index('idx_incidents_category', 'safety_incidents', ['instruction_category'], schema='vlaapi')
    op.create_index('idx_incidents_robot_severity', 'safety_incidents', ['robot_type', 'severity'], schema='vlaapi')

    # ========================================================================
    # 4. Create robot_performance_metrics table
    # ========================================================================
    op.create_table(
        'robot_performance_metrics',
        sa.Column('metric_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('robot_type', sa.String(length=100), nullable=False),
        sa.Column('model_name', sa.String(length=50), nullable=False),
        sa.Column('aggregation_date', sa.Date(), nullable=False),
        sa.Column('total_inferences', sa.Integer(), nullable=False),
        sa.Column('success_count', sa.Integer(), nullable=False),
        sa.Column('success_rate', sa.Float(), nullable=False),
        sa.Column('avg_latency_ms', sa.Float(), nullable=False),
        sa.Column('p50_latency_ms', sa.Float(), nullable=False),
        sa.Column('p95_latency_ms', sa.Float(), nullable=False),
        sa.Column('p99_latency_ms', sa.Float(), nullable=False),
        sa.Column('avg_safety_score', sa.Float(), nullable=False),
        sa.Column('action_statistics', postgresql.JSONB(), nullable=False),
        sa.Column('common_instructions', postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column('failure_patterns', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('total_inferences > 0', name='chk_total_inferences_positive'),
        sa.CheckConstraint('success_count <= total_inferences', name='chk_success_count_valid'),
        sa.CheckConstraint('success_rate >= 0.0 AND success_rate <= 1.0', name='chk_success_rate_range'),
        sa.CheckConstraint('avg_safety_score >= 0.0 AND avg_safety_score <= 1.0', name='chk_avg_safety_score_range'),
        sa.CheckConstraint('p50_latency_ms <= p95_latency_ms', name='chk_latency_p50_p95'),
        sa.CheckConstraint('p95_latency_ms <= p99_latency_ms', name='chk_latency_p95_p99'),
        sa.ForeignKeyConstraint(['customer_id'], ['vlaapi.customers.customer_id']),
        sa.PrimaryKeyConstraint('metric_id'),
        schema='vlaapi'
    )

    # Indexes for robot_performance_metrics
    op.create_index('idx_robot_metrics_customer', 'robot_performance_metrics', ['customer_id'], schema='vlaapi')
    op.create_index('idx_robot_metrics_robot_type', 'robot_performance_metrics', ['robot_type'], schema='vlaapi')
    op.create_index('idx_robot_metrics_date', 'robot_performance_metrics', [sa.text('aggregation_date DESC')], schema='vlaapi')
    op.create_index('idx_robot_metrics_robot_model', 'robot_performance_metrics', ['robot_type', 'model_name'], schema='vlaapi')
    op.create_index('idx_robot_metrics_customer_robot_date', 'robot_performance_metrics', ['customer_id', 'robot_type', 'aggregation_date'], unique=True, schema='vlaapi')

    # ========================================================================
    # 5. Create instruction_analytics table
    # ========================================================================
    op.create_table(
        'instruction_analytics',
        sa.Column('analytics_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('instruction_hash', sa.String(length=64), nullable=False),
        sa.Column('instruction_text', sa.Text(), nullable=False),
        sa.Column('instruction_category', sa.String(length=50), nullable=False),
        sa.Column('total_uses', sa.Integer(), nullable=False),
        sa.Column('unique_customers', sa.Integer(), nullable=False),
        sa.Column('success_rate', sa.Float(), nullable=False),
        sa.Column('avg_latency_ms', sa.Float(), nullable=False),
        sa.Column('avg_safety_score', sa.Float(), nullable=False),
        sa.Column('robot_type_distribution', postgresql.JSONB(), nullable=False),
        sa.Column('first_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('instruction_embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.CheckConstraint('total_uses > 0', name='chk_total_uses_positive'),
        sa.CheckConstraint('unique_customers > 0', name='chk_unique_customers_positive'),
        sa.CheckConstraint('success_rate >= 0.0 AND success_rate <= 1.0', name='chk_instruction_success_rate_range'),
        sa.CheckConstraint('first_seen <= last_seen', name='chk_temporal_consistency'),
        sa.PrimaryKeyConstraint('analytics_id'),
        sa.UniqueConstraint('instruction_hash'),
        schema='vlaapi'
    )

    # Indexes for instruction_analytics
    op.create_index('idx_instruction_analytics_hash', 'instruction_analytics', ['instruction_hash'], unique=True, schema='vlaapi')
    op.create_index('idx_instruction_analytics_category', 'instruction_analytics', ['instruction_category'], schema='vlaapi')
    op.create_index('idx_instruction_analytics_uses', 'instruction_analytics', [sa.text('total_uses DESC')], schema='vlaapi')
    op.create_index('idx_instruction_analytics_last_seen', 'instruction_analytics', [sa.text('last_seen DESC')], schema='vlaapi')

    # Vector similarity index (IVFFlat for better performance)
    op.execute("""
        CREATE INDEX idx_instruction_analytics_embedding ON vlaapi.instruction_analytics
        USING ivfflat (instruction_embedding vector_cosine_ops)
        WITH (lists = 100)
        WHERE instruction_embedding IS NOT NULL
    """)

    # ========================================================================
    # 6. Create context_metadata table
    # ========================================================================
    op.create_table(
        'context_metadata',
        sa.Column('context_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('log_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('environment_type', sa.String(length=50), nullable=False),
        sa.Column('lighting_condition', sa.String(length=50), nullable=True),
        sa.Column('object_count', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('image_embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('additional_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "environment_type IN ('lab', 'warehouse', 'factory', 'outdoor', 'home', 'office', 'hospital', 'retail', 'other')",
            name='chk_context_environment_type'
        ),
        sa.ForeignKeyConstraint(['log_id'], ['vlaapi.inference_logs.log_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['customer_id'], ['vlaapi.customers.customer_id']),
        sa.PrimaryKeyConstraint('context_id'),
        sa.UniqueConstraint('log_id'),
        schema='vlaapi'
    )

    # Indexes for context_metadata
    op.create_index('idx_context_metadata_log', 'context_metadata', ['log_id'], unique=True, schema='vlaapi')
    op.create_index('idx_context_metadata_customer', 'context_metadata', ['customer_id'], schema='vlaapi')
    op.create_index('idx_context_metadata_environment', 'context_metadata', ['environment_type'], schema='vlaapi')

    # Vector similarity index for image embeddings
    op.execute("""
        CREATE INDEX idx_context_metadata_embedding ON vlaapi.context_metadata
        USING ivfflat (image_embedding vector_cosine_ops)
        WITH (lists = 100)
        WHERE image_embedding IS NOT NULL
    """)

    # ========================================================================
    # 7. Create customer_data_consent table
    # ========================================================================
    op.create_table(
        'customer_data_consent',
        sa.Column('consent_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('consent_tier', sa.String(length=20), nullable=False),
        sa.Column('consent_version', sa.Integer(), nullable=False),
        sa.Column('consented_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('can_store_images', sa.Boolean(), nullable=False),
        sa.Column('can_store_embeddings', sa.Boolean(), nullable=False),
        sa.Column('can_use_for_training', sa.Boolean(), nullable=False),
        sa.Column('anonymization_level', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("consent_tier IN ('none', 'metadata', 'full')", name='chk_consent_tier'),
        sa.CheckConstraint("anonymization_level IN ('none', 'partial', 'full')", name='chk_anonymization_level'),
        sa.CheckConstraint('consent_version >= 1', name='chk_consent_version_positive'),
        sa.CheckConstraint('expires_at IS NULL OR expires_at > consented_at', name='chk_expiration'),
        sa.CheckConstraint(
            "consent_tier != 'none' OR (can_store_images = false AND can_store_embeddings = false AND can_use_for_training = false)",
            name='chk_none_tier'
        ),
        sa.CheckConstraint(
            "consent_tier != 'metadata' OR (can_store_images = false AND can_store_embeddings = true AND can_use_for_training = true)",
            name='chk_metadata_tier'
        ),
        sa.CheckConstraint(
            "consent_tier != 'full' OR (can_store_images = true AND can_store_embeddings = true AND can_use_for_training = true)",
            name='chk_full_tier'
        ),
        sa.CheckConstraint(
            'can_store_images = false OR anonymization_level != \'none\'',
            name='chk_anonymization'
        ),
        sa.ForeignKeyConstraint(['customer_id'], ['vlaapi.customers.customer_id']),
        sa.PrimaryKeyConstraint('consent_id'),
        sa.UniqueConstraint('customer_id'),
        schema='vlaapi'
    )

    # Indexes for customer_data_consent
    op.create_index('idx_consent_customer', 'customer_data_consent', ['customer_id'], unique=True, schema='vlaapi')
    op.create_index('idx_consent_tier', 'customer_data_consent', ['consent_tier'], schema='vlaapi')
    op.create_index(
        'idx_consent_expires',
        'customer_data_consent',
        ['expires_at'],
        postgresql_where=sa.text('expires_at IS NOT NULL'),
        schema='vlaapi'
    )

    # ========================================================================
    # 8. Update feedback table with additional constraints
    # ========================================================================
    # Add constraints to feedback table
    op.create_check_constraint(
        'chk_rating_required',
        'feedback',
        "(feedback_type NOT IN ('success_rating', 'safety_rating')) OR (rating IS NOT NULL)",
        schema='vlaapi'
    )
    op.create_check_constraint(
        'chk_corrected_action_required',
        'feedback',
        "feedback_type != 'action_correction' OR corrected_action IS NOT NULL",
        schema='vlaapi'
    )
    op.create_check_constraint(
        'chk_failure_reason_required',
        'feedback',
        "feedback_type != 'failure_report' OR failure_reason IS NOT NULL",
        schema='vlaapi'
    )

    # Add partial index for ratings
    op.create_index(
        'idx_feedback_rating',
        'feedback',
        ['rating'],
        postgresql_where=sa.text('rating IS NOT NULL'),
        schema='vlaapi'
    )

    # ========================================================================
    # 9. Create materialized views for reporting
    # ========================================================================

    # Daily usage summary per customer
    op.execute("""
        CREATE MATERIALIZED VIEW vlaapi.daily_usage_summary AS
        SELECT
            customer_id,
            DATE(timestamp) as usage_date,
            robot_type,
            model_name,
            COUNT(*) as total_requests,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_requests,
            AVG(inference_latency_ms) as avg_latency_ms,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY inference_latency_ms) as p50_latency_ms,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY inference_latency_ms) as p95_latency_ms,
            AVG(safety_score) as avg_safety_score,
            COUNT(DISTINCT instruction_category) as unique_instruction_categories
        FROM vlaapi.inference_logs
        WHERE timestamp >= CURRENT_DATE - INTERVAL '90 days'
        GROUP BY customer_id, DATE(timestamp), robot_type, model_name
        WITH DATA
    """)

    # Create index on materialized view
    op.create_index('idx_daily_usage_customer_date', 'daily_usage_summary', ['customer_id', 'usage_date'], schema='vlaapi')

    # Monthly billing summary
    op.execute("""
        CREATE MATERIALIZED VIEW vlaapi.monthly_billing_summary AS
        SELECT
            customer_id,
            DATE_TRUNC('month', timestamp) as billing_month,
            COUNT(*) as total_requests,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as billable_requests,
            COUNT(DISTINCT robot_type) as unique_robots,
            COUNT(DISTINCT model_name) as unique_models
        FROM vlaapi.inference_logs
        WHERE timestamp >= CURRENT_DATE - INTERVAL '13 months'
        GROUP BY customer_id, DATE_TRUNC('month', timestamp)
        WITH DATA
    """)

    # Create index on monthly billing view
    op.create_index('idx_monthly_billing_customer_month', 'monthly_billing_summary', ['customer_id', 'billing_month'], schema='vlaapi')

    # Safety trend summary
    op.execute("""
        CREATE MATERIALIZED VIEW vlaapi.safety_trend_summary AS
        SELECT
            customer_id,
            robot_type,
            environment_type,
            DATE(timestamp) as incident_date,
            severity,
            COUNT(*) as incident_count,
            COUNT(DISTINCT violation_type) as unique_violation_types
        FROM vlaapi.safety_incidents
        WHERE timestamp >= CURRENT_DATE - INTERVAL '90 days'
        GROUP BY customer_id, robot_type, environment_type, DATE(timestamp), severity
        WITH DATA
    """)

    # Create index on safety trend view
    op.create_index('idx_safety_trend_customer_date', 'safety_trend_summary', ['customer_id', 'incident_date'], schema='vlaapi')
    op.create_index('idx_safety_trend_robot_severity', 'safety_trend_summary', ['robot_type', 'severity'], schema='vlaapi')

    # ========================================================================
    # 10. Create refresh functions for materialized views
    # ========================================================================

    op.execute("""
        CREATE OR REPLACE FUNCTION vlaapi.refresh_materialized_views()
        RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY vlaapi.daily_usage_summary;
            REFRESH MATERIALIZED VIEW CONCURRENTLY vlaapi.monthly_billing_summary;
            REFRESH MATERIALIZED VIEW CONCURRENTLY vlaapi.safety_trend_summary;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create a function to schedule nightly refreshes (requires pg_cron extension)
    op.execute("""
        COMMENT ON FUNCTION vlaapi.refresh_materialized_views() IS
        'Refresh all materialized views. Schedule with pg_cron:
        SELECT cron.schedule(''refresh-analytics'', ''0 2 * * *'', ''SELECT vlaapi.refresh_materialized_views()'');';
    """)


def downgrade() -> None:
    """Downgrade database schema."""

    # Drop materialized views
    op.execute("DROP MATERIALIZED VIEW IF EXISTS vlaapi.safety_trend_summary CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS vlaapi.monthly_billing_summary CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS vlaapi.daily_usage_summary CASCADE")
    op.execute("DROP FUNCTION IF EXISTS vlaapi.refresh_materialized_views() CASCADE")

    # Drop feedback constraints
    op.drop_constraint('chk_failure_reason_required', 'feedback', schema='vlaapi', type_='check')
    op.drop_constraint('chk_corrected_action_required', 'feedback', schema='vlaapi', type_='check')
    op.drop_constraint('chk_rating_required', 'feedback', schema='vlaapi', type_='check')
    op.drop_index('idx_feedback_rating', table_name='feedback', schema='vlaapi')

    # Drop new tables
    op.drop_table('customer_data_consent', schema='vlaapi')
    op.drop_table('context_metadata', schema='vlaapi')
    op.drop_table('instruction_analytics', schema='vlaapi')
    op.drop_table('robot_performance_metrics', schema='vlaapi')

    # Remove safety_incidents extensions
    op.drop_index('idx_incidents_robot_severity', table_name='safety_incidents', schema='vlaapi')
    op.drop_index('idx_incidents_category', table_name='safety_incidents', schema='vlaapi')
    op.drop_index('idx_incidents_environment', table_name='safety_incidents', schema='vlaapi')
    op.drop_index('idx_incidents_robot_type', table_name='safety_incidents', schema='vlaapi')
    op.drop_constraint('chk_critical_action', 'safety_incidents', schema='vlaapi', type_='check')
    op.drop_constraint('chk_collision_severity', 'safety_incidents', schema='vlaapi', type_='check')
    op.drop_constraint('chk_incident_instruction_category', 'safety_incidents', schema='vlaapi', type_='check')
    op.drop_constraint('chk_environment_type', 'safety_incidents', schema='vlaapi', type_='check')
    op.drop_column('safety_incidents', 'instruction_category', schema='vlaapi')
    op.drop_column('safety_incidents', 'environment_type', schema='vlaapi')
    op.drop_column('safety_incidents', 'robot_type', schema='vlaapi')

    # Remove inference_logs extensions
    op.drop_index('idx_logs_customer_robot_timestamp', table_name='inference_logs', schema='vlaapi')
    op.drop_constraint('chk_instruction_category', 'inference_logs', schema='vlaapi', type_='check')
    op.drop_column('inference_logs', 'action_magnitude', schema='vlaapi')
    op.drop_column('inference_logs', 'instruction_category', schema='vlaapi')
    op.drop_column('inference_logs', 'robot_type', schema='vlaapi')

    # Drop pgvector extension (optional - comment out if other tables use it)
    # op.execute("DROP EXTENSION IF EXISTS vector")
