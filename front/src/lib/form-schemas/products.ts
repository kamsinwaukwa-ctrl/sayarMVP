import { z } from 'zod'

export const productSchema = z.object({
  title: z.string().min(2, "Product name required"),
  description: z.string().optional(),
  price_kobo: z.number().min(100, "Minimum price ₦1.00"),
  stock: z.number().min(0, "Stock cannot be negative"),
  sku: z.string().regex(/^[A-Za-z0-9-_]{1,64}$/).optional()
    .describe("SKU (optional) — leave blank to auto-generate"),
  condition: z.enum(['new', 'used', 'refurbished']).optional()
    .describe("Product condition (improves Meta acceptance)"),
  category_path: z.string().optional(),
  tags: z.array(z.string()).default([]),
  image_url: z.string().url("Must be a valid URL").optional(),
  additional_image_urls: z.array(z.string().url("Must be a valid URL")).optional()
    .describe("Additional product images (up to 10 images)"),
  // Advanced Meta-friendly fields
  brand: z.string().optional()
    .describe("Product brand (readonly after creation)"),
  mpn: z.string().optional()
    .describe("Manufacturer Part Number (readonly after creation)"),
  gtin: z.string().optional()
    .describe("Global Trade Item Number (readonly after creation)")
})