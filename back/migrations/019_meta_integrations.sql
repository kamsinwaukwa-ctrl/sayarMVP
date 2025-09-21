-- Meta integration credentials (encrypted storage)
CREATE TABLE meta_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,

    -- Meta Commerce Catalog credentials (encrypted)
    catalog_id VARCHAR(255) NOT NULL,
    system_user_token_encrypted TEXT NOT NULL,
    app_id VARCHAR(255) NOT NULL,
    waba_id VARCHAR(255), -- optional for some setups

    -- Verification status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'verified', 'invalid', 'expired')),
    catalog_name VARCHAR(255),
    last_verified_at TIMESTAMPTZ,
    last_error TEXT,
    error_code VARCHAR(100),

    -- Audit fields
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Ensure one integration per merchant
    UNIQUE(merchant_id)
);

-- Indexes for efficient lookups
CREATE INDEX idx_meta_integrations_merchant ON meta_integrations(merchant_id);
CREATE INDEX idx_meta_integrations_status ON meta_integrations(merchant_id, status);

-- Updated trigger for timestamp management
CREATE TRIGGER set_meta_integrations_updated_at
    BEFORE UPDATE ON meta_integrations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security for multi-tenant isolation
ALTER TABLE meta_integrations ENABLE ROW LEVEL SECURITY;

-- Merchants can only access their own integrations
CREATE POLICY meta_integrations_tenant_isolation
    ON meta_integrations
    USING (merchant_id::text = auth.jwt() ->> 'merchant_id');

-- Admin can read/write, staff can read only
CREATE POLICY meta_integrations_admin_full
    ON meta_integrations
    FOR ALL
    TO authenticated
    USING (
        merchant_id::text = auth.jwt() ->> 'merchant_id'
        AND auth.jwt() ->> 'role' = 'admin'
    );

CREATE POLICY meta_integrations_staff_read
    ON meta_integrations
    FOR SELECT
    TO authenticated
    USING (
        merchant_id::text = auth.jwt() ->> 'merchant_id'
        AND auth.jwt() ->> 'role' IN ('admin', 'staff')
    );

-- Comments for documentation
COMMENT ON TABLE meta_integrations IS 'Per-merchant Meta Commerce Catalog integration credentials and status';
COMMENT ON COLUMN meta_integrations.system_user_token_encrypted IS 'Fernet-encrypted system user token for Meta Graph API';
COMMENT ON COLUMN meta_integrations.waba_id IS 'WhatsApp Business Account ID (optional, for future webhook routing)';