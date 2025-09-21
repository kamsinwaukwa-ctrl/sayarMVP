import { z } from 'zod'

export const brandBasicsSchema = z.object({
  description: z.string().trim().min(10, "Description must be at least 10 characters"),
  currency: z.enum(['NGN', 'USD', 'GHS', 'KES'] as const),
  logo_url: z.string().url("Upload a logo first").optional()
})

export type BrandBasicsFormData = z.infer<typeof brandBasicsSchema>