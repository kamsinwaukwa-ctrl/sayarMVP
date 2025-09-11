-- Migration: 010_login_lookup_function.sql
-- Purpose: Login lookup function to bypass RLS for authentication
-- Allows looking up user by email during login without requiring JWT context

BEGIN;

-- Function to lookup user for authentication, bypassing RLS
CREATE OR REPLACE FUNCTION public.lookup_user_for_login(
  p_email text
)
RETURNS TABLE (
  out_user_id uuid,
  out_merchant_id uuid,
  out_name text,
  out_email text,
  out_password_hash text,
  out_role text
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
  -- Input validation
  IF p_email IS NULL OR length(trim(p_email)) = 0 THEN
    RAISE EXCEPTION 'Email cannot be empty' USING ERRCODE = '22023';
  END IF;

  -- Lookup user by email (bypasses RLS due to SECURITY DEFINER)
  RETURN QUERY
  SELECT 
    u.id,
    u.merchant_id,
    u.name,
    u.email,
    u.password_hash,
    u.role
  FROM public.users u
  WHERE u.email = lower(trim(p_email));
END;
$$;

-- Security: Revoke public access and grant only to authenticated roles
REVOKE ALL ON FUNCTION public.lookup_user_for_login(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.lookup_user_for_login(text) TO anon, authenticated;

-- Ensure function is owned by privileged role
ALTER FUNCTION public.lookup_user_for_login(text) OWNER TO postgres;

COMMIT;

-- Migration notes:
-- 1. SECURITY DEFINER allows the function to run with elevated privileges
-- 2. Only used for login authentication - bypasses RLS safely
-- 3. Returns user data needed for authentication and JWT creation
-- 4. All other user operations still go through normal RLS policies