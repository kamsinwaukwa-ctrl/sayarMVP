-- Migration: Add Meta catalog sync fields to products table
-- File: migrations/011_meta_catalog_enhancements.sql
-- Date: 2025-01-27
-- Task: BE-010-products-crud-meta-sync

-- Add Meta catalog sync fields to products table
ALTER TABLE products ADD COLUMN IF NOT EXISTS meta_catalog_visible BOOLEAN DEFAULT true;
ALTER TABLE products ADD COLUMN IF NOT EXISTS meta_sync_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE products ADD COLUMN IF NOT EXISTS meta_sync_errors JSONB;
ALTER TABLE products ADD COLUMN IF NOT EXISTS meta_last_synced_at TIMESTAMP;

-- Ensure retailer_id is properly indexed and has constraint
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_products_retailer_id 
  ON products (retailer_id);

-- Add SKU uniqueness constraint per merchant
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_products_merchant_sku 
  ON products (merchant_id, sku) WHERE sku IS NOT NULL;

-- Add idempotency keys table
CREATE TABLE IF NOT EXISTS idempotency_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(100) NOT NULL,
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    endpoint VARCHAR(200) NOT NULL,
    request_hash VARCHAR(64) NOT NULL,
    response_data JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_idempotency_keys_unique 
  ON idempotency_keys (key, merchant_id, endpoint);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_idempotency_keys_cleanup 
  ON idempotency_keys (created_at);

-- Enable RLS on idempotency_keys
ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY idempotency_keys_tenant_isolation ON idempotency_keys
  FOR ALL USING (merchant_id::text = auth.jwt() ->> 'merchant_id');

-- Add indexes for product queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_status_active 
  ON products (merchant_id, status) WHERE status = 'active';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_meta_sync_pending 
  ON products (merchant_id, meta_sync_status) WHERE meta_sync_status = 'pending';

-- Add check constraints
ALTER TABLE products ADD CONSTRAINT IF NOT EXISTS chk_products_price_positive 
  CHECK (price_kobo >= 0);
ALTER TABLE products ADD CONSTRAINT IF NOT EXISTS chk_products_stock_positive 
  CHECK (stock >= 0);
ALTER TABLE products ADD CONSTRAINT IF NOT EXISTS chk_products_reserved_valid 
  CHECK (reserved_qty >= 0 AND reserved_qty <= stock);

-- Update meta_sync_status enum constraint
ALTER TABLE products ADD CONSTRAINT IF NOT EXISTS chk_products_meta_sync_status
  CHECK (meta_sync_status IN ('pending', 'syncing', 'synced', 'error'));

-- Add comments for documentation
COMMENT ON COLUMN products.meta_catalog_visible IS 'Whether product should be visible in Meta Commerce Catalog';
COMMENT ON COLUMN products.meta_sync_status IS 'Status of Meta catalog sync: pending, syncing, synced, error';
COMMENT ON COLUMN products.meta_sync_errors IS 'JSON array of sync errors from Meta API';
COMMENT ON COLUMN products.meta_last_synced_at IS 'Timestamp of last successful sync to Meta catalog';

COMMENT ON TABLE idempotency_keys IS 'Idempotency tracking for API operations with 24-hour TTL';
COMMENT ON COLUMN idempotency_keys.key IS 'Idempotency key from client request header';
COMMENT ON COLUMN idempotency_keys.endpoint IS 'API endpoint path for operation scoping';
COMMENT ON COLUMN idempotency_keys.request_hash IS 'SHA-256 hash of request payload for duplicate detection';
COMMENT ON COLUMN idempotency_keys.response_data IS 'Cached response data for idempotent replay';