-- Migration: Add logo_url column to merchants table
-- Task: BE-011 Media Upload Policies
-- Description: Optional migration to add logo_url reference column for convenience

-- ============================================================================
-- UP Migration: Add logo_url column
-- ============================================================================

-- Add logo_url column to merchants table for convenience (optional)
-- The authoritative blob lives in Supabase Storage, this is just a reference
ALTER TABLE merchants 
ADD COLUMN IF NOT EXISTS logo_url text;

-- Add comment to document the column purpose
COMMENT ON COLUMN merchants.logo_url IS 'Optional convenience reference to merchant logo in Supabase Storage. Authoritative blob lives in storage bucket.';

-- Create index for potential queries on logo_url
CREATE INDEX IF NOT EXISTS idx_merchants_logo_url 
ON merchants(logo_url) 
WHERE logo_url IS NOT NULL;

-- ============================================================================
-- DOWN Migration: Remove logo_url column
-- ============================================================================

/*
-- To rollback this migration, execute the following:

-- Drop the index first
DROP INDEX IF EXISTS idx_merchants_logo_url;

-- Remove the logo_url column
ALTER TABLE merchants DROP COLUMN IF EXISTS logo_url;

*/

-- ============================================================================
-- NOTES
-- ============================================================================

/*
1. This migration is OPTIONAL and can be deferred
   - The media upload system works without this column
   - Storage is the authoritative source for logos
   - This column is only for convenience/display purposes

2. Column Usage:
   - Updated automatically by MediaService when logos are uploaded/deleted
   - Contains storage path reference, not the signed URL
   - Can be used for quick logo existence checks in queries

3. Storage vs Database:
   - Supabase Storage: Authoritative blob storage
   - Database logo_url: Optional convenience reference
   - Always use signed URLs for actual file access

4. Migration Safety:
   - Uses IF NOT EXISTS/IF EXISTS for idempotent operations
   - Safe to run multiple times
   - Safe to rollback

5. Performance:
   - Index created only for non-null values (partial index)
   - Minimal storage overhead for merchants without logos

6. Multi-tenant Isolation:
   - RLS policies still apply to merchants table
   - logo_url values will be tenant-isolated automatically
   - No additional security policies needed for this column

7. Application Updates:
   - MediaService automatically updates this column
   - No changes needed to existing merchant queries
   - Column will be NULL for merchants without logos
*/