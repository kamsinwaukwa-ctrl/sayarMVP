-- Migration: 009_register_bootstrap_function.sql
-- Purpose: Bootstrap function to register merchant and admin user atomically, bypassing RLS safely
-- Solves the chicken-and-egg problem where RLS policies prevent initial merchant/user creation

CREATE OR REPLACE FUNCTION public.register_merchant_and_admin(
  p_name            text,
  p_email           text,
  p_password_hash   text,
  p_business_name   text,
  p_whatsapp        text DEFAULT NULL
)
RETURNS TABLE (out_merchant_id uuid, out_user_id uuid, out_slug text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_merchant_id uuid := gen_random_uuid();
  v_user_id     uuid := gen_random_uuid();
  v_whatsapp    text := NULLIF(trim(p_whatsapp), '');
  v_slug        text;
BEGIN
  -- Basic validation (optional if you validate in app)
  IF p_name IS NULL OR length(trim(p_name)) = 0 THEN
    RAISE EXCEPTION 'Name cannot be empty' USING ERRCODE = '22023';
  END IF;
  IF p_email IS NULL OR length(trim(p_email)) = 0 THEN
    RAISE EXCEPTION 'Email cannot be empty' USING ERRCODE = '22023';
  END IF;
  IF p_password_hash IS NULL OR length(p_password_hash) = 0 THEN
    RAISE EXCEPTION 'Password hash cannot be empty' USING ERRCODE = '22023';
  END IF;
  IF p_business_name IS NULL OR length(trim(p_business_name)) = 0 THEN
    RAISE EXCEPTION 'Business name cannot be empty' USING ERRCODE = '22023';
  END IF;

  -- Optional pre-check; you can also rely on a UNIQUE INDEX on lower(email)
  PERFORM 1 FROM public.users WHERE email = lower(trim(p_email));
  IF FOUND THEN
    RAISE EXCEPTION 'User with this email already exists' USING ERRCODE = '23505';
  END IF;

  -- Generate unique slug from business name
  v_slug := public.generate_unique_slug(trim(p_business_name));

  INSERT INTO public.merchants (id, name, slug, whatsapp_phone_e164, created_at, updated_at)
  VALUES (v_merchant_id, trim(p_business_name), v_slug, v_whatsapp, now(), now());

  INSERT INTO public.users (id, merchant_id, name, email, password_hash, role, created_at, updated_at)
  VALUES (v_user_id, v_merchant_id, trim(p_name), lower(trim(p_email)), p_password_hash, 'admin', now(), now());

  -- ✅ Return one row for the caller including the generated slug
  RETURN QUERY SELECT v_merchant_id, v_user_id, v_slug;
END;
$$;

-- Lock down & grant
REVOKE ALL ON FUNCTION public.register_merchant_and_admin(text, text, text, text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.register_merchant_and_admin(text, text, text, text, text) TO anon, authenticated;
-- Migration notes:
-- 1. SECURITY DEFINER allows the function to run with the privileges of the function owner
-- 2. SET search_path prevents search-path hijacking attacks  
-- 3. This function only bypasses RLS for the specific bootstrap case
-- 4. All existing RLS policies remain intact for normal operations
-- 5. Function validates inputs and provides meaningful error messages
-- 6. Atomic transaction ensures both merchant and user are created or both fail