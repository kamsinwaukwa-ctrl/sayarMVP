BEGIN;

-- 1) Drop column-level NOT NULLs for staged fields
ALTER TABLE public.meta_integrations
  ALTER COLUMN catalog_id DROP NOT NULL,
  ALTER COLUMN system_user_token_encrypted DROP NOT NULL,
  ALTER COLUMN app_id DROP NOT NULL;

-- 2) Defensively drop any auto-generated NOT NULL CHECK constraints
DO $$
DECLARE
  r RECORD;
BEGIN
  -- Drop by known names if they exist (from your constraint listing)
  IF EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = '2200_32832_3_not_null'
  ) THEN
    EXECUTE 'ALTER TABLE public.meta_integrations DROP CONSTRAINT "2200_32832_3_not_null"';
  END IF;

  IF EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = '2200_32832_4_not_null'
  ) THEN
    EXECUTE 'ALTER TABLE public.meta_integrations DROP CONSTRAINT "2200_32832_4_not_null"';
  END IF;

  IF EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = '2200_32832_5_not_null'
  ) THEN
    EXECUTE 'ALTER TABLE public.meta_integrations DROP CONSTRAINT "2200_32832_5_not_null"';
  END IF;

  -- Catch any other NOT NULL CHECK constraints that match these columns
  FOR r IN
    SELECT c.conname
    FROM pg_constraint c
    JOIN pg_class t       ON c.conrelid = t.oid
    JOIN pg_namespace ns  ON t.relnamespace = ns.oid
    WHERE t.relname = 'meta_integrations'
      AND ns.nspname = 'public'
      AND c.contype = 'c'
      AND (
           pg_get_constraintdef(c.oid) ILIKE '%catalog_id IS NOT NULL%'
        OR pg_get_constraintdef(c.oid) ILIKE '%system_user_token_encrypted IS NOT NULL%'
        OR pg_get_constraintdef(c.oid) ILIKE '%app_id IS NOT NULL%'
      )
  LOOP
    EXECUTE format(
      'ALTER TABLE %I.%I DROP CONSTRAINT %I',
      'public', 'meta_integrations', r.conname
    );
  END LOOP;
END
$$;

-- 3) Ensure status has a sensible default for partial records
ALTER TABLE public.meta_integrations
  ALTER COLUMN status SET DEFAULT 'pending';

-- 4) Document the intent
COMMENT ON TABLE public.meta_integrations IS
  'Per-merchant Meta Commerce Catalog integration credentials and status. Supports staged onboarding where catalog_id, system_user_token_encrypted, and app_id can be provided separately.';

COMMIT;