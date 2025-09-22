-- Migration: 010_slug_generation_functions.sql
-- Purpose: Add database-level slug generation for merchants
-- Safe to run multiple times

-- Enable unaccent extension for accent folding: "Beyoncé" -> "beyonce"
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Slugify function: converts text to URL-friendly slug
-- Example: "Jane's Beauty Store!" -> "janes-beauty-store"
CREATE OR REPLACE FUNCTION public.slugify(input text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT
    regexp_replace(
      regexp_replace( -- collapse multiple dashes
        regexp_replace( -- replace non-alphanumeric with dash
          lower(trim(unaccent(coalesce(input, '')))),
          '[^a-z0-9]+', '-', 'g'
        ),
        '-{2,}', '-', 'g'
      ),
      '(^-|-$)', '', 'g' -- remove leading/trailing dashes
    )
$$;

-- Generate unique slug with -2, -3... suffixes if needed
-- Ensures no collisions with existing slugs in merchants table
CREATE OR REPLACE FUNCTION public.generate_unique_slug(base text)
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
  base_slug text := slugify(base);
  candidate text := NULLIF(base_slug, '');
  suffix int := 1;
  exists_ boolean;
BEGIN
  -- Fallback for empty inputs
  IF candidate IS NULL THEN
    candidate := 'merchant';
  END IF;

  -- Check for uniqueness and add suffix if needed
  LOOP
    SELECT EXISTS (SELECT 1 FROM public.merchants m WHERE m.slug = candidate)
      INTO exists_;
    EXIT WHEN NOT exists_;
    suffix := suffix + 1;
    candidate := base_slug || '-' || suffix::text;
  END LOOP;

  RETURN candidate;
END;
$$;

-- Ensure slug column exists and has uniqueness constraint
ALTER TABLE public.merchants
  ADD COLUMN IF NOT EXISTS slug text;

CREATE UNIQUE INDEX IF NOT EXISTS merchants_slug_key
  ON public.merchants (slug);

-- Comments for documentation
COMMENT ON FUNCTION public.slugify(text) IS 'Converts text to URL-friendly slug format';
COMMENT ON FUNCTION public.generate_unique_slug(text) IS 'Generates unique slug for merchants, handling collisions with suffixes';
COMMENT ON COLUMN public.merchants.slug IS 'URL-friendly unique identifier generated from business name';