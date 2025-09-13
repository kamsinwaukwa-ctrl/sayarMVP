-- Migration: Create payment provider configs table
-- This migration creates the table for storing encrypted payment provider credentials

CREATE TABLE payment_provider_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    provider_type VARCHAR(20) NOT NULL CHECK (provider_type IN ('paystack', 'korapay')),
    public_key_encrypted TEXT NOT NULL,
    secret_key_encrypted TEXT NOT NULL,
    webhook_secret_encrypted TEXT,
    environment VARCHAR(10) NOT NULL CHECK (environment IN ('test', 'live')) DEFAULT 'test',
    verification_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending', 'verifying', 'verified', 'failed')),
    last_verified_at TIMESTAMPTZ,
    verification_error TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure unique provider config per merchant per environment
    UNIQUE(merchant_id, provider_type, environment)
);

-- Create indexes for performance
CREATE INDEX idx_payment_provider_configs_merchant_id ON payment_provider_configs(merchant_id);
CREATE INDEX idx_payment_provider_configs_provider_status ON payment_provider_configs(provider_type, verification_status);
CREATE INDEX idx_payment_provider_configs_active ON payment_provider_configs(active);

-- Enable Row Level Security
ALTER TABLE payment_provider_configs ENABLE ROW LEVEL SECURITY;

-- Create RLS policy for multi-tenant isolation
CREATE POLICY payment_provider_configs_tenant_isolation ON payment_provider_configs
    USING (merchant_id = (current_setting('request.jwt.claims')::json->>'merchant_id')::uuid);

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON payment_provider_configs TO service_role;

-- Add trigger for updated_at
CREATE OR REPLACE FUNCTION update_payment_provider_configs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER payment_provider_configs_updated_at
    BEFORE UPDATE ON payment_provider_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_payment_provider_configs_updated_at();

-- Add comments for documentation
COMMENT ON TABLE payment_provider_configs IS 'Stores encrypted payment provider credentials per merchant';
COMMENT ON COLUMN payment_provider_configs.public_key_encrypted IS 'Fernet-encrypted public API key';
COMMENT ON COLUMN payment_provider_configs.secret_key_encrypted IS 'Fernet-encrypted secret API key';
COMMENT ON COLUMN payment_provider_configs.webhook_secret_encrypted IS 'Fernet-encrypted webhook secret';
COMMENT ON COLUMN payment_provider_configs.verification_status IS 'Credential verification status';