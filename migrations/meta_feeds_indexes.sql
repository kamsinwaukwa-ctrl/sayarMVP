-- Meta Feeds Database Indexes
-- Run these manually in Supabase SQL editor or via migration tool
-- These indexes optimize the Meta Feed generation queries

-- Optimize merchant slug lookups for feed generation
-- This index supports the public feed endpoint lookups by slug
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_merchants_slug_feeds
  ON merchants (slug) 
  WHERE slug IS NOT NULL;

-- Optimize feed generation queries for products
-- This composite index supports the main feed generation query:
-- WHERE merchant_id = ? AND status = 'active' AND meta_catalog_visible = true
-- ORDER BY updated_at DESC
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_feed_generation
  ON products (merchant_id, status, meta_catalog_visible, updated_at);

-- Additional index for feed performance monitoring
-- Supports queries filtering by meta sync status for feed statistics
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_meta_sync_monitoring
  ON products (merchant_id, meta_sync_status, meta_catalog_visible)
  WHERE meta_catalog_visible = true;

-- Index to support ETag generation (finding latest updated_at per merchant)
-- This helps generate proper cache headers efficiently
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_merchant_updated
  ON products (merchant_id, updated_at DESC)
  WHERE status = 'active' AND meta_catalog_visible = true;

-- Comments for production deployment:
-- 1. CREATE INDEX CONCURRENTLY can be run on live database without blocking
-- 2. These indexes will significantly improve feed generation performance
-- 3. Monitor index usage with: 
--    SELECT schemaname,tablename,indexname,idx_tup_read,idx_tup_fetch 
--    FROM pg_stat_user_indexes WHERE indexname LIKE 'idx_%feed%';
-- 4. If using migrations, split CONCURRENTLY operations into separate transactions