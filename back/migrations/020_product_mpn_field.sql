-- Migration: Add brand and MPN fields to products table for BE-010.2
-- Purpose: Support auto-generation of brand/MPN for Meta Catalog compliance

-- Add brand column to products table
ALTER TABLE products
ADD COLUMN IF NOT EXISTS brand VARCHAR(70);

-- Add MPN column to products table
ALTER TABLE products
ADD COLUMN IF NOT EXISTS mpn VARCHAR(70);

-- Add indexes for potential future searches
CREATE INDEX IF NOT EXISTS idx_products_brand ON products(merchant_id, brand)
WHERE brand IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_products_mpn ON products(merchant_id, mpn)
WHERE mpn IS NOT NULL;

-- Add check constraints for format validation
ALTER TABLE products
ADD CONSTRAINT chk_products_brand_format
CHECK (brand IS NULL OR (length(trim(brand)) >= 1 AND length(trim(brand)) <= 70));

ALTER TABLE products
ADD CONSTRAINT chk_products_mpn_format
CHECK (mpn IS NULL OR mpn ~ '^[A-Za-z0-9-._]{1,70}$');

-- Update RLS policies to include brand and mpn in allowed columns (already covered by existing policies)
-- No additional RLS changes needed as brand/mpn follow same tenant isolation rules

-- Add comments for documentation
COMMENT ON COLUMN products.brand IS 'Product brand - auto-generated from merchant name if not provided. Used for Meta Commerce Catalog compliance.';
COMMENT ON COLUMN products.mpn IS 'Manufacturer Part Number - auto-generated as <merchant_slug>-<sku> if not provided. Used for Meta Commerce Catalog compliance.';