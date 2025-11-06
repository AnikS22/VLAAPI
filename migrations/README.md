# Database Migrations

This directory contains SQL migration scripts for the VLA Inference API database schema.

## Migration Files

### 001_initial_schema.sql
- Initial database schema with customers, API keys, inference logs, safety incidents, and feedback tables
- Includes indexes, constraints, and partitioning setup

### 002_add_feedback_system.sql
- Enhanced feedback system for ground truth collection
- Action correction tracking for continuous learning

### 003_add_customer_data_consent.sql
- Customer data consent management for privacy compliance
- Supports GDPR, CCPA, and other privacy regulations
- Includes audit logging for consent changes

## Running Migrations

Migrations should be applied in order using PostgreSQL:

```bash
# Connect to database
psql -U vlaapi -d vlaapi

# Apply migrations in order
\i migrations/001_initial_schema.sql
\i migrations/002_add_feedback_system.sql
\i migrations/003_add_customer_data_consent.sql
```

Or using the migration script (if available):

```bash
# Apply all pending migrations
python scripts/migrate.py up

# Rollback last migration
python scripts/migrate.py down
```

## Best Practices

1. **Always backup** the database before running migrations
2. **Test migrations** in a staging environment first
3. **Run migrations** during maintenance windows for production
4. **Version control** all migration files
5. **Never modify** existing migration files after they've been applied

## Consent System Usage

The consent system (migration 003) provides:

- **Consent tiers**: none, basic, analytics, research
- **Data permissions**: images, embeddings, training data
- **Anonymization levels**: full, partial, minimal, none
- **Audit logging**: Track all consent changes

Example consent queries:

```sql
-- Set customer consent to analytics tier
INSERT INTO vlaapi.customer_data_consent (customer_id, consent_tier, can_store_embeddings, anonymization_level)
VALUES ('customer-uuid', 'analytics', TRUE, 'full')
ON CONFLICT (customer_id)
DO UPDATE SET
    consent_tier = EXCLUDED.consent_tier,
    can_store_embeddings = EXCLUDED.can_store_embeddings,
    anonymization_level = EXCLUDED.anonymization_level,
    consent_updated_at = NOW();

-- Check customer consent
SELECT * FROM vlaapi.customer_data_consent WHERE customer_id = 'customer-uuid';

-- View consent audit trail
SELECT * FROM vlaapi.customer_consent_audit
WHERE customer_id = 'customer-uuid'
ORDER BY timestamp DESC;
```
