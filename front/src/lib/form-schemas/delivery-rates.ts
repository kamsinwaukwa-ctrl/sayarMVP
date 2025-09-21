import { z } from 'zod'

export const deliveryRateSchema = z.object({
  name: z.string().min(2, "Rate name required"),
  areas_text: z.string().min(5, "Delivery areas required"),
  price_kobo: z.number().min(0, "Price cannot be negative"),
  description: z.string().optional()
})