-- ============================================================================
-- Webhook Endpoints: table, RLS, and admin functions
-- ============================================================================

-- 0) Crypto primitives
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1) Helper: updated_at trigger function (idempotent)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_proc WHERE proname = 'update_updated_at_column'
  ) THEN
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER
    LANGUAGE plpgsql
    AS $fn$
    BEGIN
      NEW.updated_at := NOW();
      RETURN NEW;
    END
    $fn$;
  END IF;
END$$;

-- 2) Table (TEXT everywhere; no VARCHAR)
CREATE TABLE IF NOT EXISTS webhook_endpoints (
  id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id              UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
  provider                 TEXT NOT NULL DEFAULT 'whatsapp',  -- future: instagram / telegram etc.

  -- Meta app identification
  app_id                   TEXT NOT NULL,   -- used in the URL path
  app_secret_encrypted     TEXT NOT NULL,   -- PGP-sym encrypted with app.encryption_key
  verify_token_hash        TEXT NOT NULL,   -- bcrypt (crypt) hash

  -- WhatsApp-specific (optional, but useful for routing/diagnostics)
  phone_number_id          TEXT,
  waba_id                  TEXT,
  whatsapp_phone_e164      TEXT,

  -- Routing
  callback_path            TEXT NOT NULL,   -- e.g. /api/webhooks/whatsapp/app/{app_id}

  -- Ops / observability
  last_webhook_at          TIMESTAMPTZ,
  signature_fail_count     INTEGER NOT NULL DEFAULT 0,

  -- Lifecycle
  active                   BOOLEAN NOT NULL DEFAULT TRUE,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Uniqueness
  CONSTRAINT webhook_endpoints_merchant_provider_app_uidx
    UNIQUE (merchant_id, provider, app_id),

  CONSTRAINT webhook_endpoints_app_id_uidx
    UNIQUE (app_id)
);

-- 3) Indexes
CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_merchant_id ON webhook_endpoints(merchant_id);
CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_app_id      ON webhook_endpoints(app_id);
CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_active      ON webhook_endpoints(active) WHERE active = TRUE;
CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_phone_id    ON webhook_endpoints(phone_number_id) WHERE phone_number_id IS NOT NULL;

-- 4) updated_at trigger
DROP TRIGGER IF EXISTS trg_webhook_endpoints_updated_at ON webhook_endpoints;
CREATE TRIGGER trg_webhook_endpoints_updated_at
  BEFORE UPDATE ON webhook_endpoints
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- 5) RLS
ALTER TABLE webhook_endpoints ENABLE ROW LEVEL SECURITY;

-- 5a) Merchant read-only: can ONLY view their own rows
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'webhook_endpoints' AND policyname = 'merchant_select_own_webhooks'
  ) THEN
    CREATE POLICY merchant_select_own_webhooks
      ON webhook_endpoints
      FOR SELECT
      USING (
        auth.jwt() ->> 'merchant_id' = merchant_id::text
      );
  END IF;
END$$;

-- 5b) Service role: full access (insert/update/delete/select)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'webhook_endpoints' AND policyname = 'service_full_access_webhooks'
  ) THEN
    CREATE POLICY service_full_access_webhooks
      ON webhook_endpoints
      FOR ALL
      USING   (auth.jwt() ->> 'role' = 'service_role')
      WITH CHECK (auth.jwt() ->> 'role' = 'service_role');
  END IF;
END$$;

-- Optional comments
COMMENT ON TABLE  webhook_endpoints IS 'Per-app webhook config with encrypted app_secret and hashed verify token.';
COMMENT ON COLUMN webhook_endpoints.app_secret_encrypted IS 'PGP-sym encrypted Meta App Secret (never store plaintext).';
COMMENT ON COLUMN webhook_endpoints.verify_token_hash    IS 'Bcrypt hash of verify token (raw shown once on creation).';
COMMENT ON COLUMN webhook_endpoints.callback_path        IS 'Path used in callback URL: /api/webhooks/whatsapp/app/{app_id}.';

-- ============================================================================
-- 6) Admin function: create OR rotate a webhook record
--    - If row exists: updates in-place (rotate verify token, replace secret, etc.)
--    - If not: inserts a new row
--    - Returns: callback_url + the NEW verify token (only once)
--    SECURITY NOTE: Call this from your backend with a service-role JWT and
--    set `SET app.encryption_key = '...';` for PGP encryption key management.
-- ============================================================================

