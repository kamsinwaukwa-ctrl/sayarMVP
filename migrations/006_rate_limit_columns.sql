-- Sayar Platform
-- Migration: 008_rate_limit_columns.sql
-- Description: Add per-merchant rate limit configuration columns

BEGIN;

ALTER TABLE merchants
  ADD COLUMN IF NOT EXISTS api_rate_limit_per_minute INTEGER NOT NULL DEFAULT 60 CHECK (api_rate_limit_per_minute >= 0),
  ADD COLUMN IF NOT EXISTS api_burst_limit INTEGER NOT NULL DEFAULT 15 CHECK (api_burst_limit >= 0),
  ADD COLUMN IF NOT EXISTS wa_rate_limit_per_hour INTEGER NOT NULL DEFAULT 1000 CHECK (wa_rate_limit_per_hour >= 0),
  ADD COLUMN IF NOT EXISTS rate_limit_enabled BOOLEAN NOT NULL DEFAULT TRUE;

COMMENT ON COLUMN merchants.api_rate_limit_per_minute IS 'Default API requests per minute per merchant';
COMMENT ON COLUMN merchants.api_burst_limit IS 'Short-window burst capacity for token bucket';
COMMENT ON COLUMN merchants.wa_rate_limit_per_hour IS 'WhatsApp messages per hour per merchant (soft cap for scheduling)';
COMMENT ON COLUMN merchants.rate_limit_enabled IS 'Toggle rate limiting for this merchant';

COMMIT;
