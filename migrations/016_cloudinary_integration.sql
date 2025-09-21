-- Migration 016: Cloudinary Integration
-- Product images table with metadata tracking and RLS policies

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Product images table
CREATE TABLE product_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    cloudinary_public_id TEXT NOT NULL UNIQUE,
    secure_url TEXT NOT NULL,
    thumbnail_url TEXT,
    width INTEGER,
    height INTEGER,
    format TEXT,
    bytes INTEGER,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    alt_text TEXT,
    upload_status TEXT NOT NULL DEFAULT 'uploading' CHECK (upload_status IN ('uploading', 'completed', 'failed', 'deleted')),
    cloudinary_version BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_product_images_product_id ON product_images(product_id);
CREATE INDEX idx_product_images_merchant_id ON product_images(merchant_id);
CREATE INDEX idx_product_images_is_primary ON product_images(product_id) WHERE is_primary = TRUE;
CREATE INDEX idx_product_images_cloudinary_public_id ON product_images(cloudinary_public_id);
CREATE INDEX idx_product_images_upload_status ON product_images(upload_status);

-- RLS Policies
ALTER TABLE product_images ENABLE ROW LEVEL SECURITY;

-- Product images policies
CREATE POLICY "Merchants can manage their own product images" ON product_images
    FOR ALL USING (merchant_id::text = auth.jwt() ->> 'merchant_id');

-- Constraints
ALTER TABLE product_images DROP CONSTRAINT IF EXISTS unique_primary_image_per_product;
DROP INDEX IF EXISTS ux_product_images_primary;
CREATE UNIQUE INDEX ux_product_images_primary
  ON product_images(product_id)
  WHERE is_primary = TRUE;

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_product_images_updated_at
    BEFORE UPDATE ON product_images
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Update existing products table to link with images
ALTER TABLE products ADD COLUMN primary_image_id UUID REFERENCES product_images(id) ON DELETE SET NULL;
CREATE INDEX idx_products_primary_image_id ON products(primary_image_id);

-- Comments for documentation
COMMENT ON TABLE product_images IS 'Product images stored in Cloudinary with metadata tracking';
COMMENT ON COLUMN product_images.cloudinary_public_id IS 'Cloudinary public_id in format: sayar/products/{merchant_id}/{image_uuid}';
COMMENT ON COLUMN product_images.secure_url IS 'Main preset URL (c_limit,w_1600,h_1600,f_auto,q_auto:good) for Meta Catalog';
COMMENT ON COLUMN product_images.thumbnail_url IS 'Thumbnail preset URL (c_fill,w_600,h_600,g_auto,f_auto,q_auto:eco)';
COMMENT ON COLUMN product_images.upload_status IS 'Status: uploading, completed, failed, deleted';
COMMENT ON COLUMN product_images.is_primary IS 'Primary image triggers Meta Catalog sync when changed';
COMMENT ON COLUMN product_images.cloudinary_version IS 'Cloudinary version number for webhook idempotency';