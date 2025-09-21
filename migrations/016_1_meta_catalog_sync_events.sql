-- Migration 016.1: Meta Catalog Sync Events
-- Extends products table and creates meta_catalog_sync_log for tracking image sync events

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Add catalog sync tracking to products table
ALTER TABLE products ADD COLUMN IF NOT EXISTS meta_image_sync_version INTEGER DEFAULT 0;
ALTER TABLE products ADD COLUMN IF NOT EXISTS meta_last_image_sync_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_products_meta_image_sync ON products(meta_image_sync_version, meta_last_image_sync_at);

-- Add catalog sync status tracking table
CREATE TABLE IF NOT EXISTS meta_catalog_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    outbox_job_id UUID REFERENCES outbox_events(id) ON DELETE SET NULL,
    action TEXT NOT NULL CHECK (action IN ('create', 'update', 'update_image', 'delete')),
    retailer_id TEXT NOT NULL,
    catalog_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'success', 'failed', 'rate_limited')),
    request_payload JSONB,
    response_data JSONB,
    error_details JSONB,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TIMESTAMPTZ,
    idempotency_key TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for sync log performance
CREATE INDEX idx_meta_catalog_sync_merchant ON meta_catalog_sync_log(merchant_id);
CREATE INDEX idx_meta_catalog_sync_product ON meta_catalog_sync_log(product_id);
CREATE INDEX idx_meta_catalog_sync_status ON meta_catalog_sync_log(status, next_retry_at);
CREATE INDEX idx_meta_catalog_sync_idempotency ON meta_catalog_sync_log(idempotency_key);
CREATE INDEX idx_meta_catalog_sync_outbox ON meta_catalog_sync_log(outbox_job_id);
CREATE INDEX idx_meta_catalog_sync_action ON meta_catalog_sync_log(action, created_at);

-- RLS Policy for sync log
ALTER TABLE meta_catalog_sync_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Merchants can manage their own catalog sync logs" ON meta_catalog_sync_log
    FOR ALL USING (merchant_id::text = auth.jwt() ->> 'merchant_id');

-- Update trigger for meta_catalog_sync_log (reuse existing function)
CREATE TRIGGER update_meta_catalog_sync_log_updated_at
    BEFORE UPDATE ON meta_catalog_sync_log
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE meta_catalog_sync_log IS 'Tracks Meta Catalog synchronization events for product images';
COMMENT ON COLUMN meta_catalog_sync_log.action IS 'Type of sync action: create, update, update_image, delete';
COMMENT ON COLUMN meta_catalog_sync_log.retailer_id IS 'Stable product identifier for Meta Catalog';
COMMENT ON COLUMN meta_catalog_sync_log.catalog_id IS 'Meta Catalog ID from merchant configuration';
COMMENT ON COLUMN meta_catalog_sync_log.status IS 'Sync status: pending, success, failed, rate_limited';
COMMENT ON COLUMN meta_catalog_sync_log.request_payload IS 'Original Meta Graph API request payload';
COMMENT ON COLUMN meta_catalog_sync_log.response_data IS 'Meta Graph API response data';
COMMENT ON COLUMN meta_catalog_sync_log.error_details IS 'Error details for failed sync attempts';
COMMENT ON COLUMN meta_catalog_sync_log.retry_count IS 'Number of retry attempts made';
COMMENT ON COLUMN meta_catalog_sync_log.next_retry_at IS 'Scheduled time for next retry attempt';
COMMENT ON COLUMN meta_catalog_sync_log.idempotency_key IS 'Key for deduplicating sync requests within 24h window';
COMMENT ON COLUMN products.meta_image_sync_version IS 'Version counter for image sync tracking';
COMMENT ON COLUMN products.meta_last_image_sync_at IS 'Timestamp of last successful image sync to Meta Catalog';