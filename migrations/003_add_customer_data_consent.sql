-- Migration: Add customer data consent table for privacy compliance
-- Version: 003
-- Description: Adds customer_data_consent table to track customer data usage preferences

-- Create customer_data_consent table
CREATE TABLE IF NOT EXISTS vlaapi.customer_data_consent (
    consent_id SERIAL PRIMARY KEY,
    customer_id UUID NOT NULL UNIQUE REFERENCES vlaapi.customers(customer_id) ON DELETE CASCADE,

    -- Consent tier and permissions
    consent_tier VARCHAR(20) NOT NULL DEFAULT 'none' CHECK (consent_tier IN ('none', 'basic', 'analytics', 'research')),
    can_store_images BOOLEAN NOT NULL DEFAULT FALSE,
    can_store_embeddings BOOLEAN NOT NULL DEFAULT FALSE,
    can_use_for_training BOOLEAN NOT NULL DEFAULT FALSE,

    -- Anonymization settings
    anonymization_level VARCHAR(20) NOT NULL DEFAULT 'full' CHECK (anonymization_level IN ('full', 'partial', 'minimal', 'none')),

    -- Timestamps
    consent_granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    consent_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NULL,  -- NULL = never expires

    -- Indexes
    CONSTRAINT chk_consent_tier CHECK (consent_tier IN ('none', 'basic', 'analytics', 'research')),
    CONSTRAINT chk_anonymization_level CHECK (anonymization_level IN ('full', 'partial', 'minimal', 'none'))
);

-- Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_consent_customer ON vlaapi.customer_data_consent(customer_id);
CREATE INDEX IF NOT EXISTS idx_consent_tier ON vlaapi.customer_data_consent(consent_tier);

-- Create trigger to update consent_updated_at timestamp
CREATE OR REPLACE FUNCTION vlaapi.update_consent_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.consent_updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_consent_timestamp
    BEFORE UPDATE ON vlaapi.customer_data_consent
    FOR EACH ROW
    EXECUTE FUNCTION vlaapi.update_consent_updated_at();

-- Create audit log table for consent changes
CREATE TABLE IF NOT EXISTS vlaapi.customer_consent_audit (
    audit_id SERIAL PRIMARY KEY,
    customer_id UUID NOT NULL REFERENCES vlaapi.customers(customer_id) ON DELETE CASCADE,

    -- Change details
    previous_tier VARCHAR(20) NOT NULL,
    new_tier VARCHAR(20) NOT NULL,
    changed_by VARCHAR(255) NOT NULL,  -- User/admin who made the change
    change_reason TEXT NULL,

    -- Metadata
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address INET NULL,
    user_agent TEXT NULL,

    -- Indexes
    CONSTRAINT chk_previous_tier CHECK (previous_tier IN ('none', 'basic', 'analytics', 'research')),
    CONSTRAINT chk_new_tier CHECK (new_tier IN ('none', 'basic', 'analytics', 'research'))
);

-- Create indexes for audit log
CREATE INDEX IF NOT EXISTS idx_consent_audit_customer ON vlaapi.customer_consent_audit(customer_id);
CREATE INDEX IF NOT EXISTS idx_consent_audit_timestamp ON vlaapi.customer_consent_audit(timestamp DESC);

-- Add comment for documentation
COMMENT ON TABLE vlaapi.customer_data_consent IS
'Tracks customer data consent preferences for privacy compliance (GDPR, CCPA, etc.)';

COMMENT ON COLUMN vlaapi.customer_data_consent.consent_tier IS
'Consent tier: none (no storage), basic (operational only), analytics (service improvement), research (ML training)';

COMMENT ON COLUMN vlaapi.customer_data_consent.anonymization_level IS
'Level of data anonymization: full (complete), partial (pseudonymized), minimal (basic PII removal), none';

COMMENT ON TABLE vlaapi.customer_consent_audit IS
'Audit log for customer consent changes to ensure compliance and traceability';

-- Insert default consent (none) for existing customers
INSERT INTO vlaapi.customer_data_consent (customer_id, consent_tier, can_store_images, can_store_embeddings, can_use_for_training, anonymization_level)
SELECT
    customer_id,
    'none',
    FALSE,
    FALSE,
    FALSE,
    'full'
FROM vlaapi.customers
WHERE customer_id NOT IN (SELECT customer_id FROM vlaapi.customer_data_consent)
ON CONFLICT (customer_id) DO NOTHING;

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON vlaapi.customer_data_consent TO vlaapi_app;
GRANT SELECT, INSERT ON vlaapi.customer_consent_audit TO vlaapi_app;
GRANT USAGE, SELECT ON SEQUENCE vlaapi.customer_data_consent_consent_id_seq TO vlaapi_app;
GRANT USAGE, SELECT ON SEQUENCE vlaapi.customer_consent_audit_audit_id_seq TO vlaapi_app;
