-- Migration: Add Meta catalog sync fields to products table (TX-safe)
-- File: migrations/011_meta_catalog_enhancements.sql
-- Date: 2025-01-27
-- Task: BE-010-products-crud-meta-sync

-- Optional (needed for gen_random_uuid)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Add Meta catalog sync fields to products table
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS meta_catalog_visible BOOLEAN DEFAULT true;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS meta_sync_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS meta_sync_errors JSONB;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS meta_last_synced_at TIMESTAMP;

-- Ensure retailer_id is indexed (NOTE: UNIQUE may be too strict for many products per retailer)
CREATE UNIQUE INDEX IF NOT EXISTS idx_products_retailer_id 
  ON public.products (retailer_id);

-- Add SKU uniqueness constraint per merchant
CREATE UNIQUE INDEX IF NOT EXISTS idx_products_merchant_sku 
  ON public.products (merchant_id, sku) WHERE sku IS NOT NULL;

-- Add idempotency keys table
CREATE TABLE IF NOT EXISTS public.idempotency_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(100) NOT NULL,
    merchant_id UUID NOT NULL REFERENCES public.merchants(id) ON DELETE CASCADE,
    endpoint VARCHAR(200) NOT NULL,
    request_hash VARCHAR(64) NOT NULL,
    response_data JSONB,
    created_at TIMESTAMP DEFAULT now()
);

-- Indexes for idempotency_keys (non-concurrent for TX safety)
CREATE UNIQUE INDEX IF NOT EXISTS idx_idempotency_keys_unique 
  ON public.idempotency_keys (key, merchant_id, endpoint);

CREATE INDEX IF NOT EXISTS idx_idempotency_keys_cleanup 
  ON public.idempotency_keys (created_at);

-- Enable RLS on idempotency_keys
ALTER TABLE public.idempotency_keys ENABLE ROW LEVEL SECURITY;

-- Recreate policy idempotently (DROP then CREATE, since CREATE POLICY has no IF NOT EXISTS)
DROP POLICY IF EXISTS idempotency_keys_tenant_isolation ON public.idempotency_keys;
CREATE POLICY idempotency_keys_tenant_isolation ON public.idempotency_keys
  FOR ALL USING (merchant_id::text = auth.jwt() ->> 'merchant_id');

-- Add indexes for product queries (non-concurrent for TX safety)
CREATE INDEX IF NOT EXISTS idx_products_status_active 
  ON public.products (merchant_id, status) WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_products_meta_sync_pending 
  ON public.products (merchant_id, meta_sync_status) WHERE meta_sync_status = 'pending';

-- Add check constraints (Postgres doesn't support IF NOT EXISTS on ADD CONSTRAINT)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint 
    WHERE conname = 'chk_products_price_positive' 
      AND conrelid = 'public.products'::regclass
  ) THEN
    ALTER TABLE public.products 
      ADD CONSTRAINT chk_products_price_positive CHECK (price_kobo >= 0);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint 
    WHERE conname = 'chk_products_stock_positive' 
      AND conrelid = 'public.products'::regclass
  ) THEN
    ALTER TABLE public.products 
      ADD CONSTRAINT chk_products_stock_positive CHECK (stock >= 0);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint 
    WHERE conname = 'chk_products_reserved_valid' 
      AND conrelid = 'public.products'::regclass
  ) THEN
    ALTER TABLE public.products 
      ADD CONSTRAINT chk_products_reserved_valid CHECK (reserved_qty >= 0 AND reserved_qty <= stock);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint 
    WHERE conname = 'chk_products_meta_sync_status' 
      AND conrelid = 'public.products'::regclass
  ) THEN
    ALTER TABLE public.products 
      ADD CONSTRAINT chk_products_meta_sync_status
      CHECK (meta_sync_status IN ('pending', 'syncing', 'synced', 'error'));
  END IF;
END
$$;

-- Add comments for documentation
COMMENT ON COLUMN public.products.meta_catalog_visible IS 'Whether product should be visible in Meta Commerce Catalog';
COMMENT ON COLUMN public.products.meta_sync_status IS 'Status of Meta catalog sync: pending, syncing, synced, error';
COMMENT ON COLUMN public.products.meta_sync_errors IS 'JSON array of sync errors from Meta API';
COMMENT ON COLUMN public.products.meta_last_synced_at IS 'Timestamp of last successful sync to Meta catalog';

COMMENT ON TABLE public.idempotency_keys IS 'Idempotency tracking for API operations with 24-hour TTL';
COMMENT ON COLUMN public.idempotency_keys.key IS 'Idempotency key from client request header';
COMMENT ON COLUMN public.idempotency_keys.endpoint IS 'API endpoint path for operation scoping';
COMMENT ON COLUMN public.idempotency_keys.request_hash IS 'SHA-256 hash of request payload for duplicate detection';
COMMENT ON COLUMN public.idempotency_keys.response_data IS 'Cached response data for idempotent replay';