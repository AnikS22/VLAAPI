-- Migration: Add model catalog and version management tables
-- Version: 010
-- Description: Support multi-model serving, version management, and A/B testing

-- ============================================================================
-- Model Catalog Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS model_catalog (
    model_id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    version VARCHAR(20) NOT NULL,
    architecture VARCHAR(50) NOT NULL,

    -- HuggingFace identifiers
    hf_model_id VARCHAR(200) NOT NULL,
    hf_processor_id VARCHAR(200),

    -- Hardware requirements
    size_gb FLOAT NOT NULL,
    min_vram_gb FLOAT NOT NULL,
    recommended_vram_gb FLOAT NOT NULL,
    supports_fp16 BOOLEAN DEFAULT TRUE,
    supports_bf16 BOOLEAN DEFAULT TRUE,
    supports_4bit BOOLEAN DEFAULT FALSE,
    supports_8bit BOOLEAN DEFAULT FALSE,

    -- Performance expectations
    expected_latency_p50_ms FLOAT NOT NULL,
    expected_latency_p95_ms FLOAT NOT NULL,
    expected_throughput_rps FLOAT NOT NULL,

    -- Cost
    cost_per_1k FLOAT NOT NULL DEFAULT 0.001,

    -- Capabilities
    supported_robots TEXT[] NOT NULL,
    max_image_size_h INTEGER NOT NULL DEFAULT 224,
    max_image_size_w INTEGER NOT NULL DEFAULT 224,
    action_dim INTEGER NOT NULL DEFAULT 7,

    -- Training info
    training_datasets TEXT[],
    accuracy_benchmark FLOAT,

    -- Availability
    status VARCHAR(20) NOT NULL DEFAULT 'production',
    release_date DATE,
    deprecation_date DATE,

    -- Additional config (JSON)
    config JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_model_catalog_status ON model_catalog(status);
CREATE INDEX idx_model_catalog_architecture ON model_catalog(architecture);
CREATE INDEX idx_model_catalog_release_date ON model_catalog(release_date DESC);

-- ============================================================================
-- Model Deployments Table (for versioning and traffic splitting)
-- ============================================================================
CREATE TABLE IF NOT EXISTS model_deployments (
    deployment_id VARCHAR(150) PRIMARY KEY,
    model_id VARCHAR(100) NOT NULL REFERENCES model_catalog(model_id) ON DELETE CASCADE,
    version VARCHAR(20) NOT NULL,

    -- Traffic management
    traffic_weight FLOAT NOT NULL DEFAULT 0.0 CHECK (traffic_weight >= 0.0 AND traffic_weight <= 1.0),
    status VARCHAR(20) NOT NULL DEFAULT 'canary',

    -- Performance metrics (updated from inference logs)
    total_inferences INTEGER DEFAULT 0,
    avg_latency_ms FLOAT DEFAULT 0.0,
    success_rate FLOAT DEFAULT 0.0,
    avg_safety_score FLOAT DEFAULT 0.0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Unique constraint: one deployment per model+version combination
    UNIQUE(model_id, version)
);

-- Indexes
CREATE INDEX idx_deployments_model ON model_deployments(model_id);
CREATE INDEX idx_deployments_status ON model_deployments(status);
CREATE INDEX idx_deployments_traffic ON model_deployments(traffic_weight DESC);

-- ============================================================================
-- A/B Test Cohorts Table (customer assignment)
-- ============================================================================
CREATE TABLE IF NOT EXISTS ab_test_cohorts (
    customer_id UUID NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    model_id VARCHAR(100) NOT NULL,
    assigned_version VARCHAR(20) NOT NULL,
    cohort_name VARCHAR(50) NOT NULL,
    assigned_at TIMESTAMP DEFAULT NOW(),

    -- Metadata
    assignment_reason VARCHAR(100),  -- 'traffic_split', 'manual_assignment', etc.
    locked BOOLEAN DEFAULT FALSE,    -- If true, customer stays in this cohort

    PRIMARY KEY (customer_id, model_id)
);

-- Indexes
CREATE INDEX idx_cohorts_model ON ab_test_cohorts(model_id);
CREATE INDEX idx_cohorts_version ON ab_test_cohorts(assigned_version);
CREATE INDEX idx_cohorts_cohort_name ON ab_test_cohorts(cohort_name);

-- ============================================================================
-- Model Performance Metrics Table (aggregated stats)
-- ============================================================================
CREATE TABLE IF NOT EXISTS model_performance_metrics (
    metric_id SERIAL PRIMARY KEY,
    model_id VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL,

    -- Time window
    date DATE NOT NULL,
    hour INTEGER,  -- NULL for daily aggregates, 0-23 for hourly

    -- Metrics
    inference_count INTEGER NOT NULL DEFAULT 0,
    total_latency_ms BIGINT NOT NULL DEFAULT 0,
    avg_latency_ms FLOAT,
    p50_latency_ms FLOAT,
    p95_latency_ms FLOAT,
    p99_latency_ms FLOAT,

    -- Success metrics
    success_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    success_rate FLOAT,

    -- Safety metrics
    total_safety_score FLOAT NOT NULL DEFAULT 0.0,
    avg_safety_score FLOAT,
    safety_incidents INTEGER DEFAULT 0,

    -- GPU metrics
    avg_gpu_utilization FLOAT,
    avg_vram_usage_gb FLOAT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Unique constraint for time windows
    UNIQUE(model_id, version, date, hour)
);

-- Indexes
CREATE INDEX idx_perf_model_version ON model_performance_metrics(model_id, version);
CREATE INDEX idx_perf_date ON model_performance_metrics(date DESC);
CREATE INDEX idx_perf_model_date ON model_performance_metrics(model_id, date DESC);

-- ============================================================================
-- Rollout Plans Table (for gradual deployments)
-- ============================================================================
CREATE TABLE IF NOT EXISTS rollout_plans (
    plan_id UUID PRIMARY KEY,
    model_id VARCHAR(100) NOT NULL,
    current_version VARCHAR(20) NOT NULL,
    new_version VARCHAR(20) NOT NULL,

    -- Strategy
    strategy VARCHAR(20) NOT NULL,  -- 'conservative', 'moderate', 'aggressive'
    stages JSONB NOT NULL,  -- Array of stages: [{"traffic": 0.1, "duration_hours": 24}, ...]

    -- Rollback thresholds
    rollback_threshold JSONB NOT NULL,

    -- Status
    current_stage INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'in_progress', 'completed', 'rolled_back'

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Notes
    created_by UUID REFERENCES users(user_id),
    notes TEXT
);

-- Indexes
CREATE INDEX idx_rollout_model ON rollout_plans(model_id);
CREATE INDEX idx_rollout_status ON rollout_plans(status);
CREATE INDEX idx_rollout_created ON rollout_plans(created_at DESC);

-- ============================================================================
-- Update trigger for model_deployments
-- ============================================================================
CREATE OR REPLACE FUNCTION update_deployment_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_deployment_timestamp
BEFORE UPDATE ON model_deployments
FOR EACH ROW
EXECUTE FUNCTION update_deployment_timestamp();

-- ============================================================================
-- Insert default models from registry
-- ============================================================================

-- OpenVLA 7B v1
INSERT INTO model_catalog (
    model_id, name, version, architecture,
    hf_model_id, size_gb, min_vram_gb, recommended_vram_gb,
    expected_latency_p50_ms, expected_latency_p95_ms, expected_throughput_rps,
    cost_per_1k, supported_robots, training_datasets,
    accuracy_benchmark, status, release_date
) VALUES (
    'openvla-7b-v1', 'OpenVLA 7B', '1.0.0', 'prismatic',
    'openvla/openvla-7b-prismatic', 14.0, 16.0, 20.0,
    120.0, 250.0, 8.0,
    0.001, ARRAY['franka_panda', 'franka_fr3', 'universal_robots_ur5e', 'kinova_gen3', 'abb_yumi'],
    ARRAY['bridge_v2', 'fractal'],
    0.85, 'production', '2024-01-15'
) ON CONFLICT (model_id) DO NOTHING;

-- OpenVLA 7B v2
INSERT INTO model_catalog (
    model_id, name, version, architecture,
    hf_model_id, size_gb, min_vram_gb, recommended_vram_gb,
    expected_latency_p50_ms, expected_latency_p95_ms, expected_throughput_rps,
    cost_per_1k, supported_robots, training_datasets,
    accuracy_benchmark, status, release_date
) VALUES (
    'openvla-7b-v2', 'OpenVLA 7B v2', '2.0.0', 'prismatic',
    'openvla/openvla-7b-v2', 14.0, 16.0, 20.0,
    110.0, 230.0, 9.0,
    0.0012, ARRAY['franka_panda', 'franka_fr3', 'universal_robots_ur5e', 'kinova_gen3', 'abb_yumi', 'kuka_iiwa7'],
    ARRAY['bridge_v2', 'fractal', 'oxe'],
    0.88, 'beta', '2024-09-01'
) ON CONFLICT (model_id) DO NOTHING;

-- RT-1
INSERT INTO model_catalog (
    model_id, name, version, architecture,
    hf_model_id, size_gb, min_vram_gb, recommended_vram_gb,
    expected_latency_p50_ms, expected_latency_p95_ms, expected_throughput_rps,
    cost_per_1k, supported_robots, training_datasets,
    accuracy_benchmark, status, release_date
) VALUES (
    'rt-1', 'RT-1 (Robotics Transformer 1)', '1.0.0', 'rt-1',
    'google/rt-1-x', 8.5, 12.0, 16.0,
    90.0, 180.0, 11.0,
    0.0008, ARRAY['franka_panda', 'universal_robots_ur5e', 'kinova_gen3'],
    ARRAY['rt-1'],
    0.82, 'production', '2023-06-15'
) ON CONFLICT (model_id) DO NOTHING;

-- RT-2 Base
INSERT INTO model_catalog (
    model_id, name, version, architecture,
    hf_model_id, size_gb, min_vram_gb, recommended_vram_gb,
    expected_latency_p50_ms, expected_latency_p95_ms, expected_throughput_rps,
    cost_per_1k, supported_robots, training_datasets,
    accuracy_benchmark, status, release_date,
    max_image_size_h, max_image_size_w
) VALUES (
    'rt-2-base', 'RT-2 Base', '1.0.0', 'rt-2',
    'google/rt-2-base', 18.0, 24.0, 32.0,
    150.0, 300.0, 6.0,
    0.0015, ARRAY['franka_panda', 'franka_fr3', 'universal_robots_ur5e', 'kinova_gen3', 'abb_yumi', 'kuka_iiwa7'],
    ARRAY['rt-1', 'rt-2'],
    0.90, 'production', '2023-12-01',
    320, 320
) ON CONFLICT (model_id) DO NOTHING;

-- Octo Base
INSERT INTO model_catalog (
    model_id, name, version, architecture,
    hf_model_id, size_gb, min_vram_gb, recommended_vram_gb,
    expected_latency_p50_ms, expected_latency_p95_ms, expected_throughput_rps,
    cost_per_1k, supported_robots, training_datasets,
    accuracy_benchmark, status, release_date,
    max_image_size_h, max_image_size_w
) VALUES (
    'octo-base', 'Octo Base', '1.0.0', 'octo',
    'octo-models/octo-base', 12.0, 16.0, 20.0,
    100.0, 200.0, 10.0,
    0.0009, ARRAY['franka_panda', 'universal_robots_ur5e', 'kinova_gen3', 'abb_yumi'],
    ARRAY['oxe'],
    0.87, 'production', '2024-03-15',
    256, 256
) ON CONFLICT (model_id) DO NOTHING;

-- Octo Small
INSERT INTO model_catalog (
    model_id, name, version, architecture,
    hf_model_id, size_gb, min_vram_gb, recommended_vram_gb,
    expected_latency_p50_ms, expected_latency_p95_ms, expected_throughput_rps,
    cost_per_1k, supported_robots, training_datasets,
    accuracy_benchmark, status, release_date,
    max_image_size_h, max_image_size_w
) VALUES (
    'octo-small', 'Octo Small', '1.0.0', 'octo',
    'octo-models/octo-small', 5.0, 8.0, 12.0,
    60.0, 120.0, 16.0,
    0.0005, ARRAY['franka_panda', 'universal_robots_ur5e', 'kinova_gen3'],
    ARRAY['oxe'],
    0.81, 'production', '2024-03-15',
    256, 256
) ON CONFLICT (model_id) DO NOTHING;

-- ============================================================================
-- Grant permissions
-- ============================================================================
GRANT SELECT, INSERT, UPDATE ON model_catalog TO vla_api_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON model_deployments TO vla_api_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ab_test_cohorts TO vla_api_user;
GRANT SELECT, INSERT, UPDATE ON model_performance_metrics TO vla_api_user;
GRANT SELECT, INSERT, UPDATE ON rollout_plans TO vla_api_user;
GRANT USAGE, SELECT ON SEQUENCE model_performance_metrics_metric_id_seq TO vla_api_user;
