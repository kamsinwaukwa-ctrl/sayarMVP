import { z } from 'zod'

export const brandBasicsSchema = z.object({
  description: z.string().trim().min(10, "Description must be at least 10 characters"),
  currency: z.enum(['NGN', 'USD', 'GHS', 'KES'] as const),
  logo_url: z.string().url("Upload a logo first").optional(),
  // Extended fields for settings mode
  website_url: z.string().url("Please enter a valid URL").optional().or(z.literal('')),
  support_email: z.string().email("Please enter a valid email").optional().or(z.literal('')),
  support_phone_e164: z.string().optional(),
  address_line1: z.string().optional(),
  address_line2: z.string().optional(),
  city: z.string().optional(),
  state_region: z.string().optional(),
  postal_code: z.string().optional(),
  country_code: z.string().optional(),
})

export type BrandBasicsFormData = z.infer<typeof brandBasicsSchema>