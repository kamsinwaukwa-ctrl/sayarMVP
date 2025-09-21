import { z } from 'zod'

export const paymentVerificationSchema = z.object({
  provider: z.enum(['paystack', 'korapay']),
  secret_key: z.string().min(10, "Secret key required"),
  public_key: z.string().min(10, "Public key required")
})