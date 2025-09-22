-- Drop the old signature first (types must match the existing one)
DROP FUNCTION IF EXISTS public.get_merchant_feed_data(text);

-- Recreate with matching types
CREATE OR REPLACE FUNCTION public.get_merchant_feed_data(merchant_slug_param TEXT)
RETURNS TABLE (
    merchant_id            uuid,
    merchant_name          text,
    merchant_slug          text,
    product_id             uuid,
    title                  text,
    description            text,
    price_kobo             bigint,       -- was integer; match products.price_kobo
    stock                  integer,
    available_qty          integer,
    image_url              text,
    retailer_id            text,
    category_path          text,
    status                 text,
    meta_catalog_visible   boolean,
    created_at             timestamptz,  -- match your table type
    updated_at             timestamptz
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
STABLE
AS $$
BEGIN
  RETURN QUERY
  SELECT 
      m.id,
      m.name,
      m.slug,
      p.id,
      p.title,
      p.description,
      p.price_kobo,          -- bigint
      p.stock,
      p.available_qty,
      p.image_url,
      p.retailer_id,
      p.category_path,
      p.status,
      p.meta_catalog_visible,
      p.created_at,
      p.updated_at
  FROM merchants m
  LEFT JOIN products p 
    ON p.merchant_id = m.id
   AND p.status = 'active'
   AND p.meta_catalog_visible = true
  WHERE m.slug = merchant_slug_param;
END;
$$;

-- Lock down & grant execute to roles your API uses
REVOKE ALL ON FUNCTION public.get_merchant_feed_data(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_merchant_feed_data(text) TO anon, authenticated;