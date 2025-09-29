-- Migration: 018_meta_sync_reason.sql
-- Add meta_sync_reason field for human-readable sync error explanations

-- Add meta_sync_reason column to products table
ALTER TABLE products
ADD COLUMN meta_sync_reason VARCHAR(500);

-- Add performance index for error/pending status queries
CREATE INDEX idx_products_meta_sync_status_reason
ON products (merchant_id, meta_sync_status)
WHERE meta_sync_status IN ('error', 'pending');

-- Add comment for documentation
COMMENT ON COLUMN products.meta_sync_reason IS 'Human-readable explanation of Meta sync status derived from meta_sync_errors';