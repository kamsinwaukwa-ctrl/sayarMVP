import { z } from 'zod'

export const deliveryRateSchema = z.object({
  name: z.string().min(2, "Rate name required"),
  areas_text: z.string().min(5, "Delivery areas required"),
  price_naira: z.union([z.string(), z.number()])
    .transform(v => String(v))
    .refine(v => /^\d+(\.\d{0,2})?$/.test(v.replace(/,/g, "")), "Enter a valid amount (max 2 decimals)")
    .refine(v => parseFloat(v.replace(/,/g, "")) >= 0, "Price cannot be negative"),
  description: z.string().optional()
})