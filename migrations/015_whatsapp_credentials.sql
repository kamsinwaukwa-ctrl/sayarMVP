-- Migration: 015_whatsapp_credentials.sql
-- Description: Add encrypted WhatsApp credentials fields to merchants table
-- Author: BE-015 WhatsApp Credentials CRUD implementation
-- Date: 2025-01-14

-- Extend merchants table with encrypted WhatsApp credentials
ALTER TABLE merchants
ADD COLUMN waba_id_enc TEXT, -- Stores encrypted ciphertext
ADD COLUMN phone_number_id_enc TEXT, -- Stores encrypted ciphertext
ADD COLUMN app_id_enc TEXT, -- Stores encrypted ciphertext
ADD COLUMN system_user_token_enc TEXT, -- Stores encrypted ciphertext
ADD COLUMN wa_connection_status TEXT NOT NULL DEFAULT 'not_connected'
    CHECK (wa_connection_status IN ('not_connected', 'verified_test', 'verified_prod')),
ADD COLUMN wa_environment TEXT NOT NULL DEFAULT 'test'
    CHECK (wa_environment IN ('test', 'prod')),
ADD COLUMN wa_verified_at TIMESTAMPTZ,
ADD COLUMN wa_last_error TEXT;

-- Index for connection status queries
CREATE INDEX idx_merchants_wa_status ON merchants (wa_connection_status, wa_verified_at);

-- Update RLS policies remain the same (merchant_id isolation already in place)
-- The existing RLS policies for merchants table will automatically apply to new columns

-- Comments for documentation
COMMENT ON COLUMN merchants.waba_id_enc IS 'Encrypted WhatsApp Business Account ID';
COMMENT ON COLUMN merchants.phone_number_id_enc IS 'Encrypted Phone Number ID from Meta';
COMMENT ON COLUMN merchants.app_id_enc IS 'Encrypted Facebook App ID';
COMMENT ON COLUMN merchants.system_user_token_enc IS 'Encrypted System User access token';
COMMENT ON COLUMN merchants.wa_connection_status IS 'WhatsApp connection verification status';
COMMENT ON COLUMN merchants.wa_environment IS 'WhatsApp environment (test/prod)';
COMMENT ON COLUMN merchants.wa_verified_at IS 'Timestamp of last successful verification';
COMMENT ON COLUMN merchants.wa_last_error IS 'Last error message from verification attempt';