CREATE OR REPLACE FUNCTION admin_create_or_rotate_webhook(
  p_merchant_id          UUID,
  p_provider             TEXT,           -- e.g. 'whatsapp'
  p_app_id               TEXT,           -- Meta App ID
  p_app_secret_plain     TEXT,           -- plaintext secret from Meta
  p_base_url             TEXT,           -- e.g. 'https://your-railway.app'
  p_phone_number_id      TEXT DEFAULT NULL,
  p_waba_id              TEXT DEFAULT NULL,
  p_whatsapp_phone_e164  TEXT DEFAULT NULL,
  p_verify_token_plain   TEXT DEFAULT NULL  -- if NULL, one is generated
)
RETURNS TABLE (
  id            UUID,
  callback_url  TEXT,
  verify_token  TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $fn$
DECLARE
  v_existing_id        UUID;
  v_callback_path      TEXT;
  v_callback_url       TEXT;
  v_verify_token_raw   TEXT;
  v_verify_token_hash  TEXT;
  v_app_secret_enc     TEXT;
BEGIN
  -- Require service role (defense-in-depth). Adjust to your auth if needed.
  IF (auth.jwt() ->> 'role') IS DISTINCT FROM 'service_role' THEN
    RAISE EXCEPTION 'insufficient_privilege: service_role required';
  END IF;

  IF p_app_id IS NULL OR length(p_app_id) = 0 THEN
    RAISE EXCEPTION 'app_id is required';
  END IF;

  -- Build path and URL
  v_callback_path := '/api/webhooks/whatsapp/app/' || p_app_id;
  v_callback_url  := rtrim(p_base_url, '/') || v_callback_path;

  -- Verify token: generate if not supplied
  v_verify_token_raw := COALESCE(
    p_verify_token_plain,
    -- 32 random bytes base64url (no padding) → ~43 chars; safe, high-entropy
    replace(replace(encode(gen_random_bytes(32), 'base64'), '+','-'), '/','_')
  );

  -- Hash token with bcrypt
  v_verify_token_hash := crypt(v_verify_token_raw, gen_salt('bf'));

  -- Encrypt app secret with app.encryption_key
  -- Make sure your backend sets: SET app.encryption_key = '...';
  v_app_secret_enc := pgp_sym_encrypt(p_app_secret_plain, current_setting('app.encryption_key', true));

  -- Upsert: if row exists for (merchant, provider, app_id) update it; else insert
  SELECT id INTO v_existing_id
  FROM webhook_endpoints
  WHERE merchant_id = p_merchant_id
    AND provider    = p_provider
    AND app_id      = p_app_id;

  IF v_existing_id IS NULL THEN
    INSERT INTO webhook_endpoints (
      merchant_id, provider, app_id,
      app_secret_encrypted, verify_token_hash,
      phone_number_id, waba_id, whatsapp_phone_e164,
      callback_path, active
    )
    VALUES (
      p_merchant_id, COALESCE(p_provider, 'whatsapp'), p_app_id,
      v_app_secret_enc, v_verify_token_hash,
      p_phone_number_id, p_waba_id, p_whatsapp_phone_e164,
      v_callback_path, TRUE
    )
    RETURNING id INTO v_existing_id;
  ELSE
    UPDATE webhook_endpoints
    SET
      app_secret_encrypted    = v_app_secret_enc,
      verify_token_hash       = v_verify_token_hash,
      phone_number_id         = COALESCE(p_phone_number_id, phone_number_id),
      waba_id                 = COALESCE(p_waba_id, waba_id),
      whatsapp_phone_e164     = COALESCE(p_whatsapp_phone_e164, whatsapp_phone_e164),
      callback_path           = v_callback_path,
      active                  = TRUE,
      signature_fail_count    = 0,        -- reset on rotation
      updated_at              = NOW()
    WHERE id = v_existing_id;
  END IF;

  id           := v_existing_id;
  callback_url := v_callback_url;
  verify_token := v_verify_token_raw;   -- return raw token ONCE to caller

  RETURN NEXT;
END
$fn$;

COMMENT ON FUNCTION admin_create_or_rotate_webhook(UUID, TEXT, TEXT, TEXT, TEXT, TEXT, TEXT, TEXT, TEXT)
  IS 'Create or rotate a webhook row. Returns callback_url + NEW verify_token (show-once). Requires service_role and app.encryption_key.';

-- ============================================================================
-- 7) Admin function: rotate ONLY the verify token (keeps same secret/ids)
-- ============================================================================

CREATE OR REPLACE FUNCTION admin_rotate_verify_token(
  p_app_id  TEXT
)
RETURNS TABLE (
  id            UUID,
  callback_url  TEXT,
  verify_token  TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $fn$
DECLARE
  v_row webhook_endpoints%ROWTYPE;
  v_verify_token_raw  TEXT;
  v_verify_token_hash TEXT;
  v_base_url          TEXT;
BEGIN
  IF (auth.jwt() ->> 'role') IS DISTINCT FROM 'service_role' THEN
    RAISE EXCEPTION 'insufficient_privilege: service_role required';
  END IF;

  SELECT * INTO v_row
  FROM webhook_endpoints
  WHERE app_id = p_app_id
    AND active = TRUE
  LIMIT 1;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'webhook row not found for app_id=%', p_app_id;
  END IF;

  -- Generate fresh token
  v_verify_token_raw  := replace(replace(encode(gen_random_bytes(32), 'base64'), '+','-'), '/','_');
  v_verify_token_hash := crypt(v_verify_token_raw, gen_salt('bf'));

  UPDATE webhook_endpoints
  SET verify_token_hash    = v_verify_token_hash,
      signature_fail_count = 0,
      updated_at           = NOW()
  WHERE id = v_row.id;

  -- Build full URL from path; require caller to pass base URL? We can infer via a GUC too.
  -- For simplicity, expect you keep base URL in a GUC (set per session in your backend):
  --   SET app.base_url = 'https://your-railway.app';
  v_base_url := current_setting('app.base_url', true);
  IF v_base_url IS NULL OR length(v_base_url) = 0 THEN
    -- Fall back to path only if base not configured
    callback_url := v_row.callback_path;
  ELSE
    callback_url := rtrim(v_base_url, '/') || v_row.callback_path;
  END IF;

  id           := v_row.id;
  verify_token := v_verify_token_raw;

  RETURN NEXT;
END
$fn$;

COMMENT ON FUNCTION admin_rotate_verify_token(TEXT)
  IS 'Rotate only the verify token for an app_id. Returns NEW token (show-once). Requires service_role.';

-- ============================================================================
-- Done.
-- ============================================================================