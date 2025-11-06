-- Migration: Add feedback table for ground truth collection
-- Version: 003
-- Description: Creates feedback table for collecting user feedback on inference results

-- Create feedback table
CREATE TABLE IF NOT EXISTS vlaapi.feedback (
    feedback_id SERIAL PRIMARY KEY,
    log_id INTEGER NOT NULL REFERENCES vlaapi.inference_logs(log_id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES vlaapi.customers(customer_id) ON DELETE CASCADE,

    -- Feedback metadata
    feedback_type VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Rating fields (for success_rating and safety_rating)
    rating INTEGER,

    -- Action correction fields
    corrected_action FLOAT[],
    original_action FLOAT[],
    correction_delta FLOAT[],
    correction_magnitude FLOAT,

    -- Failure report fields
    failure_reason VARCHAR(200),

    -- General notes
    notes TEXT,

    -- Constraints
    CONSTRAINT chk_feedback_type CHECK (
        feedback_type IN ('success_rating', 'safety_rating', 'action_correction', 'failure_report')
    ),
    CONSTRAINT chk_rating_range CHECK (
        rating IS NULL OR (rating >= 1 AND rating <= 5)
    )
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_feedback_customer ON vlaapi.feedback(customer_id);
CREATE INDEX IF NOT EXISTS idx_feedback_log ON vlaapi.feedback(log_id);
CREATE INDEX IF NOT EXISTS idx_feedback_type ON vlaapi.feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON vlaapi.feedback USING btree (timestamp DESC);

-- Add comments for documentation
COMMENT ON TABLE vlaapi.feedback IS 'Feedback records for ground truth collection and model improvement';
COMMENT ON COLUMN vlaapi.feedback.feedback_type IS 'Type of feedback: success_rating, safety_rating, action_correction, failure_report';
COMMENT ON COLUMN vlaapi.feedback.rating IS 'User rating (1-5 stars) for success or safety';
COMMENT ON COLUMN vlaapi.feedback.corrected_action IS 'Human-corrected 7-DoF action vector for supervised learning';
COMMENT ON COLUMN vlaapi.feedback.correction_magnitude IS 'L2 norm of correction delta (measure of correction size)';
COMMENT ON COLUMN vlaapi.feedback.failure_reason IS 'Brief reason why inference failed in real execution';

-- Create materialized view for feedback analytics (refreshed periodically)
CREATE MATERIALIZED VIEW IF NOT EXISTS vlaapi.feedback_analytics AS
SELECT
    customer_id,
    DATE_TRUNC('day', timestamp) as date,
    COUNT(*) as total_feedback,
    COUNT(*) FILTER (WHERE feedback_type = 'success_rating') as success_ratings_count,
    COUNT(*) FILTER (WHERE feedback_type = 'safety_rating') as safety_ratings_count,
    COUNT(*) FILTER (WHERE feedback_type = 'action_correction') as corrections_count,
    COUNT(*) FILTER (WHERE feedback_type = 'failure_report') as failures_count,
    AVG(rating) FILTER (WHERE feedback_type = 'success_rating') as avg_success_rating,
    AVG(rating) FILTER (WHERE feedback_type = 'safety_rating') as avg_safety_rating,
    AVG(correction_magnitude) as avg_correction_magnitude
FROM vlaapi.feedback
GROUP BY customer_id, DATE_TRUNC('day', timestamp);

-- Create index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_feedback_analytics_customer_date
ON vlaapi.feedback_analytics(customer_id, date);

COMMENT ON MATERIALIZED VIEW vlaapi.feedback_analytics IS 'Daily aggregated feedback statistics per customer';

-- Grant permissions (adjust as needed for your user)
-- GRANT SELECT, INSERT, UPDATE ON vlaapi.feedback TO app_user;
-- GRANT SELECT ON vlaapi.feedback_analytics TO app_user;
