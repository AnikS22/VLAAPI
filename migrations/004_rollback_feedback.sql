-- Rollback migration for feedback table
-- Version: 003-rollback
-- Description: Removes feedback table and related objects

-- Drop materialized view and its index
DROP INDEX IF EXISTS vlaapi.idx_feedback_analytics_customer_date;
DROP MATERIALIZED VIEW IF EXISTS vlaapi.feedback_analytics;

-- Drop indexes
DROP INDEX IF EXISTS vlaapi.idx_feedback_timestamp;
DROP INDEX IF EXISTS vlaapi.idx_feedback_type;
DROP INDEX IF EXISTS vlaapi.idx_feedback_log;
DROP INDEX IF EXISTS vlaapi.idx_feedback_customer;

-- Drop table
DROP TABLE IF EXISTS vlaapi.feedback CASCADE;
