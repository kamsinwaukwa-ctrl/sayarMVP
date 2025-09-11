-- Migration: BE-009 Configuration Management (DOWN)
BEGIN;

-- Drop triggers first
DROP TRIGGER IF EXISTS set_updated_at_feature_flags ON feature_flags;
DROP TRIGGER IF EXISTS set_updated_at_merchant_settings ON merchant_settings;
DROP TRIGGER IF EXISTS set_updated_at_system_settings ON system_settings;

-- Drop function if not used elsewhere
DROP FUNCTION IF EXISTS set_updated_at();

-- Drop tables (reverse dependency order)
DROP TABLE IF EXISTS system_settings;
DROP TABLE IF EXISTS merchant_settings;
DROP TABLE IF EXISTS feature_flags;


-- Use pgcrypto for gen_random_uuid(); Supabase enables this by default,
-- but we guard it here for local/dev.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Function to keep updated_at in sync
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =========================
-- system_settings
-- =========================
CREATE TABLE IF NOT EXISTS system_settings (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  key         text NOT NULL UNIQUE,
  value       jsonb NOT NULL,
  description text,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER set_updated_at_system_settings
BEFORE UPDATE ON system_settings
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Helpful index for partial lookups by key prefix (optional)
CREATE INDEX IF NOT EXISTS ix_system_settings_key ON system_settings (key);

-- =========================
-- merchant_settings
-- =========================
CREATE TABLE IF NOT EXISTS merchant_settings (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id uuid NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
  key         text NOT NULL,
  value       jsonb NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (merchant_id, key)
);

CREATE INDEX IF NOT EXISTS ix_merchant_settings_merchant_id ON merchant_settings (merchant_id);

CREATE TRIGGER set_updated_at_merchant_settings
BEFORE UPDATE ON merchant_settings
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =========================
-- feature_flags
-- =========================
-- Supports both global flags (merchant_id IS NULL) and per-merchant overrides.
CREATE TABLE IF NOT EXISTS feature_flags (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text NOT NULL,
  description text,
  enabled     boolean NOT NULL DEFAULT false,
  merchant_id uuid REFERENCES merchants(id) ON DELETE CASCADE,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Uniqueness rules:
-- 1) Only one GLOBAL row per name (merchant_id IS NULL)
CREATE UNIQUE INDEX IF NOT EXISTS ux_feature_flags_name_global
  ON feature_flags (name)
  WHERE merchant_id IS NULL;

-- 2) Only one OVERRIDE per (merchant, name)
CREATE UNIQUE INDEX IF NOT EXISTS ux_feature_flags_name_per_merchant
  ON feature_flags (name, merchant_id)
  WHERE merchant_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_feature_flags_merchant_id ON feature_flags (merchant_id);

CREATE TRIGGER set_updated_at_feature_flags
BEFORE UPDATE ON feature_flags
FOR EACH ROW EXECUTE FUNCTION set_updated_at();


COMMIT;
