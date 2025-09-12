-- Rollback Migration: Remove Meta catalog sync fields from products table
-- File: migrations/011_meta_catalog_enhancements_down.sql
-- Date: 2025-01-27
-- Task: BE-010-products-crud-meta-sync

-- Remove check constraints
ALTER TABLE products DROP CONSTRAINT IF EXISTS chk_products_meta_sync_status;
ALTER TABLE products DROP CONSTRAINT IF EXISTS chk_products_reserved_valid;
ALTER TABLE products DROP CONSTRAINT IF EXISTS chk_products_stock_positive;
ALTER TABLE products DROP CONSTRAINT IF EXISTS chk_products_price_positive;

-- Remove indexes
DROP INDEX CONCURRENTLY IF EXISTS idx_products_meta_sync_pending;
DROP INDEX CONCURRENTLY IF EXISTS idx_products_status_active;
DROP INDEX CONCURRENTLY IF EXISTS idx_idempotency_keys_cleanup;
DROP INDEX CONCURRENTLY IF EXISTS idx_idempotency_keys_unique;
DROP INDEX CONCURRENTLY IF EXISTS idx_products_merchant_sku;
DROP INDEX CONCURRENTLY IF EXISTS idx_products_retailer_id;

-- Drop idempotency_keys table
DROP TABLE IF EXISTS idempotency_keys;

-- Remove Meta catalog sync fields from products table
ALTER TABLE products DROP COLUMN IF EXISTS meta_last_synced_at;
ALTER TABLE products DROP COLUMN IF EXISTS meta_sync_errors;
ALTER TABLE products DROP COLUMN IF EXISTS meta_sync_status;
ALTER TABLE products DROP COLUMN IF EXISTS meta_catalog_visible;