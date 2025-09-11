-- Sayar WhatsApp Commerce Platform - Auth Enhancements
-- Migration: 004_auth_enhancements.sql
-- Description: Add optional auth tracking fields to users table

BEGIN;

-- Add optional authentication tracking fields to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS failed_login_attempts int DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_login_at timestamptz,
ADD COLUMN IF NOT EXISTS password_changed_at timestamptz DEFAULT now();

-- Add index for performance on email lookups (for login)
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Add index for merchant_id lookups
CREATE INDEX IF NOT EXISTS idx_users_merchant_id ON users(merchant_id);

-- Update existing users to set password_changed_at for existing records
UPDATE users 
SET password_changed_at = created_at 
WHERE password_changed_at IS NULL;

-- Add comments
COMMENT ON COLUMN users.failed_login_attempts IS 'Count of consecutive failed login attempts for rate limiting';
COMMENT ON COLUMN users.last_login_at IS 'Timestamp of last successful login';
COMMENT ON COLUMN users.password_changed_at IS 'Timestamp when password was last changed';

COMMIT;