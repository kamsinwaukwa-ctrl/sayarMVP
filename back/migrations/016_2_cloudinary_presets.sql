-- Migration 016_2: Cloudinary Transform Presets
-- Extends existing product_images table with preset information
-- Creates preset performance tracking table

BEGIN;

-- Add preset tracking columns to product_images
ALTER TABLE product_images ADD COLUMN IF NOT EXISTS preset_profile TEXT DEFAULT 'standard';
ALTER TABLE product_images ADD COLUMN IF NOT EXISTS variants JSONB DEFAULT '{}'::jsonb;
ALTER TABLE product_images ADD COLUMN IF NOT EXISTS optimization_stats JSONB DEFAULT '{}'::jsonb;
ALTER TABLE product_images ADD COLUMN IF NOT EXISTS preset_version INTEGER DEFAULT 1;

-- Create preset performance tracking table
CREATE TABLE IF NOT EXISTS cloudinary_preset_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    preset_id TEXT NOT NULL,
    usage_count INTEGER DEFAULT 0,
    avg_file_size_kb INTEGER,
    avg_processing_time_ms INTEGER,
    quality_score_avg DECIMAL(3,1),
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(merchant_id, preset_id)
);

-- Indexes for preset stats
CREATE INDEX IF NOT EXISTS idx_preset_stats_merchant_preset
  ON cloudinary_preset_stats(merchant_id, preset_id);

CREATE INDEX IF NOT EXISTS idx_preset_stats_usage
  ON cloudinary_preset_stats(usage_count DESC, last_used_at DESC);

-- GIN indexes for JSONB columns for efficient querying
CREATE INDEX IF NOT EXISTS idx_product_images_variants_gin
  ON product_images USING GIN (variants);

CREATE INDEX IF NOT EXISTS idx_product_images_optimization_stats_gin
  ON product_images USING GIN (optimization_stats);

-- Add preset validation constraint (compat version; no IF NOT EXISTS)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'valid_preset_profile'
      AND conrelid = 'public.product_images'::regclass
  ) THEN
    ALTER TABLE product_images
      ADD CONSTRAINT valid_preset_profile
      CHECK (preset_profile IN ('standard', 'premium', 'mobile_first', 'catalog_focus'));
  END IF;
END
$$;

-- Update existing images with default preset profile
UPDATE product_images
SET preset_profile = 'standard'
WHERE preset_profile IS NULL;

-- RLS Policy for preset stats
ALTER TABLE cloudinary_preset_stats ENABLE ROW LEVEL SECURITY;

-- Drop and recreate policies for compatibility
DROP POLICY IF EXISTS "Merchants manage own preset stats" ON cloudinary_preset_stats;
CREATE POLICY "Merchants manage own preset stats"
  ON cloudinary_preset_stats
  FOR INSERT
  TO authenticated
  WITH CHECK (merchant_id::text = auth.jwt() ->> 'merchant_id');

DROP POLICY IF EXISTS "Merchants read own preset stats" ON cloudinary_preset_stats;
CREATE POLICY "Merchants read own preset stats"
  ON cloudinary_preset_stats
  FOR SELECT
  TO authenticated
  USING (merchant_id::text = auth.jwt() ->> 'merchant_id');

DROP POLICY IF EXISTS "Merchants update own preset stats" ON cloudinary_preset_stats;
CREATE POLICY "Merchants update own preset stats"
  ON cloudinary_preset_stats
  FOR UPDATE
  TO authenticated
  USING (merchant_id::text = auth.jwt() ->> 'merchant_id')
  WITH CHECK (merchant_id::text = auth.jwt() ->> 'merchant_id');

DROP POLICY IF EXISTS "Admins all access preset stats" ON cloudinary_preset_stats;
CREATE POLICY "Admins all access preset stats"
  ON cloudinary_preset_stats
  FOR ALL
  TO authenticated
  USING (auth.jwt() ->> 'role' = 'admin')
  WITH CHECK (auth.jwt() ->> 'role' = 'admin');

-- Trigger for preset stats updated_at (idempotent)
DROP TRIGGER IF EXISTS update_preset_stats_updated_at ON cloudinary_preset_stats;
-- Requires helper function update_updated_at_column() to exist
CREATE TRIGGER update_preset_stats_updated_at
    BEFORE UPDATE ON cloudinary_preset_stats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON COLUMN product_images.preset_profile IS 'Preset profile used for image transformations (standard, premium, mobile_first, catalog_focus)';
COMMENT ON COLUMN product_images.variants IS 'JSON object containing all generated image variants with URLs and metadata';
COMMENT ON COLUMN product_images.optimization_stats IS 'JSON object containing optimization statistics and performance metrics';
COMMENT ON COLUMN product_images.preset_version IS 'Version of preset configuration used for transformations';

COMMENT ON TABLE cloudinary_preset_stats IS 'Performance statistics tracking for Cloudinary transformation presets';
COMMENT ON COLUMN cloudinary_preset_stats.preset_id IS 'ID of the transformation preset being tracked';
COMMENT ON COLUMN cloudinary_preset_stats.usage_count IS 'Total number of times this preset has been used';
COMMENT ON COLUMN cloudinary_preset_stats.avg_file_size_kb IS 'Average file size in KB for images using this preset';
COMMENT ON COLUMN cloudinary_preset_stats.avg_processing_time_ms IS 'Average processing time in milliseconds';
COMMENT ON COLUMN cloudinary_preset_stats.quality_score_avg IS 'Average quality score (1-100) for images using this preset';

-- Sample function to update preset statistics (called by application)
CREATE OR REPLACE FUNCTION update_preset_stats(
    p_merchant_id UUID,
    p_preset_id TEXT,
    p_file_size_kb INTEGER,
    p_processing_time_ms INTEGER,
    p_quality_score DECIMAL
) RETURNS VOID AS $$
BEGIN
    INSERT INTO cloudinary_preset_stats (
        merchant_id,
        preset_id,
        usage_count,
        avg_file_size_kb,
        avg_processing_time_ms,
        quality_score_avg,
        last_used_at
    ) VALUES (
        p_merchant_id,
        p_preset_id,
        1,
        p_file_size_kb,
        p_processing_time_ms,
        p_quality_score,
        NOW()
    )
    ON CONFLICT (merchant_id, preset_id)
    DO UPDATE SET
        usage_count = cloudinary_preset_stats.usage_count + 1,
        avg_file_size_kb = ROUND(
            (
                (cloudinary_preset_stats.avg_file_size_kb * cloudinary_preset_stats.usage_count + p_file_size_kb)::numeric
            ) / (cloudinary_preset_stats.usage_count + 1)
        )::int,
        avg_processing_time_ms = ROUND(
            (
                (cloudinary_preset_stats.avg_processing_time_ms * cloudinary_preset_stats.usage_count + p_processing_time_ms)::numeric
            ) / (cloudinary_preset_stats.usage_count + 1)
        )::int,
        quality_score_avg = ROUND(
            (
                (cloudinary_preset_stats.quality_score_avg * cloudinary_preset_stats.usage_count + p_quality_score)::numeric
            ) / (cloudinary_preset_stats.usage_count + 1)
        , 1),
        last_used_at = NOW(),
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant permissions for the stats update function
GRANT EXECUTE ON FUNCTION update_preset_stats(UUID, TEXT, INTEGER, INTEGER, DECIMAL) TO authenticated;

COMMIT;