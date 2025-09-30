-- ============================================================================
-- Fix webhook_endpoints.app_secret_encrypted column type
-- Change from TEXT to BYTEA for proper PGP encryption storage
-- ============================================================================

-- 1) Change column type from TEXT to BYTEA
-- Note: This will fail if there's existing corrupted data
-- In that case, you'll need to re-bootstrap the webhook after this migration

DO $$
BEGIN
  -- Try to alter the column type
  BEGIN
    ALTER TABLE webhook_endpoints
      ALTER COLUMN app_secret_encrypted TYPE BYTEA
      USING app_secret_encrypted::bytea;

    RAISE NOTICE 'Successfully converted app_secret_encrypted to BYTEA';
  EXCEPTION
    WHEN others THEN
      -- If conversion fails, clear the table and change type
      RAISE WARNING 'Could not convert existing data. Clearing webhook_endpoints table...';
      DELETE FROM webhook_endpoints;

      ALTER TABLE webhook_endpoints
        ALTER COLUMN app_secret_encrypted TYPE BYTEA;

      RAISE NOTICE 'Cleared table and changed app_secret_encrypted to BYTEA. Please re-bootstrap webhooks.';
  END;
END$$;

-- 2) Update the comment to reflect BYTEA storage
COMMENT ON COLUMN webhook_endpoints.app_secret_encrypted IS
  'PGP-sym encrypted Meta App Secret stored as BYTEA (never store plaintext).';

-- ============================================================================
-- Migration complete. Next steps:
-- 1. Run this migration in your Supabase SQL editor
-- 2. Re-run the webhook bootstrap script to re-encrypt the app secret properly
-- 3. Test webhook decryption
-- ============================================================================