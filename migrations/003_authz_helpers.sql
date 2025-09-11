BEGIN;

-- -------------------------------------------------------------------
-- Authz helpers (idempotent) — build once, reuse everywhere
-- Works with JWT claims:
--   sub          -> user_id (uuid as text)
--   merchant_id  -> tenant id (uuid as text)
--   role         -> 'admin' | 'staff' (string)
-- -------------------------------------------------------------------

-- 0) Core helpers (ensure they exist; 002 already added some, but OR REPLACE is safe)
CREATE OR REPLACE FUNCTION auth_user_id() RETURNS uuid
LANGUAGE sql STABLE AS
$$
  SELECT NULLIF(auth.jwt()->>'sub','')::uuid
$$;

CREATE OR REPLACE FUNCTION auth_merchant_id() RETURNS uuid
LANGUAGE plpgsql STABLE AS
$$
DECLARE
  claims jsonb;
  mid uuid;
BEGIN
  BEGIN
    claims := current_setting('request.jwt.claims', true)::jsonb;
  EXCEPTION WHEN others THEN
    claims := NULL;
  END;
  IF claims ? 'merchant_id' THEN
    mid := NULLIF(claims->>'merchant_id','')::uuid;
    RETURN mid;
  END IF;
  RETURN NULLIF(auth.jwt()->>'merchant_id','')::uuid;
END;
$$;

CREATE OR REPLACE FUNCTION auth_role() RETURNS text
LANGUAGE plpgsql STABLE AS
$$
DECLARE
  claims jsonb;
  r text;
BEGIN
  BEGIN
    claims := current_setting('request.jwt.claims', true)::jsonb;
  EXCEPTION WHEN others THEN
    claims := NULL;
  END;
  IF claims ? 'role' THEN
    r := COALESCE(claims->>'role','');
    RETURN r;
  END IF;
  RETURN COALESCE(auth.jwt()->>'role','');
END;
$$;

-- 1) Tenant & role checks
CREATE OR REPLACE FUNCTION is_same_tenant(target_merchant_id uuid) RETURNS boolean
LANGUAGE sql STABLE AS
$$
  SELECT target_merchant_id IS NOT NULL
     AND target_merchant_id = auth_merchant_id()
$$;

CREATE OR REPLACE FUNCTION is_admin() RETURNS boolean
LANGUAGE sql STABLE AS
$$
  SELECT auth_role() = 'admin'
$$;

CREATE OR REPLACE FUNCTION is_admin_for(target_merchant_id uuid) RETURNS boolean
LANGUAGE sql STABLE AS
$$
  SELECT is_same_tenant(target_merchant_id) AND is_admin()
$$;

-- 2) Convenience access predicates (future-proof for fine-grained perms)
-- For now: write -> admin; read -> same tenant
CREATE OR REPLACE FUNCTION has_read_access(target_merchant_id uuid) RETURNS boolean
LANGUAGE sql STABLE AS
$$
  SELECT is_same_tenant(target_merchant_id)
$$;

CREATE OR REPLACE FUNCTION has_write_access(target_merchant_id uuid) RETURNS boolean
LANGUAGE sql STABLE AS
$$
  SELECT is_admin_for(target_merchant_id)
$$;

-- 3) Introspection view (handy for debugging)
CREATE OR REPLACE VIEW v_current_principal AS
SELECT
  auth_user_id()      AS user_id,
  auth_merchant_id()  AS merchant_id,
  auth_role()         AS role;


-- Boolean helpers (optional sugar)
CREATE OR REPLACE FUNCTION auth_is_admin() RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT auth_role() = 'admin'
$$;

CREATE OR REPLACE FUNCTION auth_is_same_tenant(tenant uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT auth_merchant_id() = tenant
$$;

-- Example policy using them
DROP POLICY IF EXISTS products_write ON products;
CREATE POLICY products_write ON products
  FOR ALL
  USING (auth_is_admin() AND auth_is_same_tenant(merchant_id))
  WITH CHECK (auth_is_admin() AND auth_is_same_tenant(merchant_id));

COMMIT;

